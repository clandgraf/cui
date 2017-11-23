# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import atexit
import contextlib
import functools
import math
import signal
import sys
import traceback

import cui
import cui.term.curses

from cui.term import Frame
from cui.logger import Logger
from cui.keymap import WithKeymap
from cui.util import deep_get, deep_put, forward
from cui.colors import ColorCore, ColorException
from cui.singleton import Singleton, combine_meta_classes
from cui.io_selector import IOSelector

__all__ = ['init_func', 'Core']

# =================================== API ======================================

# Package Lifecycle

def core_api(_globals, fn_name, keychords=None):
    wrapped_fn = functools.wraps(getattr(Core, fn_name))(
        (lambda *args, **kwargs: getattr(Core(), fn_name)(*args, **kwargs)))
    if keychords:
        Core.set_keychord(keychords, wrapped_fn)
    _globals[fn_name] = wrapped_fn
    return wrapped_fn


@contextlib.contextmanager
def core_api_ns(_globals):
    def _core_api(*args, **kwargs):
        core_api(_globals, *args, **kwargs)
    yield _core_api


def init_func(fn):
    """
    Decorator that marks a function as an initialization function.

    Functions decorated with init_func will be run after the first
    terminal has been initialized, and the init-file has been
    read. The function has_run may be used to determine if a function
    has been run.
    """
    fn.__has_run__ = False
    @functools.wraps(fn)
    def wrapper_fn(*args, **kwargs):
        if fn.__has_run__:
            cui.message('Warning: executing init_func %s more than once.' % fn)

        result = fn(*args, **kwargs)
        fn.__has_run__ = True
        return result

    Core.__init_functions__.append(wrapper_fn)
    return wrapper_fn


def post_init_func(fn):
    """
    Decorator that marks a function as a post-initialization function.

    Functions decorated with post_init_func will be executed after all init_funcs
    have been executed. The function has_run may be used to determine if a function
    has been run.
    """
    fn.__has_run__ = False
    @functools.wraps(fn)
    def wrapper_fn(*args, **kwargs):
        if fn.__has_run__:
            cui.message('Warning: executing post_init_func %s more than once.' % fn)

        result = fn(*args, **kwargs)
        fn.__has_run__ = True
        return result

    Core.__post_init_functions__.append(wrapper_fn)
    return wrapper_fn


def update_func(fn):
    Core.__update_functions__.append(fn)
    return fn

# ==============================================================================

def mini_buffer_default():
    c = Core()
    return (c.last_message,
            '%s/%s' % (c._frame._wm.window_set_index + 1, c._frame._wm.window_set_count))


def _init_state(core):
    core.def_variable(['tab-stop'], 4)
    core.def_variable(['tree-tab'], 2)
    core.def_variable(['mini-buffer-content'], mini_buffer_default)

    from cui.buffers_std import LogBuffer
    core.def_variable(['default-buffer-class'], LogBuffer)

@forward(lambda self: self._frame,
         ['replace_buffer',
          'new_window_set', 'has_window_set', 'delete_window_set', 'delete_window_set_by_name',
          'next_window_set', 'previous_window_set',
          'find_window', 'select_window', 'select_next_window', 'select_previous_window',
          'select_left_window', 'select_right_window', 'select_top_window', 'select_bottom_window',
          'delete_selected_window', 'delete_all_windows',
          'split_window_below', 'split_window_right', 'selected_window'],
         Frame)
