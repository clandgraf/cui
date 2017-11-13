# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import math

from cui.util import deep_put, forward
from cui import core

MIN_WINDOW_HEIGHT = 4
MIN_WINDOW_WIDTH  = 20


class WindowBase(object):
    def __init__(self, screen, dimensions):
        self._core = core.Core()
        self._init_dimensions(dimensions)
        self._handle = screen.create_window(self._internal_dimensions)

    def __del__(self):
        del self._handle

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


class MiniBuffer(WindowBase):
    def __init__(self, screen):
        super(MiniBuffer, self).__init__(
            screen,
            (1, screen.get_dimensions()[1], screen.get_dimensions()[0] - 1, 0))
        self._screen = screen

    def get_content_dimensions(self, dim):
        return (dim[0], dim[1] - 1, dim[2], dim[3])

    def resize(self):
        max_y, max_x = self._screen.get_dimensions()
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


class WindowSet(object):
    def __init__(self, screen):
        self._core = core.Core()
        self._screen = screen
        self._windows = {}
        self._root = self._init_root()
        self.select_window(self._root['content'])

    def _init_root(self):
        max_y, max_x = self._screen.get_dimensions()
        dim = (max_y - 1, max_x, 0, 0)
        w = Window(self._screen, dim, self._core.buffers[0])
        self._windows[id(w)] = {
            'wm_type':    'window',
            'dimensions': dim,
            'content':    w,
            'parent':     None
        }
        return self._windows[id(w)]

    def resize(self):
        max_y, max_x = self._screen.get_dimensions()
        self._root['dimensions'] = (max_y - 1, max_x, 0, 0)
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
        return self._split_window('bsplit')

    def split_window_right(self):
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
            # TODO how to map curses.ACS_VLINE
            self._screen.add_char(row + r, col, '|', 'divider', 'default')

    def render(self):
        for w in self._iterate_windows(yield_window=False, yield_rsplit=True):
            self._render_rsplit(w)
        self._screen.update()
        for w in self._iterate_windows():
            w['content'].render(w == self._selected_window)


@forward(lambda self: self.active_window_set(),
         ['selected_window',
          'select_next_window',
          'select_previous_window',
          'select_left_window',
          'select_right_window',
          'select_top_window',
          'select_bottom_window',
          'split_window_below',
          'split_window_right',
          'delete_selected_window',
          'delete_all_windows'])
class WindowManager(object):
    def __init__(self, screen):
        self._screen = screen
        self._window_sets = [WindowSet(screen)]
        self._named_window_sets = {}
        self._active_window_set = 0
        self._mini_buffer_win = MiniBuffer(self._screen)

    def shutdown(self):
        self._mini_buffer_win = None
        # TODO close all window sets

    @property
    def window_set_index(self):
        return self._active_window_set

    @property
    def window_set_count(self):
        return len(self._window_sets)

    def active_window_set(self):
        return self._window_sets[self._active_window_set]

    def new_window_set(self, name=None):
        if name and name in self._named_window_sets:
            return self._window_sets[self._named_window_sets[name]]

        idx = self._active_window_set + 1
        ws = WindowSet(self._screen)
        self._window_sets.insert(idx, ws)
        if name:
            self._named_window_sets[name] = idx
        self._active_window_set += 1
        return ws

    def has_window_set(self, name):
        return name in self._named_window_sets

    def _delete_window_set_by_index(self, index):
        if index == 0:
            core.message('Can not delete window set 1.')
            return

        self._named_window_sets = {k:v for k, v in self._named_window_sets.items()
                                   if v != index}
        self._window_sets.pop(index)
        if index >= self._active_window_set:
            self._active_window_set -= 1

    def delete_window_set(self):
        self._delete_window_set_by_index(self._active_window_set)

    def delete_window_set_by_name(self, name):
        index = self._named_window_sets.get(name)
        if index:
            self._delete_window_set_by_index(index)

    def next_window_set(self):
        self._active_window_set += 1
        self._active_window_set %= len(self._window_sets)

    def previous_window_set(self):
        self._active_window_set += len(self._window_sets) - 1
        self._active_window_set %= len(self._window_sets)

    def resize(self):
        self._mini_buffer_win.resize()
        for ws in self._window_sets:
            ws.resize()

    def render(self):
        self.active_window_set().render()
        self._mini_buffer_win.render()

    def replace_buffer(self, old_buffer_object, new_buffer_object):
        for ws in self._window_sets:
            ws.replace_buffer(old_buffer_object, new_buffer_object)

    def select_window(self, window):
        for idx, ws in enumerate(self._window_sets):
            w = ws.select_window(window)
            if w:
                self._active_window_set = idx
                return w

    def find_window(self, predicate, current_window_set=False):
        if current_window_set:
            return self.active_window_set().find_window(predicate)
        for ws in self._window_sets:
            w = ws.find_window(predicate)
            if w:
                return w
        return None
