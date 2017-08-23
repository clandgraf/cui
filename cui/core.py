import atexit
import curses
import traceback
import math

from cui.buffers import LogBuffer
from cui.cui_input import read_keychord
from cui.logger import Logger
from cui.cui_keymap import WithKeymap
from cui.util import deep_get, deep_put
from cui.colors import ColorCore

__all__ = ['init_func', 'Core']

READ_TIMEOUT = 100

MIN_WINDOW_HEIGHT = 4
MIN_WINDOW_WIDTH  = 20


class Window(object):
    def __init__(self, core, displayed_buffer, dimensions):
        self._core = core
        self._internal_dimensions = dimensions
        self._handle = curses.newwin(*self._internal_dimensions)
        self._buffer = displayed_buffer
        self._buffer_first_row = 0
        self.dimensions = (dimensions[0] - 1,
                           dimensions[1],
                           dimensions[2],
                           dimensions[3])

    def update_dimensions(self, dimensions):
        self._internal_dimensions = dimensions
        self._handle.resize(*dimensions[:2])
        self._handle.mvwin(*dimensions[2:])
        self.dimensions = (dimensions[0] - 1,
                           dimensions[1],
                           dimensions[2],
                           dimensions[3])
        return self

    def set_buffer(self, displayed_buffer):
        self._buffer = displayed_buffer

    def buffer(self):
        return self._buffer

    def add_string(self, row, col, string, foreground=None, background='default', attributes=0):
        if foreground is None:
            foreground = self._core.get_foreground_color('default')
        self._handle.addstr(row, col, string,
                            attributes |
                            curses.color_pair(self._core.get_index_for_color(foreground,
                                                                             background)))

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
        self._handle.move(0, 0)
        for idx, row in enumerate(self._buffer.get_lines(self._buffer_first_row,
                                                         self.dimensions[0],
                                                         self.dimensions[1])):
            self.add_string(idx, 0, row)
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
        self._root = self._init_root(screen)
        self._active_window = self._root

    def _init_root(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        dimensions = (max_y - 1, max_x, 0, 0)
        return {
            'wm_type':    'window',
            'dimensions': dimensions,
            'content':    Window(self._core, self._core._buffers[0], dimensions),
            'parent':     None
        }

    def windows(self, yield_window=True, yield_rsplit=False):
        win_stack = [self._root]
        while win_stack:
            w = win_stack.pop(0)
            if w['wm_type'] == 'window':
                if yield_window:
                    yield w
            else:
                win_stack[0:0] = w['content'] # extend at front
                if yield_rsplit and w['wm_type'] == 'rsplit':
                    yield w

    def window_list(self):
        return list(self.windows())

    def current_window(self):
        return self._active_window['content']

    def next_window(self):
        windows = self.windows()
        first_window = None
        try:
            first_window = current_window = windows.next()
            while current_window != self._active_window:
                current_window = windows.next()
            return windows.next()
        except StopIteration:
            return first_window

    def select_next_window(self):
        self._active_window = self.next_window()

    def _get_vertical_dimensions(self, parent_dimension):
        # TODO ratio
        return (
            (int(math.ceil(parent_dimension[0] / 2.0)),
             parent_dimension[1],
             parent_dimension[2],
             parent_dimension[3]),
            (int(math.floor(parent_dimension[0] / 2.0)),
             parent_dimension[1],
             parent_dimension[2] +
             int(math.ceil(parent_dimension[0] / 2.0)),
             parent_dimension[3])
        )

    def _get_horizontal_dimensions(self, parent_dimension):
        # TODO ratio
        return (
            (parent_dimension[0],
             int(math.floor(parent_dimension[1] * .5)),
             parent_dimension[2],
             parent_dimension[3]),
            (parent_dimension[0],
             int(math.ceil(parent_dimension[1] * .5)) - 1,
             parent_dimension[2],
             parent_dimension[3] +
             int(math.floor(parent_dimension[1] * .5)) + 1)
        )

    def _get_dimensions(self, split_type, parent_dimension):
        return (self._get_vertical_dimensions
                if split_type == 'bsplit' else
                self._get_horizontal_dimensions)(parent_dimension)

    def _check_dimension(self, d):
        return d[0] < MIN_WINDOW_HEIGHT or d[1] < MIN_WINDOW_WIDTH

    def _split_window(self, split_type):
        d1, d2 = self._get_dimensions(split_type, self._active_window['dimensions'])
        if self._check_dimension(d1) or self._check_dimension(d2):
            self._core.message("Can not split. Dimensions too small.")
            return

        w1 = {
            'wm_type':    self._active_window['wm_type'],
            'dimensions': d1,
            'content':    self._active_window['content'].update_dimensions(d1),
            'parent':     self._active_window
        }
        w2 = {
            'wm_type':    'window',
            'dimensions': d2,
            'content':    Window(self._core, self._active_window['content'].buffer(), d2),
            'parent':     self._active_window
        }
        self._active_window['wm_type'] = split_type
        self._active_window['content'] = [w1, w2]

        assert(w1['parent'] == self._active_window)
        assert(w1['parent']['content'][0] == w1)
        assert(w2['parent'] == self._active_window)
        assert(w2['parent']['content'][1] == w2)

        self._active_window = w1

    def split_window_below(self):
        self._split_window('bsplit')

    def split_window_right(self):
        self._split_window('rsplit')

    def delete_current_window(self):
        # Do not delete last window
        if self._root == self._active_window:
            self._core.message("Can not delete last window.")
            return

        parent = self._active_window['parent']
        new_parent_content = parent['content'][1] \
                             if parent['content'][0] == self._active_window else \
                             parent['content'][0]

        parent['wm_type'] = new_parent_content['wm_type']
        parent['content'] = new_parent_content['content']
        if parent['wm_type'] != 'window':
            parent['content'][0]['parent'] = parent
            parent['content'][1]['parent'] = parent
        self._resize_window_tree(parent)

        # FIXME this is not optimal
        self._active_window = self.windows().next()

    def _resize_window_tree(self, window):
        if window['wm_type'] == 'window':
            window['content'].update_dimensions(window['dimensions'])
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
                               curses.color_pair(self._core.get_index_for_type('default',
                                                                               'default')))

    def render(self):
        for w in self.windows(yield_window=False, yield_rsplit=True):
            self._render_rsplit(w)
        self._screen.noutrefresh()
        for w in self.windows():
            w['content'].render(w == self._active_window)


