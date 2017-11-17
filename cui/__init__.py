# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from cui.api import *
from cui import buffers
from cui.buffers import with_current_buffer

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
