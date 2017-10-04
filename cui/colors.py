import curses
import re

# ncurses 6 gives us 256 but python uses the old ABI
COLOR_BG_OFFSET = 16

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

BGCOL_MAP = {
    'default':           {'index': 0, 'color': 'black'},
    'selection':         {'index': 1, 'color': 'white'},
    'modeline_active':   {'index': 2, 'color': 'white'},
    'modeline_inactive': {'index': 3, 'color': 'black'},
    'special':           {'index': 4, 'color': 'white'}
}

COLOR_RE = re.compile('#(%(h)s)(%(h)s)(%(h)s)' % {'h': '[0-9a-fA-F]{2}'})


def color_pair_from_indices(fg_index, bg_index):
    return (bg_index * COLOR_BG_OFFSET) | fg_index


def color_pair_from_color(fg_name='white', bg_type='default'):
    return color_pair_from_indices(COLOR_MAP[fg_name], BGCOL_MAP[bg_type]['index'])


def color_pair_from_type(fg_type='default', bg_type='default'):
    return color_pair_from_color(FGCOL_MAP[fg_type], bg_type)


class ColorCore(object):
    # TODO reset colors on exit

    def _init_colors(self):
        for bg_entry in BGCOL_MAP.values():
            self._init_background(bg_entry)

    def _init_background(self, bg_entry):
        for fg_color_index in set(COLOR_MAP.values()):
            pair_index = color_pair_from_indices(fg_color_index, bg_entry['index'])
            if pair_index == 0:  # Cannot change first entry
                continue
            curses.init_pair(pair_index, fg_color_index, COLOR_MAP[bg_entry['color']])

    def def_colors(self, name, string):
        match = COLOR_RE.match(string)
        if not match:
            raise Exception('Illegal color string for %s.' % name)

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
        if not curses.can_change_color():
            raise Exception('Can not set colors.')
        if not len(COLOR_MAP.values()) < COLOR_BG_OFFSET:
            raise Exception('Maximum number of colors (%s) is reached' % curses.COLORS)

        color_name_exists = name in COLOR_MAP

        color_index = COLOR_MAP.get(name, len(COLOR_MAP.values()))
        curses.init_color(color_index, r, g, b)
        COLOR_MAP[name] = color_index

        if color_name_exists:
            return

        # if it is a new name, we add new pair definitions
        for bg_entry in BGCOL_MAP.values():
            pair_index = color_pair_from_indices(color_index, bg_entry['index'])
            if pair_index == 0:  # Cannot change first entry
                continue
            curses.init_pair(pair_index, color_index, COLOR_MAP[bg_entry['color']])

    def def_foreground(self, fg_type, color_name):
        FGCOL_MAP[fg_type] = color_name

    def def_background(self, bg_type, color_name):
        if bg_type not in BGCOL_MAP:
            raise Exception('Background type %s is not defined.' % bg_type)

        BGCOL_MAP[bg_type]['color'] = color_name
        self._init_background(BGCOL_MAP[bg_type])

    def get_colors(self):
        return COLOR_MAP.keys()

    def get_foreground_color(self, fg_type):
        return FGCOL_MAP[fg_type]

    def get_backgrounds(self):
        return BGCOL_MAP.keys()

    def get_index_for_color(self, fg_name='white', bg_type='default'):
        return color_pair_from_color(fg_name, bg_type)

    def get_index_for_type(self, fg_type='default', bg_type='default'):
        return color_pair_from_type(fg_type, bg_type)
