# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

from cui.core import \
    core_api_ns, Core, \
    init_func, update_func, post_init_func
from cui.colors import ColorException

with core_api_ns(globals()) as core_api:
    core_api('message')
    core_api('is_update_func')
    core_api('remove_update_func')
    core_api('add_exit_handler')
    core_api('remove_exit_handler')
    core_api('running')
    core_api('bye',                    'C-x C-c')

    core_api('def_variable')
    core_api('get_variable')
    core_api('set_variable')

    core_api('current_buffer')
    core_api('create_buffer')
    core_api('select_buffer')
    core_api('get_buffer')
    core_api('kill_buffer_object')
    core_api('previous_buffer',        'S-<tab>')
    core_api('next_buffer',            '<tab>')

    core_api('new_window_set',         'C-x 5 2')
    core_api('has_window_set')
    core_api('delete_window_set',      'C-x 5 0')
    core_api('delete_window_set_by_name')
    core_api('next_window_set',        'C-M-n')
    core_api('previous_window_set',    'C-M-p')
    core_api('split_window_below',     'C-x 2')
    core_api('split_window_right',     'C-x 3')
    core_api('select_window')
    core_api('find_window')
    core_api('selected_window')
    core_api('select_next_window',     'M-n')
    core_api('select_previous_window', 'M-p')
    core_api('select_left_window',     'M-<left>')
    core_api('select_right_window',    'M-<right>')
    core_api('select_top_window',      'M-<up>')
    core_api('select_bottom_window',   'M-<down>')
    core_api('delete_all_windows',     'C-x 1')
    core_api('delete_selected_window', 'C-x 0')


def set_global_key(keychord, fn):
    Core.set_keychord(keychord, fn)


def set_local_key(buffer_class, keychord, fn):
    buffer_class.set_keychord(keychord, fn)


def global_key(keychord):
    def _global_key(fn):
        set_global_key(keychord, fn)
        return fn
    return _global_key


def has_run(fn):
    """Determine if an init_func or a post_init_func has been successfully executed."""
    return getattr(fn, '__has_run__')

# Input Waitables

def register_waitable(waitable, handler):
    return Core().io_selector.register(waitable, handler)

def unregister_waitable(waitable):
    return Core().io_selector.unregister(waitable)

# Hooks

def def_hook(path):
    return def_variable(path, [])

def add_hook(path, fn):
    hooks = get_variable(path)
    if fn not in hooks:
        hooks.append(fn)

def remove_hook(path, fn):
    hooks = get_variable(path)
    hooks.remove(fn)

def run_hook(path, *args, **kwargs):
    for hook in get_variable(path):
        hook(*args, **kwargs)

# Colors

def def_colors(name, string):
    """
    Define a new color or redefine an existing color.

    The color should be specified as a hex color-string in the format
    ``#rrggbb``.
    """
    try:
        return Core().def_colors(name, string)
    except ColorException as e:
        message('%s' % e)

def def_background(bg_type, color_name):
    try:
        return Core().def_background(bg_type, color_name)
    except ColorException as e:
        message('%s' % e)

def def_foreground(fg_type, color_name):
    try:
        return Core().def_foreground(fg_type, color_name)
    except ColorException as e:
        message('%s' % e)

# Buffers

def with_created_buffer(fn):
    def _fn(buffer_class, *args, **kwargs):
        return fn(create_buffer(buffer_class, *args), **kwargs)
    return _fn

def buffer_window(buffer_object, current_window_set=False):
    return find_window(lambda w: w.buffer() == buffer_object, current_window_set=current_window_set)

@with_created_buffer
def buffer_visible(buffer_object, split_method=split_window_below, to_window=False):
    win = buffer_window(buffer_object, current_window_set=True)
    if not win:
        win = split_method() if split_method else selected_window()
        if win:
            win.set_buffer(buffer_object)
    if win and to_window:
        select_window(win)

    return (win, buffer_object)

@with_created_buffer
def switch_buffer(buffer_object):
    return select_buffer(buffer_object)

@global_key('C-x C-k')
def kill_current_buffer():
    """Kill the current buffer."""
    kill_buffer_object(current_buffer())

# Windows

@contextlib.contextmanager
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
    exec_if_buffer_exists(lambda b: kill_buffer_object(b),
                          buffer_class, *args)
