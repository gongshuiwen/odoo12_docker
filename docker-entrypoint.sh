#!/bin/bash

set -e

# set the postgres database host, port, user and password according to the environment
# and pass them as arguments to the odoo process if not present in the config file
: "${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}"
: "${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}"
: "${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}"
: "${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}"

DB_ARGS=()
function check_config() {
    param="$1"
    value="$2"
    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then       
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;
    DB_ARGS+=("--${param}")
    DB_ARGS+=("${value}")
}
check_config "db_host" "$HOST"
check_config "db_port" "$PORT"
check_config "db_user" "$USER"
check_config "db_password" "$PASSWORD"

: "${RABBIT_HOST:='rabbitmq'}"
: "${RABBIT_PORT:='5672'}"
: "${RABBIT_USER:='guest'}"
: "${RABBIT_PASSWORD:='guest'}"

RABBIT_ARGS=()
function check_config_rabbit() {
    param="$1"
    value="$2"
    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;
    RABBIT_ARGS+=("--${param}")
    RABBIT_ARGS+=("${value}")
}
check_config_rabbit "rabbit_host" "${RABBIT_HOST}"
check_config_rabbit "rabbit_port" "${RABBIT_PORT}"
check_config_rabbit "rabbit_user" "${RABBIT_USER}"
check_config_rabbit "rabbit_password" "${RABBIT_PASSWORD}"

: "${REDIS_HOST:='redis'}"
: "${REDIS_PORT:='6379'}"
: "${REDIS_PASSWORD:='redis'}"

REDIS_ARGS=()
function check_config_redis() {
    param="$1"
    value="$2"
    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;
    REDIS_ARGS+=("--${param}")
    REDIS_ARGS+=("${value}")
}
check_config_redis "redis_host" "${REDIS_HOST}"
check_config_redis "redis_port" "${REDIS_PORT}"
check_config_redis "redis_password" "${REDIS_PASSWORD}"

function wait-for-connection() {
   wait-for-psql.py "${DB_ARGS[@]}" --timeout=30
   wait-for-rabbit.py "${RABBIT_ARGS[@]}" --timeout=30
   wait-for-redis.py "${REDIS_ARGS[@]}" --timeout=30
}

case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]] ; then
            exec odoo_starter.py "$@"
        else
            wait-for-connection
            exec odoo_starter.py "$@" "${DB_ARGS[@]}"
        fi
        ;;
    celery )
        shift
        wait-for-connection
        cd /usr/local/bin
        exec celery -A odoo_starter worker "$@"
        ;;
    -*)
        wait-for-connection
        exec odoo_starter.py "$@" "${DB_ARGS[@]}"
        ;;
    *)
        exec "$@"
esac

exit 1
