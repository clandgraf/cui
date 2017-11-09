# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This module abstracts ncurses color management.

The class ColorCore provides methods to define colors, as well as
semantic foreground and background color definitions.

Color values are defined as strings that map to a triple of 8
bit red/green/blue values. These colors may be referenced
in semantic background and foreground definitions, , such as
``selection`` or ``error``. Background definitions are limited to
the types provided by this module, which are:

- default: the default background color
- selection: default color for the selected row
- modeline_active: the background color of the modeline of the
  selected window
- modeline_inactive: the background color of all other modelines
- special: This background is be used to highlight important
  sections of the screen, e.g. the current line in a debugger

New foreground definitions may be added by calling defcolor*.

Technical information:

The number of possible colors, backgrounds and foregrounds is
limited by the number of available colors and pairs in curses,
and the way ncurses color_pairs are mapped to cui color
combinations.

Given a combination of foreground-color and background-type the
corresponding color_pair index is calculated by packing these into the
8 bit values that ncurses 5 ABI supports, where the lower 3 bit are
used for background types, and the remaining 5 bit for foreground
colors.

This max. 255 pairs (pair_index 0 is fixed) are initialized on startup,
as well as when new colors are defined or backgrounds are modified.
"""

import curses
import re

# ncurses 6 gives us 256 colors but python uses the old ABI
# we are restricted to 256 color_pairs,  from which we use
# 8 colors max. for background and 32 colors for foreground
COLOR_BG_OFFSET = 8

COLOR_MAP = {
    'black':   curses.COLOR_BLACK,
    'red':     curses.COLOR_RED,
    'green':   curses.COLOR_GREEN,
    'yellow':  curses.COLOR_YELLOW,
    'blue':    curses.COLOR_BLUE,
    'magenta': curses.COLOR_MAGENTA,
    'cyan':    curses.COLOR_CYAN,
    'white':   curses.COLOR_WHITE
}

FGCOL_MAP = {
    'default':           'white',
    'selection':         'black',
    'modeline_active':   'black',
    'modeline_inactive': 'white',
    'special':           'black',
    'divider':           'white',

    'error':             'red',
    'info':              'green'
}

# TODO This may be optimized by mapping backgrounds using the
# same color to the same index
BGCOL_MAP = {
    'default':           {'index': 0, 'color': 'black'},
    'selection':         {'index': 1, 'color': 'white'},
    'modeline_active':   {'index': 2, 'color': 'white'},
    'modeline_inactive': {'index': 3, 'color': 'black'},
    'special':           {'index': 4, 'color': 'white'}
}

COLOR_RE = re.compile('#(%(h)s)(%(h)s)(%(h)s)' % {'h': '[0-9a-fA-F]{2}'})


def color_pair_from_indices(fg_index, bg_index):
    return bg_index | (fg_index * COLOR_BG_OFFSET)


def color_pair_from_color(fg_name='white', bg_type='default'):
    return color_pair_from_indices(COLOR_MAP[fg_name], BGCOL_MAP[bg_type]['index'])


def color_pair_from_type(fg_type='default', bg_type='default'):
    return color_pair_from_color(FGCOL_MAP[fg_type], bg_type)


class ColorException(Exception):
    pass


class ColorCore(object):
    # TODO reset colors on exit

    def _init_colors(self):
        for bg_entry in BGCOL_MAP.values():
            self._init_background(bg_entry)

    def _init_background(self, bg_entry):
        for fg_color_index in set(COLOR_MAP.values()):
            self._init_pair(fg_color_index, bg_entry)

    def _init_pair(self, fg_color_index, bg_entry):
            pair_index = color_pair_from_indices(fg_color_index, bg_entry['index'])
            if pair_index == 0:  # Cannot change first entry
                return
            curses.init_pair(pair_index, fg_color_index, COLOR_MAP[bg_entry['color']])

    def def_colors(self, name, string):
        match = COLOR_RE.match(string)
        if not match:
            raise ColorException('Illegal color string for %s.' % name)

        return self.def_color(name,
                              int(match.group(1), 16),
                              int(match.group(2), 16),
                              int(match.group(3), 16))

    def def_color(self, name, r, g, b):
        return self.def_colorc(name,
                               int(r * 1000.0 // 255.0),
                               int(g * 1000.0 // 255.0),
                               int(b * 1000.0 // 255.0))

    def def_colorc(self, name, r, g, b):
        color_name_exists = name in COLOR_MAP

        if not curses.can_change_color():
            raise ColorException('Can not set colors.')
        if not len(COLOR_MAP.values()) < 32:
            raise ColorException('Maximum number of colors (32) is reached.')

        color_name_exists = name in COLOR_MAP

        color_index = COLOR_MAP.get(name, len(COLOR_MAP.values()))
        curses.init_color(color_index, r, g, b)
        COLOR_MAP[name] = color_index

        if color_name_exists:
            return

        # if it is a new name, we add new pair definitions
        for bg_entry in BGCOL_MAP.values():
            self._init_pair(color_index, bg_entry)

    def def_foreground(self, fg_type, color_name):
        if color_name is not None and color_name not in COLOR_MAP:
            raise ColorException('No color named %s' % color_name)

        FGCOL_MAP[fg_type] = color_name

    def def_background(self, bg_type, color_name):
        if bg_type not in BGCOL_MAP:
            raise ColorException('Background type %s is not defined.' % bg_type)
        if color_name is not None and color_name not in COLOR_MAP:
            raise ColorException('No color named %s' % color_name)

        BGCOL_MAP[bg_type]['color'] = color_name
        self._init_background(BGCOL_MAP[bg_type])

    def get_colors(self):
        return COLOR_MAP.keys()

    def get_foreground_color(self, fg_type):
        return FGCOL_MAP[fg_type]

    def get_background_color(self, bg_type):
        return BGCOL_MAP[bg_type]['color']

    def get_backgrounds(self):
        return BGCOL_MAP.keys()

    def get_index_for_color(self, fg_name='white', bg_type='default'):
        return color_pair_from_color(fg_name, bg_type)

    def get_index_for_type(self, fg_type='default', bg_type='default'):
        return color_pair_from_type(fg_type, bg_type)
