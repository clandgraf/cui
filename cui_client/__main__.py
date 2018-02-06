# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import contextlib
import json
import sys

from cui_tools import io_selector
from cui_tools import cli
from cui_tools import server
from cui_tools.util import escape_c, unescape_c


class Client(object):
    def __init__(self, prompt):
        self._io_selector = io_selector.IOSelector(timeout=None)
        self._cli = cli.CommandLine(prompt, self.send, env=self)
        self._conn = server.Connection(
            server.LineBufferedSession,
            'localhost', 5000,
            env=self
        )
        self.running = False
        self.exit_on_result = None

    def register_waitable(self, waitable, handler):
        self._io_selector.register(waitable, handler)

    def unregister_waitable(self, waitable):
        self._io_selector.unregister(waitable)

    def send(self, line):
        if line is None:
            self.running = False
            return

        line = line.strip()
        if not len(line):
            return

        self._conn.session.send_line(json.dumps({
            'type': 'eval',
            'line': escape_c(line),
        }))

    def receive(self, line):
        response = json.loads(line)
        if response['type'] in ['result', 'trace']:
            self.write(response['line'])
            if self.exit_on_result:
                self.running = False

    def write(self, line):
        if self._cli.is_active():
            self._cli.write(unescape_c(line))
        else:
            print(line)

    @contextlib.contextmanager
    def connection(self):
        try:
            self._conn.start(
                callback=self.receive,
                encoding='utf-8'
            )
            yield
        finally:
            self._conn.stop()

    def run(self):
        self.exit_on_result = False
        with self.connection():
            try:
                self._cli.start()
                self.running = True
                while self.running:
                    self._io_selector.select()
            finally:
                self._cli.stop()

    def evaluate(self, string):
        self.exit_on_result = True
        with self.connection():
            self.send(string)
            self.running = True
            while self.running:
                self._io_selector.select()


def main():
    parser = argparse.ArgumentParser('Communicate with cui.remote')
    parser.add_argument('-e', type=str, default=None, help='Evaluate a single command and exit')
    args = parser.parse_args()

    if args.e:
        Client('>>> ').evaluate(args.e)
    else:
        Client('>>> ').run()


if __name__ == '__main__':
    main()
