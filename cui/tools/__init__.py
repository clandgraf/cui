# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Mixin for io_selector handlers to dispatch input line-wise
class LineReader(object):
    def __init__(self, *args, **kwargs):
        super(LineReader, self).__init__(*args, **kwargs)
        self._read_buffer = ''
        self._encoding = kwargs.get('encoding', 'utf-8')
        self._separator = kwargs.get('separator', '\n')

    def handle(self):
        self._read_buffer += self.get_input().decode(self._encoding)
        while self._read_buffer.find('\n') != -1:
            line, self._read_buffer = self._read_buffer.split(self._separator, 1)
            self.handle_line(line)

    def get_input(self):
        pass

    def handle_line(self, line):
        pass
