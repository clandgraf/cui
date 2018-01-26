# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import select
import signal
import subprocess

<<<<<<< Updated upstream
=======
from cui import tools

>>>>>>> Stashed changes
class Process(object):
    BUFFER_SIZE = 1024

    def __init__(self, *args):
        self._args = args
        self._pread = None
        self._pwrite = None
        self._proc = None

    def start(self):
        self._pread, self._pwrite = os.pipe()
        self._proc = subprocess.Popen(self._args, stdout=self._pwrite, stdin=self._pread)
        cui.register_waitable(self._pread, self.handle)

    def stop(self):
        self.kill()

    def kill(self):
        os.kill(self._proc.pid, signal.SIGINT)

    def handle(self):
        self.handle_input(os.read(self._pread, ProcessPipe.BUFFER_SIZE))

    def handle_input(self):
        pass


class LineBufferedProcess(tools.LineReader, Process):
    def handle_line(self, line):
        pass
