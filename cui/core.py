import atexit
import curses
import traceback
import math

from cui.buffers import LogBuffer
from cui.cui_input import read_keychord
from cui.logger import Logger
from cui.keymap import WithKeymap
from cui.util import deep_get, deep_put
from cui.colors import ColorCore
from cui.windows import WindowManager

__all__ = ['init_func', 'Core']

READ_TIMEOUT = 100


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
        "C-w":     log_windows,

        '<up>':   lambda core: core._wm.current_window().scroll_up(),
        '<down>': lambda core: core._wm.current_window().scroll_down()
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

    def handle_input(self, keychords):
        return super(Core, self).handle_input(keychords)

    def input_delegate(self):
        return self._wm.current_window().buffer()

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
                    is_keychord_handled = self.handle_input(self._current_keychord)
                    if is_keychord_handled:
                        self._current_keychord = []
                    elif is_keychord_handled is None:
                        self._mini_buffer = 'Unknown keychord: %s' % ' '.join(self._current_keychord)
                        self._current_keychord = []
                except:
                    self.logger.log(traceback.format_exc())
                    self._current_keychord = []
                    raise

            self._update_ui()
        self._run_exit_handlers()
