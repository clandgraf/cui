# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import math

from cui.util import deep_put, forward
from cui import core
from cui import symbols

from cui.windows.window import Window

MIN_WINDOW_HEIGHT = 4
MIN_WINDOW_WIDTH  = 20


class WindowSet(object):
    def __init__(self, screen):
        self._core = core.Core()
        self._screen = screen
        self._windows = {}
        self._root = self._init_root()
        self.select_window(self._root['content'])

    def _root_dimensions(self):
        max_y, max_x = self._screen.get_dimensions()
        return (max_y - 1, max_x, 0, 0)

    def _init_root(self):
        dim = self._root_dimensions()
        w = Window(self._screen, dim, self._core.buffers[0])
        self._windows[id(w)] = {
            'wm_type':    'window',
            'dimensions': dim,
            'content':    w,
            'parent':     None
        }
        return self._windows[id(w)]

    def resize(self):
        self._root['dimensions'] = self._root_dimensions()
        self._resize_window_tree(self._root)

    def replace_buffer(self, old_buffer_object, new_buffer_object):
        for w in (w['content'] for w in self._iterate_windows()):
            if w.buffer() == old_buffer_object:
                w.set_buffer(new_buffer_object)

    def _iterate_windows(self, first_window=None,
                         yield_window=True, yield_rsplit=False, yield_bsplit=False):
        win_stack = [self._root]
        win_queue = []
        at_last = first_window is not None

        def _handle_window(w):
            if at_last:
                win_queue.append(w)
            else:
                yield w

        while win_stack:
            w = win_stack.pop(0)

            if at_last and w == first_window:
                at_last = False

            if w['wm_type'] == 'window':
                if yield_window:
                    yield from _handle_window(w)
            else:
                win_stack[0:0] = w['content'] # extend at front
                if yield_rsplit and w['wm_type'] == 'rsplit':
                    yield from _handle_window(w)
                if yield_bsplit and w['wm_type'] == 'bsplit':
                    yield from _handle_window(w)

        while win_queue:
            yield win_queue.pop(0)

    def _neighbouring_window(self, direction, use=None):
        # TODO make direction optional
        # Provide line/col advice when descending, buffers may provide if available
        rdirection = (direction + 1) % 2
        current = self._selected_window
        while True:
            if current['parent'] is None:
                # Is first/last leaf in tree
                break
            elif current == current['parent']['content'][rdirection] and \
                 (use is None or use == current['parent']['wm_type']):
                # Is first/last leaf in split
                current = current['parent']['content'][direction]
                break
            current = current['parent']

        while current['wm_type'] != 'window':
            current = current['content'][rdirection]

        return current

    def select_window(self, window):
        """Return window or None if not part of this WindowSet."""
        _window = self._windows.get(id(window))
        if _window:
            self._selected_window = _window
            self._selected_window['content'].sync_state_to_buffer()
        return _window['content'] if _window else None

    def selected_window(self):
        return self._selected_window['content']

    def _next_window(self):
        return self._neighbouring_window(direction=1)

    def select_next_window(self):
        self.select_window(self._next_window()['content'])

    def _previous_window(self):
        return self._neighbouring_window(direction=0)

    def select_previous_window(self):
        self.select_window(self._previous_window()['content'])

    def select_left_window(self):
        return self.select_window(
            self._neighbouring_window(direction=0, use='rsplit')['content'])

    def select_right_window(self):
        return self.select_window(
            self._neighbouring_window(direction=1, use='rsplit')['content'])

    def select_top_window(self):
        return self.select_window(
            self._neighbouring_window(direction=0, use='bsplit')['content'])

    def select_bottom_window(self):
        return self.select_window(
            self._neighbouring_window(direction=1, use='bsplit')['content'])

    # def divider_up(self, window):
    #     _window = self._windows[id(window)]
    #     while _window and _window['wm_type'] != 'bsplit':
    #         _window = _window['parent']
    #     new_size = _window['content'][0]['dimensions'][0] - 1
    #     if (new_size < )
    #     dim = self._get_vertical_dimensions(_window['dimensions'],
    #                                         new_size)
    #     for i in range(0, 2):
    #         _window['content'][i]['dimensions'] = dim[i]
    #         self._resize_window_tree(_window['content'][i])

    def find_window(self, predicate):
        for w in self._iterate_windows():
            if predicate(w['content']):
                return w['content']
        return None

    def _get_vertical_dimensions(self, parent_dimension, first_size):
        return (
            (first_size,
             parent_dimension[1],
             parent_dimension[2],
             parent_dimension[3]),
            (parent_dimension[0] - first_size,
             parent_dimension[1],
             parent_dimension[2] + first_size,
             parent_dimension[3])
        )

    def _get_vertical_dimensions_by_ratio(self, parent_dimension, ratio=.5):
        return self._get_vertical_dimensions(parent_dimension,
                                             int(math.ceil(parent_dimension[0] * ratio)))

    def _get_horizontal_dimensions(self, parent_dimension, first_size):
        return (
            (parent_dimension[0],
             first_size,
             parent_dimension[2],
             parent_dimension[3]),
            (parent_dimension[0],
             parent_dimension[1] - first_size - 1,
             parent_dimension[2],
             parent_dimension[3] + first_size + 1)
        )

    def _get_horizontal_dimensions_by_ratio(self, parent_dimension, ratio=.5):
        return self._get_horizontal_dimensions(parent_dimension,
                                               int(math.floor(parent_dimension[1] * ratio)))

    def _get_dimensions(self, split_type, parent_dimension, ratio=.5):
        return (self._get_vertical_dimensions_by_ratio
                if split_type == 'bsplit' else
                self._get_horizontal_dimensions_by_ratio)(parent_dimension, ratio)

    def _check_dimension(self, d):
        return d[0] < MIN_WINDOW_HEIGHT or d[1] < MIN_WINDOW_WIDTH

    def _split_window(self, split_type):
        d1, d2 = self._get_dimensions(split_type, self._selected_window['dimensions'])
        if self._check_dimension(d1) or self._check_dimension(d2):
            self._core.message("Can not split. Dimensions too small.")
            return None

        new_win = Window(self._screen, d2, self._selected_window['content'].buffer())
        w1 = {
            'wm_type':    self._selected_window['wm_type'],
            'dimensions': d1,
            'content':    self._selected_window['content']._update_dimensions(d1),
            'parent':     self._selected_window
        }
        w2 = {
            'wm_type':    'window',
            'dimensions': d2,
            'content':    new_win,
            'parent':     self._selected_window
        }
        self._windows[id(w1['content'])] = w1
        self._windows[id(new_win)] = w2

        self._selected_window['wm_type'] = split_type
        self._selected_window['content'] = [w1, w2]
        self.select_window(w1['content'])
        return w2['content']

    def split_window_below(self):
        """
        Split this window and create a new one below it.
        """
        return self._split_window('bsplit')

    def split_window_right(self):
        """
        Split this window and create a new one to the right of it.
        """
        return self._split_window('rsplit')

    def delete_selected_window(self):
        # Do not delete last window
        if self._root == self._selected_window:
            self._core.message("Can not delete last window.")
            return

        next_window = self._next_window()['content']
        del self._windows[id(self._selected_window['content'])]

        parent = self._selected_window['parent']
        new_parent_content = parent['content'][1] \
                             if parent['content'][0] == self._selected_window else \
                             parent['content'][0]

        parent['wm_type'] = new_parent_content['wm_type']
        parent['content'] = new_parent_content['content']
        if parent['wm_type'] != 'window':
            parent['content'][0]['parent'] = parent
            parent['content'][1]['parent'] = parent
        else:
            self._windows[id(parent['content'])] = parent
        self._resize_window_tree(parent)

        # FIXME this should be previous window
        self.select_window(next_window)

    def delete_all_windows(self):
        self._root = self._selected_window
        self._root['parent'] = None
        self._windows = {id(self._root['content']): self._root}
        self.resize()

    def _resize_window_tree(self, window):
        if window['wm_type'] == 'window':
            window['content']._update_dimensions(window['dimensions'])
        else:
            d1, d2 = self._get_dimensions(window['wm_type'], window['dimensions'])
            window['content'][0]['dimensions'] = d1
            self._resize_window_tree(window['content'][0])
            window['content'][1]['dimensions'] = d2
            self._resize_window_tree(window['content'][1])

    def _render_rsplit(self, w):
        col = w['dimensions'][3] + w['content'][0]['dimensions'][1]
        row = w['dimensions'][2]
        for r in range(0, w['dimensions'][0]):
            self._screen.add_symbol(row + r, col, symbols.SYM_VLINE, 'divider', 'default')

    def render(self):
        for w in self._iterate_windows(yield_window=False, yield_rsplit=True):
            self._render_rsplit(w)
        self._screen.update()
        for w in self._iterate_windows():
            w['content'].render(w == self._selected_window)
