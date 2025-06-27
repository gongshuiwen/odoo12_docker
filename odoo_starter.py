#!/usr/bin/env python3
import logging
from celery import Celery
from os.path import join as joinpath, isdir

import odoo
from odoo.modules import get_modules, get_module_path
from odoo.tools import config

# set server timezone in UTC before time module imported
__import__('os').environ['TZ'] = 'UTC'
_logger = logging.getLogger('odoo.stater')

# parse odoo.conf
config.parse_config()


def initialize_celery_instance():
    rabbit_host = config.get("rabbit_host", "mq")
    rabbit_port = config.get("rabbit_port", "5672")
    rabbit_user = config.get("rabbit_user", "guest")
    rabbit_pass = config.get("rabbit_password", "guest")
    rabbit_vhost = config.get("rabbit_vhost", "/")
    broker = "pyamqp://{}:{}@{}:{}/{}".format(rabbit_user, rabbit_pass, rabbit_host, rabbit_port, rabbit_vhost)
    celery_app = Celery('odoo', broker=broker)
    _logger.info("Celery instance created. (broker=pyamqp://{}@{}:{}/{})"
                 .format(rabbit_user, rabbit_host, rabbit_port, rabbit_vhost))
    return celery_app


def import_celery_tasks():
    # Import all addons' sub-module named 'tasks'
    _logger.info("Importing tasks from Odoo...")
    for module in get_modules():
        if isdir(joinpath(get_module_path(module), 'tasks')):
            __import__('odoo.addons.' + module + '.tasks')
    _logger.info("%s tasks imported from Odoo." % len([t for t in odoo.celery.tasks.keys() if t.startswith('odoo')]))


celery = odoo.celery = initialize_celery_instance()
import_celery_tasks()


if __name__ == "__main__":
    if config.get('session_type', False) == 'redis':
        from redis_session_store import monkey_patch_http_session_store_and_session_gc
        old_session_store, new_session_store = monkey_patch_http_session_store_and_session_gc()

        # migrate sessions by default
        if config.get('session_migrate', True):
            from redis_session_store import migrate_sessions
            migrate_sessions(old_session_store, new_session_store)

    if config.get('file_store_type', False) == 'minio':
        from ir_attachment_minio import monkey_patch_ir_attachment
        monkey_patch_ir_attachment()

    odoo.cli.main()
