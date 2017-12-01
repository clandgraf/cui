#!/bin/python

import json
import os.path
import subprocess
import argparse

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
    args = parser.parse_args()
    args.func()



if __name__ == '__main__':
    main()
