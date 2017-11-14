# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from cui.util import forward
from cui.windows import WindowManager

class Window(object):
    def resize(dimensions):
        raise NotImplementedError()

    def move_cursor(self, row, col):
        raise NotImplementedError()

    def add_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def add_symbol(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def insert_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def clear_line(self):
        raise NotImplementedError()

    def clear_all(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()


@forward(lambda self: self._wm,
         ['replace_buffer',
          'new_window_set', 'has_window_set', 'delete_window_set', 'delete_window_set_by_name',
          'next_window_set', 'previous_window_set',
          'find_window', 'select_window', 'select_next_window', 'select_previous_window',
          'select_left_window', 'select_right_window', 'select_top_window', 'select_bottom_window',
          'delete_selected_window', 'delete_all_windows',
          'split_window_below', 'split_window_right', 'selected_window'],
         WindowManager)
class Frame(object):
    def __init__(self, core):
        self._core = core
        self.initialize()
        self._wm = WindowManager(self)

    def initialize(self):
        pass

    def close(self):
        self._wm.shutdown()

    def render(self):
        self._wm.render()

    def set_color(self, name, r, g, b):
        pass

    def set_background(self, bg_type):
        pass

    def get_dimensions(self):
        raise NotImplementedError()

    def create_window(self, dimensions):
        raise NotImplementedError()

    def update(self):
        pass

    def add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()

    def add_symbol(self, row, col, value, foreground='default', background='default', attributes=[]):
        raise NotImplementedError()
