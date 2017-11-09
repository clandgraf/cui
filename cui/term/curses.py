# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import curses

# ncurses 6 gives us 256 colors but python uses the old ABI
# we are restricted to 256 color_pairs,  from which we use
# 8 colors max. for background and 32 colors for foreground
COLOR_BG_OFFSET = 8

# Color Indices: These act as the upper 5 Bit (foreground)
# of the curses pair index and assign cui color names to curses
# color definitions
DEFAULT_COLOR_INDEX_MAP = {
    'black':   curses.COLOR_BLACK,
    'red':     curses.COLOR_RED,
    'green':   curses.COLOR_GREEN,
    'yellow':  curses.COLOR_YELLOW,
    'blue':    curses.COLOR_BLUE,
    'magenta': curses.COLOR_MAGENTA,
    'cyan':    curses.COLOR_CYAN,
    'white':   curses.COLOR_WHITE
}

# Background indices:
BG_INDEX_MAP = {
    'default':           0,
    'selection':         1,
    'modeline_active':   2,
    'modeline_inactive': 3,
    'special':           4,
}

ATTR_MAP = {
    'bold': curses.A_BOLD
}


def curses_attributes(attributes):
    cattrs = 0
    for attr in attributes:
        cattrs |= ATTR_MAP[attr]

def curses_colpair(core, foreground, background, attributes):
    foreground = self._core.get_foreground_color(foreground) or \
                 self._core.get_foreground_color('default')
    return \
        curses.color_pair(core.get_index_for_color(foreground, background)) | \
        curses_attributes(attributes)


class CursesWindow(object):
    def __init__(self, core):
        self._core = core
        self._handle = curses.newwin(dimensions)

    def __del__(self):
        del self._handle

    def resize(self, dimensions):
        self._handle.resize(*dimensions[:2])
        self._handle.mvwin(*dimensions[2:])

    def move_cursor(self, row, col):
        self._handle.move(row, col)

    def add_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        if len(value) == 0:
            return
        self._handle.addstr(
            row, col, value,
            curses_colpair(self._core, foreground, background, attributes))

    def add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.addch(
            row, col, value,
            curses_colpair(self._core, foreground, background, attributes))

    def insert_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.insstr(
            row, col, value,
            curses_colpair(self._core, foreground, background, attributes))

    def clear_line(self):
        self._handle.clrtoeol()

    def clear_all(self):
        self._handle.clrtobot()

    def update(self):
        self._handle.noutrefresh()


class CursesFrame(object):
    def __init__(self, core):
        self._core = core
        self._color_index_map = DEFAULT_COLOR_INDEX_MAP.copy()

    # ------------ Colors: Compute pair indices ------------

    def _color_pair_from_indices(fg_index, bg_index):
        return bg_index | (fg_index * COLOR_BG_OFFSET)

    def _color_pair_from_color(fg_color='white', bg_type='default'):
        return self._color_pair_from_indices(self._color_index_map[fg_color],
                                             BG_INDEX_MAP[bg_type])

    def _color_pair_from_type(fg_type='default', bg_type='default'):
        return self._color_pair_from_color(self.get_foreground_color(fg_type),
                                           bg_type)

    # ------------ Colors: Initialization ------------

    def init_colors(self):
        for bg_entry in self._core.get_backgrounds():
            self._init_background(BG_INDEX_MAP[bg_entry],
                                  self._core.get_background_color(bg_entry))

    def _init_background(self, bg_index, bg_color):
        for fg_index in set(self._color_index_map.values()):
            self._init_pair(fg_index, bg_index, bg_color)

    def _init_pair(self, fg_index, bg_index, bg_color):
            pair_index = self._color_pair_from_indices(fg_color_index, bg_index)
            if pair_index == 0:  # Cannot change first entry
                return
            curses.init_pair(pair_index, fg_index, self._color_index_map[bg_color])

    # ------------ Colors: Definition -------------

    def def_colorc(self, name, r, g, b):
        if not curses.can_change_color():
            raise ColorException('Can not set colors.')
        if not len(self._color_index_map.values()) < 32:
            raise ColorException('Maximum number of colors (32) is reached.')

        color_name_exists = name in self._core.get_colors()

        cr = int(r * 1000.0 // 255.0)
        cg = int(g * 1000.0 // 255.0)
        cb = int(b * 1000.0 // 255.0)

        color_index = self._color_index_map.get(name, len(self._color_index_map.values()))
        curses.init_color(color_index, cr, cg, cb)
        self._color_index_map[name] = color_index

        if color_name_exists:
            return

        # if it is a new name, we add new pair definitions
        for bg_entry in self._core.get_backgrounds():
            self._init_pair(color_index,
                            BG_INDEX_MAP[bg_entry],
                            self._core.get_background_color(bg_entry))

    # ------------ Windows: Handles -----------------

    def create_window(self, dimensions):
        return CursesWindow(self._core)

    def add_string(self):
        pass
