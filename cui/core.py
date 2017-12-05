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

from cui import buffers
from cui.term import Frame
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


@contextlib.contextmanager
def context():
    yield Core()


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


class Logger(object):
    def __init__(self):
        self.messages = []

    def log(self, msg):
        if (len(self.messages) > 1000):
            self.messages.pop(0)
        self.messages.append(msg)

    def clear(self):
        self.messages = []


def echo_area_default():
    c = Core()
    return (c.last_message,
            '%s/%s' % (c._frame._wm.window_set_index + 1, c._frame._wm.window_set_count))


def complete_mini_buffer():
    core.Core().current_buffer()

class MiniBuffer(buffers.InputBuffer):
    def __init__(self, core):
        super(MiniBuffer, self).__init__()
        self._core = core

    @property
    def _buffer(self):
        return self._core.mini_buffer_state['buffer']

    @_buffer.setter
    def _buffer(self, value):
        self._core.mini_buffer_state['buffer'] = value

    @property
    def _cursor(self):
        return self._core.mini_buffer_state['cursor']

    @_cursor.setter
    def _cursor(self, value):
        self._core.mini_buffer_state['cursor'] = value

    @property
    def prompt(self):
        return self._core.mini_buffer_state.get('prompt', '')

    def on_auto_complete(self):
        if 'complete_function' not in self._core.mini_buffer_state:
            return super(MiniBuffer, self).on_auto_complete()
        return self._core.mini_buffer_state['complete_function'](self._buffer)

    def on_send_current_buffer(self, b):
        if self._core.mini_buffer_state:
            self._core.mini_buffer_state.get('submit_function', lambda _: None)(b)

# Runloop Control

class RunloopControl(Exception):
    def __init__(self):
        super(RunloopControl, self).__init__()


class RunloopCancel(RunloopControl):
    pass


class RunloopExit(RunloopControl):
    pass


class RunloopResult(RunloopControl):
    def __init__(self, result):
        super(RunloopResult, self).__init__()
        self.result = result


class RunloopState(object):
    def __init__(self):
        self.running = False
        self.current_keychord = []
        self.mini_buffer_state = None


def runloop_cancel():
    """
    Cancels the current runloop
    """
    raise RunloopCancel()


def runloop_result(result):
    raise RunloopResult(result)


def interactive(*args, **kwargs):
    def _interactive(fn):
        fn.__cui_interactive_args__ = args
        fn.__cui_interactive_kwargs__ = kwargs
        return fn
    return _interactive


# TODO can core._interactive be put into runloop_state???
@contextlib.contextmanager
def _interactive_context(handle_cancel):
    """
    This contextmanager ensures that RunloopCancel is always
    caught by the top-level interactive command that is executed
    """
    interactive_set = Core().set_interactive(True)
    try:
        if interactive_set or handle_cancel:
            try:
                yield
            except RunloopCancel:
                Core().message('Interactive cancelled.')
        else:
            yield
    finally:
        if interactive_set:
            Core().set_interactive(False)


