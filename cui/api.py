# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from cui.core import core_api_ns, Core

with core_api_ns(globals()) as core_api:
    core_api('message')

    core_api('bye',                    'C-x C-c')
    core_api('new_window_set',         'C-x 5 2')
    core_api('has_window_set')
    core_api('delete_window_set',      'C-x 5 0')
    core_api('next_window_set',        'C-M-<right>')
    core_api('previous_window_set',    'C-M-<left>')
    core_api('split_window_right',     'C-x 3')
    core_api('select_next_window',     'M-n')
    core_api('select_previous_window', 'M-p')
    core_api('select_left_window',     'M-<left>')
    core_api('select_right_window',    'M-<right>')
    core_api('select_top_window',      'M-<up>')
    core_api('select_bottom_window',   'M-<down>')
    core_api('delete_all_windows',     'C-x 1')

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