def init_func(fn):
    Core.__init_functions__.append(fn)
    return fn


def update_func(fn):
    Core.__update_functions__.append(fn)
    return fn


def _init_state(core):
    core.set_state(['tab-stop'], 4)
    core.set_state(['core', 'read-timeout'], READ_TIMEOUT)


def log_window(core, w, depth=0):
    core.logger.log('%s%s%s' % ('> ' if w == core._wm._active_window else '  ',
                                '  ' * depth,
                                (w['content']
                                 if w['wm_type'] == 'window' else
                                 "#<%s dimensions=%s>"
                                 % (w['wm_type'], w['dimensions']))))
    if w['wm_type'] != 'window':
        log_window(core, w['content'][0], depth=depth + 1)
        log_window(core, w['content'][1], depth=depth + 1)


def log_windows(core):
    core.logger.clear()
    log_window(core, core._wm._root)


class Core(WithKeymap, ColorCore):
    __init_functions__ = []
    __update_functions__ = []
    __keymap__ = {
        "C-x C-c": lambda core: core.quit(),
        "C-x 2":   lambda core: core._wm.split_window_below(),
        "C-x 3":   lambda core: core._wm.split_window_right(),
        "C-x 0":   lambda core: core._wm.delete_current_window(),
        "C-x o":   lambda core: core._wm.select_next_window(),
        "C-i":     lambda core: core.next_buffer(),
        "C-w":     log_windows
    }

    def __init__(self, cui_init):
        super(Core, self).__init__()
        self.logger = Logger()
        self._cui_init = cui_init
        self._state = {}
        self._screen = None
        self._buffers = [LogBuffer(self)]
        self._exit_handlers = []
        self._current_keychord = []
        self._mini_buffer = ""
        self._running = False
        self._wm = None
        atexit.register(self._at_exit)
        _init_state(self)

    def message(self, msg):
        self._mini_buffer = msg

    def switch_buffer(self, buffer_class, *args):
        buffer_name = buffer_class.name(*args)
        buffers = filter(lambda b: b.buffer_name() == buffer_name,
                         self._buffers)
        if len(buffers) > 1:
            self.logger.log('Error: multiple buffers with same buffer_name')
            return
        elif len(buffers) == 0:
            self._buffers.insert(0, buffer_class(self, *args))
            self._wm.current_window().set_buffer(self._buffers[0])
        else:
            self._wm.current_window().set_buffer(buffers[0])

    def next_buffer(self):
        w = self._wm.current_window()
        next_index = (self._buffers.index(w.buffer()) + 1) % len(self._buffers)
        w.set_buffer(self._buffers[next_index])

    def _current_buffer(self):
        return self._buffers[self._current_buffer_index]

    def state(self, path):
        return deep_get(self._state, path)

    def set_state(self, path, value):
        deep_put(self._state, path, value)

    def add_exit_handler(self, handler_fn):
        self._exit_handlers.append(handler_fn)

    def remove_exit_handler(self, handler_fn):
        self._exit_handlers.remove(handler_fn)

    def _run_exit_handlers(self):
        while len(self._exit_handlers):
            self._exit_handlers.pop()()

    def _at_exit(self):
        self._run_exit_handlers()
        for log_item in self.logger.messages:
            print log_item

    def _init_packages(self):
        for fn in Core.__init_functions__:
            try:
                fn(self)
            except:
                self.logger.log('init-function %s failed:\n%s'
                                % (fn.__name__, traceback.format_exc()))

    def _init_curses(self):
        self._screen = curses.initscr()
        curses.savetty()
        curses.raw(1)
        curses.noecho()
        curses.curs_set(0)
        self._screen.keypad(1)
        self._screen.timeout(self.state(['core', 'read-timeout']))

        # Init Colors
        curses.start_color()
        self._init_colors()
        self._screen.bkgd(self.get_index_for_type())
        self._screen.refresh()
        self.add_exit_handler(self._quit_curses)
        self._wm = WindowManager(self, self._screen)

    def _quit_curses(self):
        curses.resetty()
        curses.endwin()

    def _update_ui(self):
        self._render_mini_buffer() # This relies on noutrefresh called in _wm.render
        self._wm.render()
        curses.doupdate()

    def _update_packages(self):
        for fn in Core.__update_functions__:
            try:
                fn(self)
            except:
                self.logger.log('update-function %s failed:\n%s'
                                % (fn.__name__, traceback.format_exc()))

    def _render_mini_buffer(self):
        max_y, max_x = self._screen.getmaxyx()
        self._screen.addstr(max_y - 1, 0, self._mini_buffer[:(max_x - 1)])
        self._screen.clrtoeol()

    def quit(self):
        self._running = False

    def run(self):
        self._init_curses()
        self._init_packages()
        self._cui_init.initialize(self)
        self._running = True
        while self._running:
            self._update_packages()

            kc = read_keychord(self._screen, self.state(['core', 'read-timeout']))
            if kc is not None:
                try:
                    self._current_keychord.append(kc)
                    self._mini_buffer = ' '.join(self._current_keychord)
                    is_keychord_handled = self._wm.current_window().buffer().handle_input(self._current_keychord)
                    if is_keychord_handled is None:
                        is_keychord_handled = self.handle_input(self._current_keychord)
                        if is_keychord_handled is None:
                            self._mini_buffer = 'Unknown keychord: %s' % ' '.join(self._current_keychord)
                            self._current_keychord = []

                    if is_keychord_handled:
                        self._current_keychord = []
                except:
                    self.logger.log(traceback.format_exc())
                    self._current_keychord = []
                    raise

            self._update_ui()
        self._run_exit_handlers()
