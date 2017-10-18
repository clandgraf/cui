#!/bin/python

import json
import os.path
import subprocess

def create_requirements():
    with open('./requirements.txt', 'w') as req_file:
        req_file.write('--index-url https://pypi.python.org/simple/\n\n')
        req_file.write('-e file://%s#egg=cui' % os.path.dirname(__file__))

        if os.path.exists('./packages.json'):
            try:
                pkg_file = open('./packages.json', 'r')
                packages = json.load(pkg_file)
                for package in packages:
                    req_file.write('-e %(path)s#=%(name)s' % package)
            finally:
                pkg_file.close()


def main():
    create_requirements()
    subprocess.run(['virtualenv', '.'])
    subprocess.run(['bin/pip' 'install' '-r' 'requirements.txt'])


if __name__ == '__main__':
    main()
