import atexit
import curses
import traceback
import math

from cui.cui_buffers import LogBuffer
from cui.cui_input import read_keychord
from cui.logger import Logger
from cui.cui_keymap import WithKeymap
from cui.util import deep_get, deep_put

READ_TIMEOUT = 100


__all__ = ['init_func', 'Core']


class Window(object):
    def __init__(self, displayed_buffer, dimensions):
        self._internal_dimensions = dimensions
        self._handle = curses.newwin(*self._internal_dimensions)
        self._buffer = displayed_buffer
        self._buffer_first_row = 0
        self.dimensions = (dimensions[0] - 1,
                           dimensions[1],
                           dimensions[2],
                           dimensions[3])

    def update_dimensions(self, dimensions):
        self.dimensions = dimensions
        self._handle.resize(*self.dimensions)
        return self

    def set_buffer(self, displayed_buffer):
        self._buffer = displayed_buffer

    def buffer(self):
        return self._buffer

    def add_string(self, row, col, string,
                   foreground=curses.COLOR_WHITE,
                   background=curses.COLOR_BLACK):
        self._handle.addstr(row, col, string,
                            curses.color_pair(background << 3 | foreground))

    def _render_mode_line(self):
        bname = self._buffer.buffer_name()
        mline = ('  %s' + (' ' * (self.dimensions[1] - len(bname) - 3))) % bname
        self.add_string(self.dimensions[0], 0, mline,
                        curses.COLOR_BLACK, curses.COLOR_WHITE)

    def _render_buffer(self):
        self._handle.move(0, 0)
        for idx, row in enumerate(self._buffer.get_lines(self._buffer_first_row,
                                                         self.dimensions[0],
                                                         self.dimensions[1])):
            self.add_string(idx, 0, row)
        self._handle.clrtobot()

    def render(self):
        self._render_buffer()
        self._render_mode_line()
        self._handle.noutrefresh()


class WindowManager(object):
    def __init__(self, core, stdscr):
        """Foobah"""
        self.core = core

        self._root = self._init_root(stdscr)
        self._active_window = self._root

    def _init_root(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        dimensions = (max_y - 1, max_x - 1, 0, 0)
        return {
            'wm_type':    'window',
            'dimensions': dimensions,
            'content':    Window(self.core._buffers[0], dimensions),
            'parent':     None
        }

    def current_window(self):
        return self._active_window['content']

    def split_window_below(self):
        top_dimensions = (math.ceil(self._active_window['dimensions'][0] / 2.0),
                          self._active_window['dimensions'][1],
                          self._active_window['dimensions'][2],
                          self._active_window['dimensions'][3])
        bot_dimensions = (math.floor(self._active_window['dimensions'][0] / 2.0),
                          self._active_window['dimensions'][1],
                          self._active_window['dimensions'][2] +
                          math.ceil(self._active_window['dimensions'][0] / 2.0),
                          self._active_window['dimensions'][3])
        top = {
            'wm_type':    self._active_window['wm_type'],
            'dimensions': top_dimensions,
            'content':    self._active_window['content'].update_dimensions(top_dimensions),
            'parent':     self._active_window
        }
        bot = {
            'wm_type':    'window',
            'dimensions': bot_dimensions,
            'content':    Window(self._active_window['content'].buffer, bot_dimensions),
            'parent':     self._active_window
        }
        self._active_window['wm_type'] = 'bsplit'
        self._active_window['content'] = [top, bot]
        self._active_window = top

    def render(self):
        win_stack = [self._root]
        while win_stack:
            w = win_stack.pop()
            if w['wm_type'] == 'window':
                w['content'].render()
            else:
                win_stack.extend(w['content'])


def init_func(fn):
    Core.__init_functions__.append(fn)
    return fn


def update_func(fn):
    Core.__update_functions__.append(fn)
    return fn


class Core(WithKeymap):
    __init_functions__ = []
    __update_functions__ = []
    __keymap__ = {
        "C-x C-c": lambda core: core.quit(),
        "C-i":     lambda core: core.next_buffer()
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
        self._screen.timeout(READ_TIMEOUT)

        # Init Colors
        curses.start_color()
        for fg in range(0, curses.COLORS):
            for bg in range(0, curses.COLORS):
                idx = bg << 3 | fg
                if idx == 0:
                    continue
                curses.init_pair(idx, fg, bg)
        self._screen.bkgd(curses.color_pair(curses.COLOR_BLACK << 3 |
                                            curses.COLOR_WHITE))
        self._screen.refresh()
        self.add_exit_handler(self._quit_curses)
        self._wm = WindowManager(self, self._screen)

    def _quit_curses(self):
        curses.resetty()
        curses.endwin()

    def _update_ui(self):
        self._wm.render()
        self._render_mini_buffer()
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

            kc = read_keychord(self._screen)
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

            self._update_ui()
        self._run_exit_handlers()