class Core(WithKeymap,
           ColorCore,
           metaclass=combine_meta_classes(Singleton, WithKeymap.__class__)):

    __init_functions__ = []
    __post_init_functions__ = []
    __update_functions__ = []

    def __init__(self):
        super(Core, self).__init__()
        self._state = {}
        self.logger = Logger()
        self.io_selector = IOSelector(timeout=None, as_update_func=False)

        _init_state(self)
        self.buffers = []
        self._exit_handlers = []
        self._current_keychord = []
        self._last_message = ""
        self._running = False
        self._frame = None
        self._removed_update_funcs = []
        atexit.register(self._at_exit)

    def message(self, msg, show_log=True, log_message=None):
        """
        Display a message in the echo area and log it.

        :param msg: The message to be displayed
        :param show_log: Set to False, to avoid appending the message to the log
        :param log_message: Provide an alternative text for appending to the log
        """
        self._last_message = msg
        if log_message:
            self.logger.log(log_message)
        elif show_log:
            self.logger.log(msg)

    def get_buffer(self, buffer_class, *args):
        buffer_name = buffer_class.name(*args)
        buffers = list(filter(lambda b: b.buffer_name() == buffer_name,  # XXX python3
                              self.buffers))
        if len(buffers) > 1:
            raise Exception('Error: multiple buffers with same buffer_name')
        elif len(buffers) == 0:
            return None
        else:
            return buffers[0]

    def create_buffer(self, buffer_class, *args):
        buffer_object = self.get_buffer(buffer_class, *args)
        if buffer_object == None:
            buffer_object = buffer_class(*args)
            self.buffers.insert(0, buffer_object)
        return buffer_object

    def select_buffer(self, buffer_object):
        if buffer_object:
            self.selected_window().set_buffer(buffer_object)

    def _find_next_buffer(self, buffer_object):
        return self.buffers[(self.buffers.index(buffer_object) + 1) % len(self.buffers)]

    def _find_previous_buffer(self, buffer_object):
        return self.buffers[(self.buffers.index(buffer_object) - 1)]

    def previous_buffer(self):
        """Switch to the previous buffer in the selected window."""
        selected_window = self.selected_window()
        selected_window.set_buffer(self._find_previous_buffer(selected_window.buffer()))

    def next_buffer(self):
        """Switch to the next buffer in the selected window."""
        selected_window = self.selected_window()
        selected_window.set_buffer(self._find_next_buffer(selected_window.buffer()))

    def kill_buffer_object(self, buffer_object):
        self.replace_buffer(buffer_object, self._find_next_buffer(buffer_object))
        self.buffers.remove(buffer_object)

        if len(self.buffers) == 0:  # Ensure we always have a buffer available
            cui.switch_buffer(self.get_variable('default-buffer-class'))

    def current_buffer(self):
        """Return the buffer in the selected window."""
        return self.selected_window().buffer()

    def get_variable(self, path):
        return deep_get(self._state, path, return_none=False)

    def def_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=True)

    def set_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=False)

    def add_exit_handler(self, handler_fn):
        self._exit_handlers.append(handler_fn)

    def remove_exit_handler(self, handler_fn):
        self._exit_handlers.remove(handler_fn)

    def running(self):
        return self._running

    def _run_exit_handlers(self):
        while len(self._exit_handlers):
            try:
                self._exit_handlers.pop()()
            except:
                self.logger.log(traceback.format_exc())

    def _at_exit(self):
        self._run_exit_handlers()
        for log_item in self.logger.messages:
            print(log_item)

    def _init_packages(self):
        for fn in Core.__init_functions__:
            try:
                fn()
            except:
                self.message('init-function %s failed:\n%s'
                             % (fn.__name__, traceback.format_exc()))

    def _post_init_packages(self):
        for fn in Core.__post_init_functions__:
            try:
                fn()
            except:
                self.message('post-init-function %s failed:\n%s'
                             % (fn.__name__, traceback.format_exc()))

    def remove_update_func(self, fn):
        self._removed_update_funcs.append(fn)

    def is_update_func(self, fn):
        return fn in self.__update_functions__

    def _update_packages(self):
        # Process removed update functions
        while self._removed_update_funcs:
            self.__update_functions__.remove(
                self._removed_update_funcs.pop(0))

        for fn in Core.__update_functions__:
            try:
                fn()
            except:
                self.message('update-function %s failed:\n%s'
                             % (fn.__name__, traceback.format_exc()))

    def _update_ui(self):
        self._frame.render()

    @property
    def last_message(self):
        return self._last_message

    @property
    def mini_buffer(self):
        return self.get_variable(['mini-buffer-content'])()

    def bye(self):
        self._running = False

    def input_delegate(self):
        return self.selected_window().buffer()

    def takes_input(self):
        return self.current_buffer().takes_input

    def dispatch_input(self, keychord, is_input):
        try:
            self._current_keychord.append(keychord)
            is_keychord_handled = self.handle_input(self._current_keychord)
            if is_keychord_handled:
                # current_keychord was handled via keymap
                self._current_keychord = []
            elif is_input and len(self._current_keychord) == 1:
                # kc is direct input that was not handled and not beginning of sequence
                self.current_buffer().insert_chars(keychord)
                self._current_keychord = []
            elif is_keychord_handled is None:
                # current_keychord is no suffix for
                self.message('Unknown keychord: %s' % ' '.join(self._current_keychord),
                             show_log=False)
                self._current_keychord = []
            else:
                self.message(' '.join(self._current_keychord), show_log=False)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            cui.message(traceback.format_exception_only(exc_type, exc_value)[0],
                        log_message=traceback.format_exc())
            self._current_keychord = []

    def run(self):
        self.buffers.append(self.get_variable(['default-buffer-class'])())
        self._frame = cui.term.curses.Frame(self)
        self._init_packages()
        self._post_init_packages()
        self._running = True
        while self._running:
            self._update_ui()
            self.io_selector.select()

        self._run_exit_handlers()
