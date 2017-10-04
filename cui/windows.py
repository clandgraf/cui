import curses
import itertools
import math

from cui.util import deep_put
from cui import core

MIN_WINDOW_HEIGHT = 4
MIN_WINDOW_WIDTH  = 20


class WindowBase(object):
    def __init__(self, core, dimensions):
        self._core = core
        self._init_dimensions(dimensions)
        self._handle = curses.newwin(*self._internal_dimensions)

    def __del__(self):
        del self._handle

    def _init_dimensions(self, dimensions):
        self._internal_dimensions = dimensions
        self.dimensions = self.get_content_dimensions(dimensions)

    def _update_dimensions(self, dimensions):
        self._internal_dimensions = dimensions
        self._handle.resize(*dimensions[:2])
        self._handle.mvwin(*dimensions[2:])
        self.dimensions = self.get_content_dimensions(dimensions)
        return self

    def get_content_dimensions(self, dim):
        return (dim[0], dim[1], dim[2], dim[3])

    def _add_string(self, row, col, string, foreground='default', background='default', attributes=0):
        if len(string) == 0:
            return
        foreground = self._core.get_foreground_color(foreground) or self._core.get_foreground_color('default')
        self._handle.addstr(row, col, string,
                            attributes |
                            curses.color_pair(self._core.get_index_for_color(foreground,
                                                                             background)))

    def _render_line(self, line, soft_tabs, row, col=0,
                     foreground='default', background='default', attributes=0):
        _col = col
        if isinstance(line, str):
            prepared = line.replace('\t', soft_tabs)[:(self.dimensions[1] - _col)]
            self._add_string(row, _col, prepared, foreground, background, attributes)
            _col += len(prepared)
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
    def __init__(self, core, screen):
        super(MiniBuffer, self).__init__(
            core,
            (1, screen.getmaxyx()[1], screen.getmaxyx()[0] - 1, 0)
        )
        self._screen = screen

    def get_content_dimensions(self, dim):
        return (dim[0], dim[1] - 1, dim[2], dim[3])

    def resize(self):
        max_y, max_x = self._screen.getmaxyx()
        self._update_dimensions((1, max_x, max_y - 1, 0))

    def render(self):
        self._render_line(core.Core().mini_buffer.split('\n', 1)[0],
                          ' ' * core.Core().get_variable(['tab-stop']),
                          0)
        self._handle.clrtoeol()
        self._handle.noutrefresh()


class Window(WindowBase):
    def __init__(self, core, dimensions, displayed_buffer):
        super(Window, self).__init__(core, dimensions)
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
        attr  = curses.color_pair(self._core.get_index_for_color(
            self._core.get_foreground_color(style),
            style
        )) | curses.A_BOLD
        self._handle.insstr(self.dimensions[0], 0, mline, attr)

    def _render_buffer(self):
        self._buffer.on_pre_render()
        soft_tabs = ' ' * core.Core().get_variable(['tab-stop'])
        self._handle.move(0, 0)
        for idx, row in itertools.islice(enumerate(self._buffer.get_lines(self)),
                                          self.dimensions[0]):
            self._handle.move(idx, 0)
            _col = self._render_line(row, soft_tabs, idx)
            # Clear with background color
            if isinstance(row, dict):
                rest = self.dimensions[1] - _col
                if rest > 0:
                    self._add_string(idx, _col, rest * ' ', 'default', row.get('background'))
            else:
                self._handle.clrtoeol()
        self._handle.clrtobot()

    def render(self, is_active):
        self._render_buffer()
        self._render_mode_line(is_active)
        self._handle.noutrefresh()

    def __str__(self):
        return ("#<window \"%s\" dimensions=%s>"
                % (self._buffer.buffer_name(), str(self._internal_dimensions)))


class WindowManager(object):
    def __init__(self, core, screen):
        """Foobah"""
        self._core = core

        self._screen = screen
        self._windows = {}
        self._root = self._init_root()
        self.select_window(self._root['content'])

    def _init_root(self):
        max_y, max_x = self._screen.getmaxyx()
        dim = (max_y - 1, max_x, 0, 0)
        w = Window(self._core, dim, self._core.buffers[0])
        self._windows[id(w)] = {
            'wm_type':    'window',
            'dimensions': dim,
            'content':    w,
            'parent':     None
        }
        return self._windows[id(w)]

    def resize(self):
        max_y, max_x = self._screen.getmaxyx()
        self._root['dimensions'] = (max_y - 1, max_x, 0, 0)
        self._resize_window_tree(self._root)

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

    def _next_window(self):
        try:
            windows = self._iterate_windows(self._selected_window)
            next(windows)
            return next(windows)
        except:
            return self._selected_window

    def select_window(self, window):
        self._selected_window = self._windows[id(window)]
        self._selected_window['content'].sync_state_to_buffer()
        return window

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

    def selected_window(self):
        return self._selected_window['content']

    def select_next_window(self):
        self.select_window(self._next_window()['content'])

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

        new_win = Window(self._core, d2, self._selected_window['content'].buffer())
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

        # FIXME this is not optimal
        self.select_window(next(self._iterate_windows())['content'])

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
            self._screen.addch(row + r, col, ord('|'),
                               curses.color_pair(self._core.get_index_for_type('divider',
                                                                               'default')))

    def render(self):
        for w in self._iterate_windows(yield_window=False, yield_rsplit=True):
            self._render_rsplit(w)
        self._screen.noutrefresh()
        for w in self._iterate_windows():
            w['content'].render(w == self._selected_window)
