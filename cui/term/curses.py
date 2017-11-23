# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import curses
import signal
import sys

from cui.term import curses_keyreader
from cui.windows import WindowManager
from cui import core
from cui import term
from cui import symbols

TERMINAL_RESIZE_EVENT = 'SIGWINCH'

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
    return cattrs


class Window(term.Window):
    def __init__(self, frame, dimensions, foreground='default', background='default'):
        self._frame = frame
        self._handle = curses.newwin(*dimensions)
        self._foreground = foreground
        self._background = background
        self._init_background()

    def _init_background(self):
        self._handle.bkgdset(self._frame._curses_colpair(self._foreground,
                                                         self._background, []))

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
            self._frame._curses_colpair(foreground, background, attributes))

    def add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.addch(
            row, col, value,
            self._frame._curses_colpair(foreground, background, attributes))

    def add_symbol(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._handle.addch(
            row, col, self._frame.symbols.get(value, ord('?')),
            self._frame._curses_colpair(foreground, background, attributes))

    def insert_string(self, row, col, value, foreground='default', background='default', attributes=[]):
        if len(value) == 0:
            return
        self._handle.insstr(
            row, col, value,
            self._frame._curses_colpair(foreground, background, attributes))

    def clear_line(self):
        self._handle.clrtoeol()

    def clear_all(self):
        self._handle.clrtobot()

    def update(self):
        self._handle.noutrefresh()


class Frame(term.Frame):
    def initialize(self):
        self._color_index_map = DEFAULT_COLOR_INDEX_MAP.copy()
        self._old_signal_handler = None

        # Init Curses
        self._screen = curses.initscr()
        curses.savetty()
        curses.raw(1)
        curses.nonl()
        curses.noecho()
        curses.curs_set(0)
        self._screen.keypad(1)
        self._screen.timeout(0)
        self._core.add_exit_handler(self.close)

        # Init Colors
        curses.start_color()
        self._init_colors()

        # Init Symbols
        self.symbols = {
            symbols.SYM_VLINE:    curses.ACS_VLINE,
            symbols.SYM_HLINE:    curses.ACS_HLINE,
            symbols.SYM_LTEE:     curses.ACS_LTEE,
            symbols.SYM_LLCORNER: curses.ACS_LLCORNER,
            symbols.SYM_RARROW:   curses.ACS_RARROW,
            symbols.SYM_DARROW:   curses.ACS_DARROW, #ord('v'),
        }

        # Init Event Handling
        self._core.io_selector.register(sys.stdin, self._read_input)
        self._core.io_selector.register_async(TERMINAL_RESIZE_EVENT,
                                              self._handle_resize)
        self._old_signal_handler = signal.getsignal(signal.SIGWINCH)
        signal.signal(signal.SIGWINCH, self._handle_resize_sig)

    def close(self):
        if self._old_signal_handler:
            signal.signal(signal.SIGWINCH, self._old_signal_handler)
        self._core.io_selector.unregister_async(TERMINAL_RESIZE_EVENT)
        self._core.io_selector.unregister(sys.stdin)
        curses.resetty()
        curses.endwin()

    def render(self):
        super(Frame, self).render()
        curses.doupdate()

    # ------------ Terminal: Input & Resizing --------------

    def _read_input(self, _):
        keychord, is_input = curses_keyreader.read_keychord(self._screen,
                                                            receive_input=self._core.takes_input())
        if keychord is not None and keychord != curses_keyreader.EVT_RESIZE:
            self._core.dispatch_input(keychord, is_input)

    def _handle_resize_sig(self, _, __):
        self._core.io_selector.post_async_event(TERMINAL_RESIZE_EVENT)

    def _handle_resize(self, _):
        curses.endwin()
        self._screen.refresh()

        # Clear input queue
        curses_keyreader.read_keychord(self._screen, receive_input=False)
        curses_keyreader.read_keychord(self._screen, receive_input=False)

        self._wm.resize()

    # ------------ Colors: Compute pair indices ------------

    def _color_pair_from_indices(self, fg_index, bg_index):
        return bg_index | (fg_index * COLOR_BG_OFFSET)

    def _color_pair_from_color(self, fg_color='white', bg_type='default'):
        return self._color_pair_from_indices(self._color_index_map[fg_color],
                                             BG_INDEX_MAP[bg_type])

    def _color_pair_from_type(self, fg_type='default', bg_type='default'):
        return self._color_pair_from_color(self._core.get_foreground_color(fg_type),
                                           bg_type)

    def _curses_colpair(self, foreground, background, attributes):
        foreground = self._core.get_foreground_color(foreground) or \
                     self._core.get_foreground_color('default')
        return \
            curses.color_pair(self._color_pair_from_color(foreground, background)) | \
            curses_attributes(attributes)

    # ------------ Colors: Initialization ------------

    def _init_colors(self):
        # Initialize Color Definitions defined before frame.initialize
        for name in self._core.get_colors():
            color_def = self._core.get_color(name)
            if color_def:
                self.set_color(name, *color_def)

        # Initialize Color Pairs
        for bg_entry in self._core.get_backgrounds():
            self._init_background(BG_INDEX_MAP[bg_entry],
                                  self._core.get_background_color(bg_entry))

    def _init_background(self, bg_index, bg_color):
        for fg_index in set(self._color_index_map.values()):
            self._init_pair(fg_index, bg_index, bg_color)

    def _init_pair(self, fg_index, bg_index, bg_color):
            pair_index = self._color_pair_from_indices(fg_index, bg_index)
            if pair_index == 0:  # Cannot change first entry
                return
            curses.init_pair(pair_index, fg_index, self._color_index_map[bg_color])

    # ------------ Colors: Definition -------------

    def get_index_for_color(self, fg_name='white', bg_type='default'):
        return self._color_pair_from_color(fg_name, bg_type)

    def get_index_for_type(self, fg_type='default', bg_type='default'):
        return self._color_pair_from_type(fg_type, bg_type)

    def set_color(self, name, r, g, b):
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

    def set_background(self, bg_type):
        # TODO update window background
        self._init_background(BG_INDEX_MAP[bg_type],
                              self._core.get_background_color(bg_type))

    # ------------ Windows: Handles -----------------

    def get_dimensions(self):
        return self._screen.getmaxyx()

    def create_window(self, dimensions):
        return Window(self, dimensions)

    def update(self):
        self._screen.noutrefresh()

    def add_char(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._screen.addch(
            row, col, value,
            self._curses_colpair(foreground, background, attributes))

    def add_symbol(self, row, col, value, foreground='default', background='default', attributes=[]):
        self._screen.addch(
            row, col, self.symbols.get(value, '?'),
            self._curses_colpair(foreground, background, attributes))
