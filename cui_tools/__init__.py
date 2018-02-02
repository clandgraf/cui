# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Mixin for io_selector handlers to dispatch input line-wise
# TODO should use encoding for send_all
class LineReader(object):
    def __init__(self, *args, **kwargs):
        super(LineReader, self).__init__(*args, **kwargs)
        self._read_buffer = ''
        self._encoding = kwargs.get('encoding', 'utf-8')
        self._separator = kwargs.get('separator', '\n')
        self._callback = kwargs.get('callback', None)

    def handle_input(self, buf):
        self._read_buffer += buf.decode(self._encoding)
        while self._read_buffer.find(self._separator) != -1:
            line, self._read_buffer = self._read_buffer.split(self._separator, 1)
            self.handle_line(line)

    def get_input(self):
        pass

    def handle_line(self, line):
        if self._callback:
            self._callback(line)
