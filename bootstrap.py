#!/bin/python
# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import os.path
import subprocess
import sys


def set_default_subparser(self, name, args=None):
    """
    default subparser selection. 
    
    Call after setup, just before parse_args()
    :param name: is the name of the subparser to call by default
    :param args: if set is the argument list handed to parse_args()
    """
    subparser_found = False
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:  # global help if no subparser
            break
    else:
        for x in self._subparsers._actions:
            if not isinstance(x, argparse._SubParsersAction):
                continue
            for sp_name in x._name_parser_map.keys():
                if sp_name in sys.argv[1:]:
                    subparser_found = True
        if not subparser_found:
            # insert default in first position, this implies no
            # global options without a sub_parsers specified
            if args is None:
                sys.argv.insert(1, name)
            else:
                args.insert(0, name)
    
    
argparse.ArgumentParser.set_default_subparser = set_default_subparser


def create_requirements():
    with open('./requirements.txt', 'w') as req_file:
        req_file.write('--index-url https://pypi.python.org/simple/\n\n')
        req_file.write('-e file://%s#egg=cui\n' % os.path.abspath(os.path.dirname(__file__)))

        if os.path.exists('./packages.json'):
            try:
                pkg_file = open('./packages.json', 'r')
                packages = json.load(pkg_file)
                for package in packages:
                    req_file.write('-e %(path)s#egg=%(name)s\n' % package)
            finally:
                pkg_file.close()


def bootstrap():
    create_requirements()
    subprocess.run(['virtualenv', '.'])
    subprocess.run(['bin/pip', 'install', '-r', 'requirements.txt'])


def main():
    parser = argparse.ArgumentParser(prog='bootstrap.py')
    subparsers = parser.add_subparsers()
    bootstrap_parser = subparsers.add_parser('bootstrap',
                                             help='Bootstrap cui dev environment')
    bootstrap_parser.set_defaults(func=bootstrap)

    bootstrap_parser = subparsers.add_parser('requirements',
                                             help='Create a requirements.txt')
    bootstrap_parser.set_defaults(func=create_requirements)
    parser.set_default_subparser('bootstrap')
    args = parser.parse_args()
    args.func()


if __name__ == '__main__':
    main()
