# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import os

from cui.keymap import WithKeymap
from cui.util import deep_get, deep_put, minmax

from .util import with_current_buffer, with_window


class Buffer(WithKeymap):
    """
    This is the base class for all buffers. Usually you want to
    to use a more specialized class.
    """

    @classmethod
    def name(cls, mode_line_columns=None, *args):
        return None

    def __init__(self, *args):
        super(Buffer, self).__init__()
        self.args = args
        self._state = {'win/buf': {}}

    @property
    def cwd(self):
        return os.getcwd()

    def buffer_name(self, mode_line_columns=None):
        return self.name(*self.args, mode_line_columns=mode_line_columns)

    def window(self):
        selected_window = cui.selected_window()
        return selected_window if self == selected_window.buffer() else None

    def def_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=True)

    def set_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=False)
        if path[0] == 'win/buf':
            selected_window = self.window()
            if selected_window:
                selected_window.update_state(path[1:], value)

    def get_variable(self, path):
        return deep_get(self._state, path, return_none=False)

    # --------------- Override these ------------

    @property
    def takes_input(self):
        """
        Overwrite and return True if this buffer will take keyboard input for editing
        """
        return False

    def send_input(self, string):
        """
        This function will be called if ``takes_input`` returns True, and
        keyboard input has been made to this buffer.
        """
        pass

    def on_pre_render(self):
        """
        This function will be called the first time a buffer is rendered
        during updating the ui. This allows the buffer to do preparations for
        rendering its lines which are independent of the window it is rendered
        to, as a buffer may be displayed in multiple windows.

        To do window-dependent preparations implement the callback
        ``on_pre_render_win``.
        """
        pass

    def on_pre_render_win(self, window):
        """
        This function will be called each time the buffer will be rendered
        to a window, but after ``on_pre_render``. It allows the buffer to do
        preparations for rendering its lines that depend on the window it is
        rendered to.
        """
        pass

    def line_count(self):
        pass

    def get_lines(self, window):
        pass


@with_current_buffer
def scroll_up(b):
    """
    Scroll current buffer one line up.
    """
    b.scroll_up()

@with_current_buffer
def scroll_page_up(b):
    """
    Scroll current buffer one page-size up.
    """
    b.scroll_page_up()

@with_current_buffer
def scroll_down(b):
    """
    Scroll current buffer one line down.
    """
    b.scroll_down()

@with_current_buffer
def scroll_page_down(b):
    """
    Scroll current buffer one page-size down.
    """
    b.scroll_page_down()

class ScrollableBuffer(Buffer):
    __keymap__ = {
        'S-<up>':     scroll_up,
        'S-<pgup>':   scroll_page_up,
        'S-<down>':   scroll_down,
        'S-<pgdown>': scroll_page_down,
    }

    def __init__(self, *args):
        super(ScrollableBuffer, self).__init__(*args)
        self.def_variable(['win/buf', 'first-row'], 0)

    def scroll_up(self, step=1):
        self.set_variable(['win/buf', 'first-row'],
                          max(0,
                              self.get_variable(['win/buf', 'first-row']) - step))

    @with_window
    def scroll_page_up(self, window):
        self.scroll_up(window.rows)

    def scroll_down(self, step=1):
        self.set_variable(['win/buf', 'first-row'],
                          min(max(0, self.line_count() - 4),
                              self.get_variable(['win/buf', 'first-row']) + step))

    @with_window
    def scroll_page_down(self, window):
        self.scroll_down(window.rows)


@with_current_buffer
def previous_item(b):
    """
    Select the previous item.
    """
    b.item_up()

@with_current_buffer
def item_page_up(b):
    """
    Moves selection one page up.
    """
    b.item_page_up()

@with_current_buffer
def item_home(b):
    """
    Select the first item in buffer.
    """
    b.item_home()

@with_current_buffer
def next_item(b):
    """
    Select the next item.
    """
    b.item_down()

@with_current_buffer
def item_page_down(b):
    """
    Moves selection one page down.
    """
    b.item_page_down()

@with_current_buffer
def item_end(b):
    """
    Select the last item in buffer.
    """
    b.item_end()

@with_current_buffer
def select_item(b):
    """
    Invoke main action on the selected item.
    """
    b.on_item_selected()

@with_current_buffer
def recenter_selection(b):
    """
    Recenter selection in the current buffer.

    This scrolls the contents of the current buffer so that the
    selected item will be displayed in the middle of the window,
    in which the buffer will be displayed.
    """
    b.recenter()

class ListBuffer(ScrollableBuffer):
    __keymap__ = {
        '<up>':     previous_item,
        '<pgup>':   item_page_up,
        '<home>':   item_home,
        '<down>':   next_item,
        '<pgdown>': item_page_down,
        '<end>':    item_end,
        'C-l':      recenter_selection,
        '<enter>':  select_item
    }

    def __init__(self, *args):
        super(ListBuffer, self).__init__(*args)
        self._item_height = 1
        self.def_variable(['win/buf', 'selected-item'], 0)

    @with_window
    def recenter(self, window, out_of_bounds=False):
        max_lines = window.dimensions[0]
        first_row = self.get_variable(['win/buf', 'first-row'])
        selected_row = self.get_variable(['win/buf', 'selected-item']) * self._item_height
        selected_row_offset = selected_row - first_row
        if not out_of_bounds or \
           selected_row_offset < 0 or \
           selected_row_offset > max_lines - 1:
            center = first_row - (max_lines // 2 - (selected_row - first_row))
            self.set_variable(['win/buf', 'first-row'],
                              minmax(0, center, self.line_count() - 4))

    def item_up(self, step=1):
        self.set_variable(['win/buf', 'selected-item'],
                          max(0, self.get_variable(['win/buf', 'selected-item']) - step))
        self.recenter(out_of_bounds=True)

    def item_home(self):
        self.set_variable(['win/buf', 'selected-item'], 0)
        self.recenter(out_of_bounds=True)

    @with_window
    def item_page_up(self, window):
        self.item_up(window.rows // self._item_height)

    def item_down(self, step=1):
        self.set_variable(['win/buf', 'selected-item'],
                          min(self.get_variable(['win/buf', 'selected-item']) + step,
                              self.item_count() - 1))
        self.recenter(out_of_bounds=True)

    def item_end(self):
        self.set_variable(['win/buf', 'selected-item'], self.item_count() - 1)
        self.recenter(out_of_bounds=True)

    @with_window
    def item_page_down(self, window):
        self.item_down(window.rows // self._item_height)

    def selected_item(self):
        return self.items()[self.get_variable(['win/buf', 'selected-item'])]

    def line_count(self):
        return self.item_count() * self._item_height

    def hide_selection(self):
        return False

    def get_lines(self, window):
        hide_selection = self.hide_selection()
        first_row = window._state['first-row']
        selected_item = window._state['selected-item']
        item = None
        for row_index in range(first_row, min(self.line_count(),
                                              window.dimensions[0] + first_row)):
            item_index = row_index // self._item_height
            line_index = row_index % self._item_height
            if item is None or line_index == 0:
                item = self.render_item(window, self.items()[item_index], item_index)
            yield (
                {
                    'content': item[line_index],
                    'foreground': 'selection',
                    'background': 'selection'
                } if selected_item == item_index and not hide_selection else (
                    item[line_index]
                )
            ) if line_index < len(item) else ''

    def on_item_selected(self):
        pass

    def items(self):
        return []

    def item_count(self):
        return len(self.items())

    def render_item(self, window, item, index):
        return [item]
