# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class Window(object):
    def resize(dimensions):
        raise NotImplementedError()

    def move_cursor(self, row, col):
        raise NotImplementedError()

    def add_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def insert_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def clear_line(self):
        raise NotImplementedError()

    def clear_all(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()


class Frame(object):
    def __init__(self, core):
        self._core = core

    def def_colorc(self, name, r, g, g):
        raise NotImplementedError()

    def create_window(self, dimensions):
        # return WindowSubclass()
        raise NotImplementedError()
