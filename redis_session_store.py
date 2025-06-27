import json
import logging
import redis
from werkzeug.contrib.sessions import SessionStore

import odoo
from odoo.tools import config


_logger = logging.getLogger(__name__)


class RedisSessionStore(SessionStore):
    DEFAULT_MAX_CONNECTIONS = 64
    DEFAULT_KEYNAME_TEMPLATE = "sess.werkzeug:%s"
    SESSION_VALIDATION_TIME = 60 * 60 * 24 * 7

    def __init__(self, host='localhost', port=6379, password=None, db=0,
                 max_connections=DEFAULT_MAX_CONNECTIONS, session_class=None,
                 keyname_template=DEFAULT_KEYNAME_TEMPLATE,
                 renew_missing=False, validation_time=SESSION_VALIDATION_TIME):
        SessionStore.__init__(self, session_class)
        self.pool = redis.ConnectionPool(
            host=host, port=port, password=password, db=db, max_connections=max_connections)
        self.keyname_template = keyname_template
        self.renew_missing = renew_missing
        self.validation_time = validation_time

    def get_session_key(self, sid):
        return self.keyname_template % sid

    def save(self, session):
        key = self.get_session_key(session.sid)
        with redis.Redis(connection_pool=self.pool) as client:
            client.set(key, json.dumps(dict(session)), self.validation_time)

    def delete(self, session):
        key = self.get_session_key(session.sid)
        with redis.Redis(connection_pool=self.pool) as client:
            client.delete(key)

    def get(self, sid):
        if not self.is_valid_key(sid):
            return self.new()

        with redis.Redis(connection_pool=self.pool) as client:
            d = client.get(self.get_session_key(sid))

        if d is None:
            if self.renew_missing:
                return self.new()
            data = {}
        else:
            try:
                data = json.loads(d)
            except json.decoder.JSONDecodeError:
                data = {}

        return self.session_class(data, sid, False)


def initialize_redis_session_store():
    host = config.get('redis_host', 'localhost')
    port = config.get('redis_port', 6379)
    password = config.get('redis_password', None)
    db = config.get("redis_db", 0)
    max_connections = int(config.get("redis_maxconn", 64))
    _logger.info('HTTP sessions stored in: redis://%s:%s/%s' % (host, port, db))
    return RedisSessionStore(host=host, port=port, password=password, db=db, max_connections=max_connections,
                             session_class=odoo.http.OpenERPSession, renew_missing=True)


def monkey_patch_http_session_store_and_session_gc():
    old_session_store = odoo.http.root.session_store
    new_session_store = initialize_redis_session_store()

    # Monkey patch for root's session_store property
    odoo.http.root.session_store = new_session_store

    # Monkey patch for http's session_gc method to do nothing
    odoo.http.session_gc = lambda x: x

    return old_session_store, new_session_store


def migrate_sessions(old, new):
    for sid in old.list():
        session = old.get(sid)
        new.save(session)
        old.delete(session)
