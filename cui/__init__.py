# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager

from cui import core
from cui.core import \
    has_run, init_func, update_func, is_update_func, remove_update_func, post_init_func, \
    add_exit_handler, remove_exit_handler, bye, \
    running, message, \
    def_colors, def_foreground, def_background, \
    def_variable, get_variable, set_variable, \
    def_hook, add_hook, remove_hook, run_hook, \
    register_waitable, unregister_waitable, \
    new_window_set, has_window_set, delete_window_set, delete_window_set_by_name, next_window_set, \
    previous_window_set, select_window, selected_window, delete_selected_window, \
    delete_all_windows, find_window, split_window_below, split_window_right, \
    get_buffer, select_buffer, switch_buffer, current_buffer, buffer_window, buffer_visible, \
    kill_current_buffer, next_buffer, previous_buffer
from cui import buffers
from cui.buffers import with_current_buffer

@contextmanager
def window_selected(window):
    old_window = selected_window()
    yield select_window(window)
    select_window(old_window)

def exec_in_buffer_visible(expr, buffer_class, *args, **kwargs):
    """
    Run expr in a window of the current set that displays the buffer,
    creating the buffer and window if necessary.

    Finds the first window in the active set that displays the buffer_object
    specified by buffer_class and args, and executes expr with this window
    selected. If the buffer does not exist, it is created.

    If the window is not exist, a window will be chosen based on the value of
    split_method. split_method must be a function that returns a window.
    The default value is split_window_below. If split_method
    is None the buffer is displayed in the currently selected window.

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    :param split_method:
        Method of creating the window. Pass as kwarg.
    """
    window, buffer_object = buffer_visible(buffer_class, *args, **kwargs)
    with window_selected(window):
        expr(buffer_object)

def exec_in_buffer_window(expr, buffer_class, *args):
    """
    Run expr in a window of the current set that displays the buffer,
    if that buffer exists and is displayed.

    Finds the first window in the active set that displays the buffer_object
    specified by buffer_class and args, and executes expr with this window
    selected. If no such window exists, expr is not executed

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    """
    buffer_object = get_buffer(buffer_class, *args)
    if buffer_object is None:
        return
    window = buffer_window(buffer_object, current_window_set=True)
    if window:
        with window_selected(window):
            expr(buffer_object)

def exec_if_buffer_exists(expr, buffer_class, *args):
    """
    Run expr with the buffer as argument.

    Finds the first window in the active set that displays the buffer_object
    specified by buffer_class and args, and executes expr with this window
    selected. If no such window exists, expr is not executed

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    """
    buffer_object = get_buffer(buffer_class, *args)
    if buffer_object:
        expr(buffer_object)

def kill_buffer(buffer_class, *args):
    """
    Remove the buffer.

    If the buffer, identified by class buffer_class and arguments args, exists,
    it will be removed from the list of buffers and replaced in all windows
    displaying it.

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    """
    exec_if_buffer_exists(lambda b: core.Core().kill_buffer(b),
                          buffer_class, *args)

__all__ = [
    'has_run',
    'init_func',
    'post_init_func',
    'update_func',
    'is_update_func',
    'remove_update_func',
    'add_exit_handler',
    'remove_exit_handler',

    'message',

    'def_colors',
    'def_foreground',
    'def_background',

    'def_variable',
    'get_variable',
    'set_variable',

    'def_hook',
    'add_hook',
    'remove_hook',
    'run_hook',

    'new_window_set',
    'has_window_set',
    'delete_window_set',
    'delete_window_set_by_name',

    'select_window',
    'selected_window',
    'delete_selected_window',
    'delete_all_windows',
    'window_selected',
    'find_window',
    'split_window_below',
    'split_window_right',

    'current_buffer',
    'select_buffer'
    'get_buffer',
    'switch_buffer',
    'buffer_window',
    'buffer_visible',
    'kill_buffer',
    'kill_current_buffer',
    'next_buffer',
    'previous_buffer',

    'exec_in_buffer_visible',
    'exec_if_buffer_exists',

    'buffers'
]
