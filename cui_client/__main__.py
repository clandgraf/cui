# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys

from cui_tools import io_selector
from cui_tools import cli
from cui_tools import server

PROMPT = '>>> '.encode('utf-8')


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

        self._conn.session.send_all(line + b'\n')

    def receive(self, line):
        print(line)

    def run(self):
        try:
            self._conn.start(callback=self.receive)
            self._cli.start()
            self.running = True
            while self.running:
                self._io_selector.select()
        finally:
            self._cli.stop()


def main():
    Client('>>> '.encode('utf-8')).run()


if __name__ == '__main__':
    main()
