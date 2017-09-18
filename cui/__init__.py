from contextlib import contextmanager

from cui.core import \
    init_func, update_func, post_init_func, \
    message, \
    def_colors, def_foreground, def_background, \
    def_variable, get_variable, set_variable, \
    select_window, selected_window, find_window, split_window_below, split_window_right, \
    get_buffer, select_buffer, switch_buffer, current_buffer, buffer_window, buffer_visible
from cui import buffers

@contextmanager
def window_selected(window):
    old_window = selected_window()
    yield select_window(window)
    select_window(old_window)

__all__ = [
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

    'select_window',
    'selected_window',
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

    'buffers'
]
