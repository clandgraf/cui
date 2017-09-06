import atexit
import curses
import imp
import math
import traceback

from cui import keyreader
from cui.buffers import LogBuffer
from cui.logger import Logger
from cui.keymap import WithKeymap
from cui.util import deep_get, deep_put
from cui.colors import ColorCore
from cui.windows import WindowManager
from cui.singleton import Singleton, combine_meta_classes

__all__ = ['init_func', 'Core']

READ_TIMEOUT = 100


def init_func(fn):
    Core.__init_functions__.append(fn)
    return fn


def post_init_func(fn):
    Core.__post_init_functions__.append(fn)
    return fn


def update_func(fn):
    Core.__update_functions__.append(fn)
    return fn


def _init_state(core):
    core.def_variable(['tab-stop'], 4)
    core.def_variable(['core', 'read-timeout'], READ_TIMEOUT)


def log_window(core, w, depth=0):
    core.logger.log('%s%s%s' % ('> ' if w == core._wm._selected_window else '  ',
                                '  ' * depth,
                                (w['content']
                                 if w['wm_type'] == 'window' else
                                 "#<%s dimensions=%s>"
                                 % (w['wm_type'], w['dimensions']))))
    if w['wm_type'] != 'window':
        log_window(core, w['content'][0], depth=depth + 1)
        log_window(core, w['content'][1], depth=depth + 1)


def log_windows():
    c = Core()
    c.logger.clear()
    log_window(c, c._wm._root)


class Core(WithKeymap,
           ColorCore,
           metaclass=combine_meta_classes(Singleton, WithKeymap.__class__)):

    __init_functions__ = []
    __post_init_functions__ = []
    __update_functions__ = []

    __keymap__ = {
        "C-x C-c": lambda: Core().quit(),
        "C-x 2":   lambda: Core()._wm.split_window_below(),
        "C-x 3":   lambda: Core()._wm.split_window_right(),
        "C-x 0":   lambda: Core()._wm.delete_selected_window(),
        "C-x o":   lambda: Core()._wm.select_next_window(),
        "C-i":     lambda: Core().next_buffer(),
        "C-w":     log_windows,
        #'<up>':    lambda: Core()._wm.selected_window().scroll_up(),
        #'<down>':  lambda: Core()._wm.selected_window().scroll_down()
    }

    def __init__(self):
        super(Core, self).__init__()
        self.logger = Logger()
        self._state = {}
        self._screen = None
        self._buffers = [LogBuffer()]
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
        buffers = list(filter(lambda b: b.buffer_name() == buffer_name,  # XXX python3
                              self._buffers))
        if len(buffers) > 1:
            self.logger.log('Error: multiple buffers with same buffer_name')
            return
        elif len(buffers) == 0:
            self._buffers.insert(0, buffer_class(*args))
            self._wm.selected_window().set_buffer(self._buffers[0])
        else:
            self._wm.selected_window().set_buffer(buffers[0])

    def next_buffer(self):
        w = self._wm.selected_window()
        next_index = (self._buffers.index(w.buffer()) + 1) % len(self._buffers)
        w.set_buffer(self._buffers[next_index])

    def current_buffer(self):
        return self._wm.selected_window().buffer()

    def get_variable(self, path):
        return deep_get(self._state, path, return_none=False)

    def def_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=True)

    def set_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=False)

    def selected_window(self):
        return self._wm.selected_window()

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
            print(log_item)

    def _init_curses(self):
        self._screen = curses.initscr()
        curses.savetty()
        curses.raw(1)
        curses.noecho()
        curses.curs_set(0)
        self._screen.keypad(1)
        self._screen.timeout(self.get_variable(['core', 'read-timeout']))

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
                                   # This should be refactored
        self._wm.render()
        curses.doupdate()

    def _init_packages(self):
        for fn in Core.__init_functions__:
            try:
                fn()
            except:
                self.logger.log('init-function %s failed:\n%s'
                                % (fn.__name__, traceback.format_exc()))

    def _post_init_packages(self):
        for fn in Core.__post_init_functions__:
            try:
                fn()
            except:
                self.logger.log('post-init-function %s failed:\n%s'
                                % (fn.__name__, traceback.format_exc()))

    def _update_packages(self):
        for fn in Core.__update_functions__:
            try:
                fn()
            except:
                self.logger.log('update-function %s failed:\n%s'
                                % (fn.__name__, traceback.format_exc()))

    def _render_mini_buffer(self):
        max_y, max_x = self._screen.getmaxyx()
        self._screen.addstr(max_y - 1, 0, self._mini_buffer[:(max_x - 1)])
        self._screen.clrtoeol()

    def quit(self):
        self._running = False

    def input_delegate(self):
        return self._wm.selected_window().buffer()

    def run(self):
        self._init_curses()
        imp.load_source('cui._user_init', './init.py')
        self._init_packages()
        self._post_init_packages()
        self._running = True
        while self._running:
            self._update_packages()

            kc = keyreader.read_keychord(self._screen,
                                         self.get_variable(['core', 'read-timeout']))
            if kc is not None:
                if kc == keyreader.EVT_RESIZE:
                    self._wm.resize()
                else:
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
