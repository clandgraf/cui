# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import select
import signal
import subprocess

from . import LineReader

class Process(object):
    BUFFER_SIZE = 1024

    def __init__(self, *args, **kwargs):
        self._args = args
        self._pread = None
        self._pwrite = None
        self._proc = None
        self._env = kwargs['env']

    def start(self):
        self._proc = subprocess.Popen(self._args,
                                      stdout=subprocess.PIPE,
                                      stdin=subprocess.PIPE,
                                      bufsize=0)
        self._env.register_waitable(self._proc.stdout, self.handle)

    def stop(self):
        self._env.unregister_waitable(self._proc.stdout)
        self.term()

    def term(self):
        self.kill()

    def kill(self, wait=False):
        self._proc.kill()
        if wait:
            return self._proc.wait()

    def send_all(self, buf):
        self._proc.stdin.write(buf.encode('utf-8'))

    def handle(self, pread):
        self.handle_input(self._proc.stdout.read(Process.BUFFER_SIZE))

    def handle_input(self):
        # Overwrite in subclass
        pass


class LineBufferedProcess(LineReader, Process):
    def handle_line(self, line):
        # Overwrite in subclass
        pass
