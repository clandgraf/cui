# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import os
import select
import signal
import subprocess

from cui import tools

class Process(object):
    BUFFER_SIZE = 1024

    def __init__(self, *args, **kwargs):
        self._args = args
        self._pread = None
        self._pwrite = None
        self._proc = None

    def start(self):
        self._proc = subprocess.Popen(self._args,
                                      stdout=subprocess.PIPE,
                                      stdin=subprocess.PIPE,
                                      bufsize=0)
        cui.register_waitable(self._proc.stdout, self.handle)

    def stop(self):
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


class LineBufferedProcess(tools.LineReader, Process):
    def handle_line(self, line):
        # Overwrite in subclass
        pass
