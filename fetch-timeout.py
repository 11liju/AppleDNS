#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import json
import os.path
import random
import socket
import sys
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from multiprocessing.dummy import Pool as ParallelPool

from io import open

if sys.version_info[0] == 2:
    from urlparse import urlparse
    str = unicode
else:
    from urllib.parse import urlparse


def check_requirements():
    def check_python_version():
        if sys.hexversion >= 0x2000000 and sys.hexversion <= 0x2070000:
            print('your "python" lower than 2.7.0 upgrade.')
            return False
        if sys.hexversion >= 0x3000000 and sys.hexversion <= 0x3040000:
            print('your "python" lower than 3.4.0 upgrade.')
            return False
        return True

    return check_python_version()


def request(target):
    host, port, timeout = target
    try:
        begin_time = datetime.now()

        conn = socket.socket()
        conn.settimeout(timeout)
        conn.connect((host, port))

        end_time = datetime.now()

        delta = end_time - begin_time

        rt = (delta.seconds * 1000) + (delta.microseconds / 1000.0)
        return host, rt
    except socket.error as err:
        return host, False


def fetch(payload, timeout, concurrent, testing_times):
    if not payload:
        return

    def handle_ip(target):
        address = urlparse('http://%s' % str(target))
        return address.hostname, address.port or 80, timeout

    def handle_ipset(ips):
        ips = ips * testing_times
        random.shuffle(ips)
        return ips

    with closing(ParallelPool(concurrent)) as pool:
        for service_item in payload:
            print(str(service_item['title']))
            print(', '.join(service_item['domains']))
            for name, ips in service_item['ips'].items():
                request_payload = map(handle_ip, handle_ipset(ips))
                ipset = defaultdict(list)
                print('\t%s' % name)
                for ip, delta in pool.imap(request, request_payload):
                    ipset[ip].append(delta)
                    if delta:
                        print('\t\t%-15s\t%sms' % (ip, delta))
                service_item['ips'][name] = ipset
    return payload


def load_payload(path):
    if os.path.exists(path):
        with open(path, encoding='UTF-8') as fp:
            return json.loads(fp.read())


def save_result(payload):
    target_filename = 'apple-cdn-speed.report'
    with open(target_filename, 'w', encoding='utf-8') as fp:
        report_data = json.dumps(
            payload,
            sort_keys=True,
            indent=4,
            ensure_ascii=False
        )
        fp.write(str(report_data))


def main():
    parser = ArgumentParser()
    parser.add_argument(
        'payload',
        type=str,
        help='payload'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        help='timeout (default: 400) (unit ms)',
        dest='timeout',
        default=400
    )

    parser.add_argument(
        '--concurrent',
        type=int,
        help='concurrent (default: 10)',
        dest='concurrent',
        default=10
    )

    parser.add_argument(
        '--testing_times',
        type=int,
        help='testing times (default: 20)',
        dest='testing_times',
        default=20
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    save_result(
        fetch(
            load_payload(args.payload),
            timeout=args.timeout / 1000.0,
            concurrent=args.concurrent,
            testing_times=args.testing_times
        )
    )


if __name__ == '__main__' and check_requirements():
    main()
