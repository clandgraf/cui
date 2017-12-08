# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools

from cui.util import deep_put
from cui import core
from cui import symbols


class WindowBase(object):
    def __init__(self, screen, dimensions):
        self._core = core.Core()
        self._init_dimensions(dimensions)
        self._handle = screen.create_window(self._internal_dimensions)

    def _init_dimensions(self, dimensions):
        self._internal_dimensions = dimensions
        self.dimensions = self.get_content_dimensions(dimensions)

    @property
    def columns(self):
        return self.dimensions[1]

    @property
    def rows(self):
        return self.dimensions[0]

    def _update_dimensions(self, dimensions):
        self._internal_dimensions = dimensions
        self._handle.resize(dimensions)
        self.dimensions = self.get_content_dimensions(dimensions)
        return self

    def get_content_dimensions(self, dim):
        return (dim[0], dim[1], dim[2], dim[3])

    def _add_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.add_string(row, col, value, foreground, background, attributes)

    def _add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.add_char(row, col, value, foreground, background, attributes)

    def _add_symbol(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.add_symbol(row, col, value, foreground, background, attributes)

    def _render_line(self, line, soft_tabs, row, col=0,
                     foreground='default', background='default', attributes=[]):
        _col = col
        if isinstance(line, str):
            prepared = line.replace('\t', soft_tabs)[:(self.dimensions[1] - _col)]
            self._add_string(row, _col, prepared, foreground, background, attributes)
            _col += len(prepared)
        elif isinstance(line, int):
            self._add_char(row, _col, line, foreground, background, attributes)
            _col += 1
        elif isinstance(line, symbols.Symbol):
            self._add_symbol(row, _col, line, foreground, background, attributes)
            _col += 1
        elif isinstance(line, list):
            for sub_part in line:
                _col = self._render_line(sub_part, soft_tabs, row, _col,
                                         foreground, background, attributes)
        elif isinstance(line, dict):
            new_foreground = line.get('foreground', foreground)
            new_background = line.get('background', background)
            new_attributes = line.get('attributes', attributes)
            _col = self._render_line(line['content'], soft_tabs, row, _col,
                                     new_foreground, new_background, new_attributes)
        return _col


class MiniBufferWindow(WindowBase):
    def __init__(self, screen):
        super(MiniBufferWindow, self).__init__(
            screen,
            (1, screen.get_dimensions()[1], screen.get_dimensions()[0] - 1, 0))
        self._screen = screen

    def buffer(self):
        return self._mini_buffer

    def get_content_dimensions(self, dim):
        return (dim[0], dim[1] - 1, dim[2], dim[3])

    def resize(self):
        max_y, max_x = self._screen.get_dimensions()
        self._update_dimensions((1, max_x, max_y - 1, 0))

    def get_line(self):
        if self._core.mini_buffer_state:
            return self._core._mini_buffer.buffer_line(cursor=True)

        left, right = self._core.echo_area
        left = left.split('\n', 1)[0]
        right = right.split('\n', 1)[0]
        space = (self.dimensions[1] - len(left) - len(right))
        if space < 0:
            left = left[:(space - 4)] + '... '
        return [left, ' ' * max(0, space), right]

    def render(self):
        self._render_line(self.get_line(),
                          ' ' * self._core.get_variable(['tab-stop']),
                          0)
        self._handle.clear_line()
        self._handle.update()


class Window(WindowBase):
    def __init__(self, screen, dimensions, displayed_buffer):
        super(Window, self).__init__(screen, dimensions)
        self._buffer = None
        self.set_buffer(displayed_buffer)

    def get_content_dimensions(self, dim):
        return (dim[0] - 1, dim[1], dim[2], dim[3])

    def sync_state_to_buffer(self):
        for key in self._state:
            self._buffer._state['win/buf'][key] = self._state[key]

    def update_state(self, path, value):
        deep_put(self._state, path, value)

    def set_buffer(self, displayed_buffer):
        if displayed_buffer == self._buffer:
            return

        self._buffer = displayed_buffer
        self._state = self._buffer._state['win/buf'].copy()

    def buffer(self):
        return self._buffer

    def _render_mode_line(self, is_active):
        bname = self._buffer.buffer_name()
        mline = ('  %s' + (' ' * (self.dimensions[1] - len(bname) - 2))) % bname
        style = 'modeline_active' if is_active else 'modeline_inactive'
        self._handle.insert_string(self.dimensions[0], 0, mline, style, style, ['bold'])

    def _render_buffer(self):
        self._buffer.on_pre_render()
        soft_tabs = ' ' * self._core.get_variable(['tab-stop'])
        self._handle.move_cursor(0, 0)
        for idx, row in itertools.islice(enumerate(self._buffer.get_lines(self)),
                                          self.dimensions[0]):
            self._handle.move_cursor(idx, 0)
            _col = self._render_line(row, soft_tabs, idx)
            # Clear with background color
            if isinstance(row, dict):
                rest = self.dimensions[1] - _col
                if rest > 0:
                    self._add_string(idx, _col, rest * ' ', 'default', row.get('background'))
            else:
                self._handle.clear_line()
        self._handle.clear_all()

    def render(self, is_active):
        self._render_buffer()
        self._render_mode_line(is_active)
        self._handle.update()

    def __str__(self):
        return ("#<window \"%s\" dimensions=%s>"
                % (self._buffer.buffer_name(), str(self._internal_dimensions)))
