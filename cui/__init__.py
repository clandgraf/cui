# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager

from cui import core
from cui.core import \
    has_run, init_func, update_func, post_init_func, \
    running, message, \
    def_colors, def_foreground, def_background, \
    def_variable, get_variable, set_variable, \
    def_hook, add_hook, remove_hook, run_hook, \
    select_window, selected_window, delete_selected_window, delete_all_windows, find_window, \
    split_window_below, split_window_right, \
    get_buffer, select_buffer, switch_buffer, current_buffer, buffer_window, buffer_visible, \
    kill_current_buffer
from cui import buffers
from cui.buffers import with_current_buffer

@contextmanager
def window_selected(window):
    old_window = selected_window()
    yield select_window(window)
    select_window(old_window)

def exec_in_buffer_visible(expr, buffer_class, *args, **kwargs):
    window, buffer_object = buffer_visible(buffer_class, *args, **kwargs)
    with window_selected(window):
        expr(buffer_object)

def exec_if_buffer_exists(expr, buffer_class, *args):
    buffer_object = get_buffer(buffer_class, *args)
    if buffer_object:
        expr(buffer_object)

def kill_buffer(buffer_class, *args):
    exec_if_buffer_exists(lambda b: core.Core().kill_buffer(b),
                          buffer_class, *args)

__all__ = [
    'has_run',
    'init_func',
    'update_func',
    'post_init_func',

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

    'exec_in_buffer_visible',
    'exec_if_buffer_exists',

    'buffers'
]
