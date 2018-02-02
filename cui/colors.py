# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
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

import re

COLOR_MAP = {
    'black':   None,
    'red':     None,
    'green':   None,
    'yellow':  None,
    'blue':    None,
    'magenta': None,
    'cyan':    None,
    'white':   None
}

FGCOL_MAP = {
    'default':           'white',
    'inactive':          'white',
    'selection':         'black',
    'modeline_active':   'black',
    'modeline_inactive': 'white',
    'special':           'black',
    'divider':           'white',

    'error':             'red',
    'info':              'green'
}

FGCOL_MAP_COMPAT = FGCOL_MAP.copy()

BGCOL_MAP = {
    'default':           'black',
    'selection':         'white',
    'modeline_active':   'white',
    'modeline_inactive': 'black',
    'special':           'white'
}

BGCOL_MAP_COMPAT = BGCOL_MAP.copy()

COLOR_RE = re.compile('#(%(h)s)(%(h)s)(%(h)s)' % {'h': '[0-9a-fA-F]{2}'})


class ColorException(Exception):
    pass


class ColorCore(object):
    def def_colors(self, name, string):
        match = COLOR_RE.match(string)
        if not match:
            raise ColorException('Illegal color string for %s.' % name)

        return self.def_color(name,
                              int(match.group(1), 16),
                              int(match.group(2), 16),
                              int(match.group(3), 16))

    def def_color(self, name, r, g, b):
        if self._frame:
            self._frame.set_color(name, r, g, b)
        COLOR_MAP[name] = (r, g, b)

    def def_foreground(self, fg_type, color_name):
        if color_name is not None and color_name not in COLOR_MAP:
            raise ColorException('No color named %s' % color_name)

        FGCOL_MAP[fg_type] = color_name

    def def_background(self, bg_type, color_name):
        if bg_type not in BGCOL_MAP:
            raise ColorException('Background type %s is not defined.' % bg_type)
        if color_name is not None and color_name not in COLOR_MAP:
            raise ColorException('No color named %s' % color_name)

        BGCOL_MAP[bg_type] = color_name
        if self._frame:
            self._frame.set_background(bg_type)

    def get_colors(self):
        return COLOR_MAP.keys()

    def get_color(self, name):
        return COLOR_MAP.get(name)

    def get_foreground_color(self, fg_type, compat=False):
        return (FGCOL_MAP_COMPAT if compat else FGCOL_MAP).get(fg_type)

    def get_foregrounds(self):
        return FGCOL_MAP.keys()

    def get_background_color(self, bg_type, compat=False):
        return (BGCOL_MAP_COMPAT if compat else BGCOL_MAP)[bg_type]

    def get_backgrounds(self):
        return BGCOL_MAP.keys()
