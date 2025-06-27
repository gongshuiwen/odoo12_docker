import base64
import io
import logging
from minio import Minio

from odoo import api
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.tools import config

_logger = logging.getLogger(__name__)


@api.model
def _file_read(self, fname, bin_size=False):
    db_name = self.env.cr.dbname
    if bin_size:
        r = self.minio_client.stat_object(self.bucket_name, db_name + '/' + fname).size
    else:
        with self.minio_client.get_object(self.bucket_name, db_name + '/' + fname) as resp:
            r = base64.b64encode(resp.data)
    return r


@api.model
def _file_write(self, value, checksum):
    bin_value = base64.b64decode(value)
    fname, full_path = self._get_path(bin_value, checksum)
    db_name = self.env.cr.dbname
    self._mark_for_gc(fname)
    self.minio_client.put_object(self.bucket_name, db_name + '/' + fname, io.BytesIO(bin_value), len(bin_value))
    return fname


def _mark_for_gc(self, fname):
    """ Add ``fname`` in a checklist for the filestore garbage collection. """
    db_name = self.env.cr.dbname
    self.minio_client.put_object(self.bucket_name, db_name + '/checklist/' + fname, io.BytesIO(b""), 0)
    return


@api.model
def _file_gc(self):
    """ Perform the garbage collection of the filestore. """
    cr = self._cr
    dbname = cr.dbname
    cr.commit()

    # prevent all concurrent updates on ir_attachment while collecting!
    cr.execute("LOCK ir_attachment IN SHARE MODE")

    # retrieve the file names from the checklist
    checklist = {}
    for obj in self.minio_client.list_objects(self.bucket_name, dbname + "/checklist/", recursive=True):
        checklist[obj.object_name.split("/checklist/")[-1]] = obj.object_name

    # determine which files to keep among the checklist
    whitelist = set()
    for names in cr.split_for_in_conditions(checklist):
        cr.execute("SELECT store_fname FROM ir_attachment WHERE store_fname IN %s", [names])
        whitelist.update(row[0] for row in cr.fetchall())

    # remove garbage files, and clean up checklist
    removed = 0
    for fname, filepath in checklist.items():
        if fname not in whitelist:
            try:
                self.minio_client.remove_object(self.bucket_name, fname)
                removed += 1
            except (OSError, IOError):
                _logger.info("_file_gc could not unlink %s", self._full_path(fname), exc_info=True)
        self.minio_client.remove_object(self.bucket_name, filepath)

    # commit to release the lock
    cr.commit()
    _logger.info("filestore gc %d checked, %d removed", len(checklist), removed)
    return


def monkey_patch_ir_attachment():
    minio_endpoint = config.get('minio_endpoint', "127.0.0.1:9000")
    minio_client = Minio(
        endpoint=minio_endpoint,
        access_key=config.get('minio_access_key', False),
        secret_key=config.get('minio_secret_key', False),
        secure=config.get('minio_secure', False)
    )

    bucket_name = config.get('bucket_name', "odoo-files")
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    IrAttachment.minio_client = minio_client
    IrAttachment.bucket_name = bucket_name
    IrAttachment._file_read = _file_read
    IrAttachment._file_write = _file_write
    IrAttachment._mark_for_gc = _mark_for_gc
    IrAttachment._file_gc = _file_gc
    _logger.info('Files stored in: minio://%s/%s' % (minio_endpoint, IrAttachment.bucket_name))
