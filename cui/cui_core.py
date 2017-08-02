import atexit
import curses
import traceback

from cui.cui_buffers import LogBuffer
from cui.cui_input import read_keychord
from cui.cui_logger import Logger
from cui.cui_constants import COLOR_DEFAULT, COLOR_HIGHLIGHTED

READ_TIMEOUT = 100


__all__ = ['init_func', 'Core']


def init_func(fn):
    Core.__init_functions__.append(fn)
    return fn


class Core(object):
    __init_functions__ = []

    def __init__(self):
        self.logger = Logger()
        self._state = {}
        self._screen = None
        self._buffers = [LogBuffer(self)]
        self._exit_handlers = []
        atexit.register(self._run_exit_handlers)

    def add_buffer(self, b):
        self._buffers.append(b)

    def _current_buffer(self):
        return self._buffers[0]

    def state(self, path):
        st = self._state
        for key in path:
            st = st.get(key)
            if st is None:
                return None
        return st

    def set_state(self, path, value):
        st = self._state
        for key in path[:-1]:
            if key not in st:
                st[key] = {}
        st[path[-1]] = value

    def add_exit_handler(self, handler_fn):
        self._exit_handlers.append(handler_fn)

    def remove_exit_handler(self, handler_fn):
        self._exit_handlers.remove(handler_fn)

    def _run_exit_handlers(self):
        for eh in self._exit_handlers:
            eh()

        # if an exception occured let's print it out
        # to see if it is the reason for a crash
        print traceback.format_exc()

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

        curses.start_color()
        curses.init_pair(COLOR_DEFAULT, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_HIGHLIGHTED, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self._screen.bkgd(curses.color_pair(COLOR_DEFAULT))
        self._screen.refresh()
        self.add_exit_handler(self._quit_curses)

    def _quit_curses(self):
        curses.resetty()
        curses.endwin()
        self.remove_exit_handler(self._quit_curses)

    def _update_ui(self):
        #maxy, maxx = stdscr.getmaxyx()
        #pad = curses.newpad(10000, 3000)
        self._current_buffer().render(self._screen)

    def run(self):
        self._init_packages()
        self._init_curses()
        while True:
            self._update_ui()

            kc = read_keychord(self._screen)
            if kc is None:
                continue
            if kc == 'C-q':
                break
            else:
                self._current_buffer().handle_input(kc)
        self._quit_curses()
