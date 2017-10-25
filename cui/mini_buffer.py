# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from cui.windows import WindowBase


class MiniBuffer(WindowBase):
    def __init__(self, screen):
        super(MiniBuffer, self).__init__(
            (1, screen.getmaxyx()[1], screen.getmaxyx()[0] - 1, 0))
        self._screen = screen

    def get_content_dimensions(self, dim):
        return (dim[0], dim[1] - 1, dim[2], dim[3])

    def resize(self):
        max_y, max_x = self._screen.getmaxyx()
        self._update_dimensions((1, max_x, max_y - 1, 0))

    def render(self):
        left, right = self._core.mini_buffer
        left = left.split('\n', 1)[0]
        right = right.split('\n', 1)[0]
        space = (self.dimensions[1] - len(left) - len(right))
        if space < 0:
            left = left[:(space - 4)] + '... '

        self._render_line([left, ' ' * max(0, space), right],
                          ' ' * self._core.get_variable(['tab-stop']),
                          0)
        self._handle.clrtoeol()
        self._handle.noutrefresh()
