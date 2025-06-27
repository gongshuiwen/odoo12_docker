#!/usr/bin/env python3
import argparse
import sys
import time

from amqp.connection import Connection

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--rabbit_host', required=True)
    arg_parser.add_argument('--rabbit_port', required=True)
    arg_parser.add_argument('--rabbit_user', required=True)
    arg_parser.add_argument('--rabbit_password', required=True)
    arg_parser.add_argument('--timeout', type=int, default=5)
    args = arg_parser.parse_args()

    start_time = time.time()
    error = ''
    while (time.time() - start_time) < args.timeout:
        try:
            conn = Connection("%s:%s" % (args.rabbit_host, args.rabbit_port), args.rabbit_user, args.rabbit_password)
            conn.connect()
        except Exception as e:
            error = e
        else:
            conn.close()
            sys.exit(0)
        time.sleep(1)

    if error:
        print("RabbitMQ connection failure: %s" % error, file=sys.stderr)
        sys.exit(1)
