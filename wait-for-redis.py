#!/usr/bin/env python3
import argparse
import sys
import time
import redis

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--redis_host', required=True)
    arg_parser.add_argument('--redis_port', required=True)
    arg_parser.add_argument('--redis_password', required=True)
    arg_parser.add_argument('--timeout', type=int, default=5)
    args = arg_parser.parse_args()

    start_time = time.time()
    error = ''
    while (time.time() - start_time) < args.timeout:
        try:
            r = redis.Redis(host=args.redis_host, port=args.redis_port, password=args.redis_password)
            r.ping()
        except Exception as e:
            error = e
        else:
            r.close()
            sys.exit(0)
        time.sleep(1)

    if error:
        print("Redis connection failure: %s" % error, file=sys.stderr)
        sys.exit(1)