def run_interactive(fn, handle_cancel=False):
    args = getattr(fn, '__cui_interactive_args__', [])
    kwargs = getattr(fn, '__cui_interactive_kwargs__', {})

    with _interactive_context(handle_cancel):
        return fn(*[arg() for arg in args],
                  **{kwarg: kwargs[kwarg]() for kwarg in kwargs})


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
        self._init_state()
        self.logger = Logger()
        self.io_selector = IOSelector(timeout=None, as_update_func=False)
        self.buffers = []
        self._mini_buffer = MiniBuffer(self)
        self._exit_handlers = []
        self._last_message = ""
        self._frame = None
        self._removed_update_funcs = []
        self._runloops = []
        self._running = False
        self._interactive = False
        atexit.register(self._at_exit)

    def _init_state(self):
        self._state = {}
        self.def_variable(['tab-stop'], 4)
        self.def_variable(['tree-tab'], 2)
        self.def_variable(['echo-area'], echo_area_default)

        from cui.buffers_std import LogBuffer
        self.def_variable(['default-buffer-class'], LogBuffer)

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

    def exception(self):
        """
        Call to log the last thrown exception exception.
        """
        exc_type, exc_value, exc_tb = sys.exc_info()
        cui.message(traceback.format_exception_only(exc_type, exc_value)[-1],
                    log_message=traceback.format_exc())

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

    @property
    def mini_buffer(self):
        return self._mini_buffer

    @property
    def mini_buffer_state(self):
        return self._runloops[0].mini_buffer_state

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
        """
        Switch to the previous buffer in the selected window.
        """
        selected_window = self.selected_window()
        selected_window.set_buffer(self._find_previous_buffer(selected_window.buffer()))

    def next_buffer(self):
        """
        Switch to the next buffer in the selected window.
        """
        selected_window = self.selected_window()
        selected_window.set_buffer(self._find_next_buffer(selected_window.buffer()))

    def kill_buffer_object(self, buffer_object):
        self.replace_buffer(buffer_object, self._find_next_buffer(buffer_object))
        self.buffers.remove(buffer_object)

        if len(self.buffers) == 0:  # Ensure we always have a buffer available
            cui.switch_buffer(self.get_variable('default-buffer-class'))

    def current_buffer(self):
        """
        Return the buffer in the selected window.
        """
        return self._mini_buffer if self.mini_buffer_state else self.selected_window().buffer()

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
    def echo_area(self):
        return self.get_variable(['echo-area'])()

    def bye(self):
        raise RunloopExit()

    def input_delegate(self):
        return self.current_buffer()

    def takes_input(self):
        return self.current_buffer().takes_input

    def dispatch_input(self, keychord, is_input):
        rl = self._runloops[0]
        if keychord == 'C-g':
            runloop_cancel()
        else:
            try:
                rl.current_keychord.append(keychord)

                fn = self.handle_input(rl.current_keychord)
                if hasattr(fn, '__call__'):
                    # current_keychord was handled via keymap
                    run_interactive(fn, handle_cancel=True)
                    rl.current_keychord = []
                elif is_input and len(rl.current_keychord) == 1:
                    # kc is direct input that was not handled and not beginning of sequence
                    self.current_buffer().insert_chars(keychord)
                    rl.current_keychord = []
                elif not fn:
                    # current_keychord is no suffix for
                    self.message('Unknown keychord: %s' % ' '.join(rl.current_keychord),
                                 show_log=False)
                    rl.current_keychord = []
                else:
                    self.message(' '.join(rl.current_keychord), show_log=False)
            except RunloopResult:
                raise
            except RunloopCancel:
                raise
            except RunloopExit:
                raise
            except:
                cui.exception()
                rl.current_keychord = []

    def activate_minibuffer(self, prompt, submit_fn, default='', complete_fn=None):
        self._runloops[0].mini_buffer_state = {
            'prompt': prompt,
            'buffer': '',
            'cursor': 0,
            'submit_function': submit_fn,
            'complete_function': complete_fn,
        }
        self.mini_buffer.reset_buffer(default)

    def set_interactive(self, interactive):
        has_set = not self._interactive and interactive
        self._interactive = interactive
        return has_set

    def runloop_enter(self, pre_loop_fn=None):
        self._runloops.insert(0, RunloopState())
        self._runloops[0].running = True
        if pre_loop_fn:
            pre_loop_fn()

        result = None
        try:
            while self._runloops[0].running:
                self._update_ui()
                self.io_selector.select()
        except RunloopResult as e:
            result = e.result
        except RunloopCancel:
            # In interactive mode top-level interactive handles cancel
            if self._interactive:
                raise
            self.message('Cancelled.')
        finally:
            self.io_selector.invalidate()
            self._runloops.pop(0)
        return result

    def run(self):
        self.buffers.append(self.get_variable(['default-buffer-class'])())
        self._frame = cui.term.curses.Frame(self)
        self._init_packages()
        self._post_init_packages()
        try:
            self._running = True
            while True:
                self.runloop_enter()
        except RunloopExit:
            self.message('Exiting.')
        finally:
            self._running = False
        self._run_exit_handlers()
