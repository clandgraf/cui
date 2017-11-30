# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This module provides abstract buffer classes to derive your own
concrete or abstract buffer classes from, as well as functions
that act on buffers.

A buffer class describes how data is rendered to the screen, which is
always line-wise. It may provide its own keymap to define a set of
keybindings that are used in addition to the global keybindings
defined in core. For details on defining keybindings see keymap.

Buffer classes are instantiated with a set of arguments. These arguments
must be serializable to a string representation and need to be able to
- along with the buffer class of the object - uniquely identify a
buffer to the system.
"""

import contextlib
import functools
import itertools

import cui

from cui import symbols
from cui import api
from cui.keymap import WithKeymap
from cui.util import get_base_classes, deep_get, deep_put, minmax


def pad_left(width, string):
    if len(string) > width:
        return '%s%s' % ('...', string[-(width - 3):])
    return string


def with_window(f):
    """
    Decorator that runs function only if buffer is in selected window.

    This decorator expects the first parameter of the wrapped function
    to be a buffer. Note that this modifies the argument list of f,
    inserting window as second positional argument.
    """
    @functools.wraps(f)
    def _with_window(*args, **kwargs):
        self = args[0]
        win = self.window()
        if win:
            f(args[0], win, *args[1:], **kwargs)
    return _with_window


def with_current_buffer(fn):
    @functools.wraps(fn)
    def _fn():
        return fn(cui.current_buffer())
    return _fn


def close_buffer():
    """
    Kill current buffer and delete selected window.
    """
    cui.kill_current_buffer()
    cui.delete_selected_window()


def buffer_keys(keychord, name=None):
    def _buffer_keys(class_):
        def switch_to_buffer():
            cui.switch_buffer(class_)
        if name:
            switch_to_buffer.__name__ = name
        switch_to_buffer.__doc__ = 'Switch to buffer %s' % class_.__name__
        cui.set_global_key(keychord, switch_to_buffer)
        return class_
    return _buffer_keys


class Buffer(WithKeymap):
    """
    This is the base class for all buffers. Usually you want to
    to use a more specialized class.
    """

    @classmethod
    def name(cls, *args):
        return None

    def __init__(self, *args):
        super(Buffer, self).__init__()
        self.args = args
        self._state = {'win/buf': {}}

    def buffer_name(self):
        return self.name(*self.args)

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
        return False

    def send_input(self, string):
        pass

    def on_pre_render(self):
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
    Recenter selection the current buffer.
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


@with_current_buffer
def expand_node(b):
    """
    Expand the currently selected node.
    """
    item = b.selected_item()
    if not b.is_expanded(item) and b.has_children(item):
        b.set_expanded(item, True)

@with_current_buffer
def collapse_node(b):
    """
    Collapse the currently selected node.
    """
    item = b.selected_item()
    if b.is_expanded(item) and b.has_children(item):
        b.set_expanded(item, False)

class TreeBuffer(ListBuffer):
    __keymap__ = {
        '<left>': collapse_node,
        '<right>': expand_node
    }

    def __init__(self, *args, show_handles=False):
        super(TreeBuffer, self).__init__(*args)
        self._flattened = []
        self._show_handles = show_handles

    def get_children(self, item):
        return []

    def is_expanded(self, item):
        False

    def set_expanded(self, item, expanded):
        pass

    def has_children(self, item):
        False

    def fetch_children(self, item):
        pass

    def _fetch_children(self, item):
        self.fetch_children(item)
        return self.get_children(item)

    def get_roots(self):
        return []

    def on_pre_render(self):
        self._flattened = []
        def _create_internal_nodes(nodes, parent=None):
            return list(map(lambda n: {'item': n,
                                       'first': n == nodes[0],
                                       'last': n == nodes[-1],
                                       'parent': parent,
                                       'depth': 0 if parent is None else parent['depth'] + 1},
                            nodes))

        roots = self.get_roots()
        node_stack = _create_internal_nodes(roots)
        while node_stack:
            n = node_stack.pop(0)
            self._flattened.append(n)
            if self.has_children(n['item']) and self.is_expanded(n['item']):
                node_stack[0:0] = _create_internal_nodes(self.get_children(n['item']) or \
                                                         self._fetch_children(n['item']),
                                                         n)

    def items(self):
        return self._flattened

    def selected_node(self):
        return super(TreeBuffer, self).selected_item()

    def selected_item(self):
        return self.selected_node()['item']

    def render_item(self, window, item, index):
        tree_tab = cui.get_variable(['tree-tab'])
        rendered_node = self.render_node(window, item['item'], item['depth'],
                                         window.dimensions[1] - tree_tab * item['depth'])
        return [[self.render_tree_tab(window, item, line, tree_tab, line == rendered_node[0]),
                 line]
                for line in rendered_node]

    def render_tree_tab(self, window, item, line, tree_tab, first_line):
        lst = []

        if item['depth'] != 0:
            lst.append((symbols.SYM_LLCORNER if item['last'] else symbols.SYM_LTEE) \
                       if first_line else \
                       (' ' if item['last'] else symbols.SYM_VLINE))
        if self._show_handles:
            lst.append((symbols.SYM_DARROW if self.is_expanded(item['item']) else symbols.SYM_RARROW) \
                       if first_line and self.has_children(item['item']) else \
                       ' ')
        lst.append(' ')

        while item['depth'] > 1:
            item = item['parent']
            lst = (['  '] if item['last'] else [symbols.SYM_VLINE, ' ']) + \
                  ([' '] if self._show_handles else []) + \
                  lst
        if item['depth'] == 1:
            lst = (['  '] if self._show_handles else [' ']) + lst

        return lst

    def render_node(self, window, item, depth, width):
        return [item]


@with_current_buffer
def next_char(buf):
    return buf.set_cursor(buf.cursor + 1)

@with_current_buffer
def previous_char(buf):
    return buf.set_cursor(buf.cursor - 1)

@with_current_buffer
def first_char(buf):
    return buf.set_cursor(0)

@with_current_buffer
def last_char(buf):
    return buf.set_cursor(len(buf.buffer()))

@with_current_buffer
def delete_next_char(buf):
    buf.delete_chars(1)

@with_current_buffer
def delete_previous_char(buf):
    if previous_char():
        buf.delete_chars(1)

@with_current_buffer
def previous_history_item(buf):
    buf.activate_history_item(
        (buf.history_length - 1) if buf.history_index == -1 else max(buf.history_index - 1, 0))

@with_current_buffer
def next_history_item(buf):
    if buf.history_index != -1:
        buf.activate_history_item(buf.history_index + 1)


class InputBuffer(WithKeymap):
    """
    Buffer Mixin for line-based editing
    """
    __keymap__ = {
        '<enter>': with_current_buffer(lambda buf: buf.send_current_buffer()),
        'C-a':     first_char,
        'C-e':     last_char,
        'C-?':     delete_previous_char,
        '<del>':   delete_next_char,
        '<left>':  previous_char,
        '<right>': next_char,
        '<up>':    previous_history_item,
        '<down>':  next_history_item,
    }

    def __init__(self, *args, **kwargs):
        super(InputBuffer, self).__init__()
        self._bhistory = []
        self._bhistory_index = -1
        self._saved_buffer = ''
        self._buffer = ''
        self._cursor = 0

    @property
    def takes_input(self):
        return True

    def insert_chars(self, string):
        self._buffer = self._buffer[:self._cursor] + string + self._buffer[self._cursor:]
        self._cursor += len(string)

    def delete_chars(self, length):
        if self._cursor < len(self._buffer):
            self._buffer = self._buffer[:self._cursor] + self._buffer[self._cursor + length:]

    @property
    def history_index(self):
        return self._bhistory_index

    @property
    def history_length(self):
        return len(self._bhistory)

    def activate_history_item(self, index):
        if not self._bhistory:
            return

        if self._bhistory_index != -1 and (index == -1 or index == len(self._bhistory)):
            self._buffer = self._saved_buffer
            self._bhistory_index = -1
        else:
            if self._bhistory_index == -1:
                self._saved_buffer = self._buffer
            self._bhistory_index = index % len(self._bhistory)
            self._buffer = self._bhistory[self._bhistory_index]

        self.set_cursor(min(self._cursor, len(self._buffer)))

    @property
    def cursor(self):
        return self._cursor

    def set_cursor(self, cur):
        if cur >= 0 and cur <= len(self._buffer):
            self._cursor = cur
            return True
        return False

    def buffer(self):
        return self._buffer

    def buffer_line(self, cursor):
        bstring = self._buffer + ' '
        return [str(self._bhistory_index) if self._bhistory_index != -1 else '', self.prompt,
                [bstring[:self._cursor],
                 {'content': bstring[self._cursor],
                  'foreground': 'special',
                  'background': 'special'},
                 bstring[self._cursor + 1:]] \
                if cursor else \
                self._buffer]

    def send_current_buffer(self):
        self._bhistory.append(self._buffer)
        self._bhistory_index = -1
        b = self._buffer
        self._buffer = ''
        self._cursor = 0
        self.on_send_current_buffer(b)
        self._to_bottom = True

    def on_send_current_buffer(self, b):
        pass


class ConsoleBuffer(InputBuffer, ScrollableBuffer):
    __keymap__ = {
        'C-d': close_buffer
    }

    def __init__(self, *args):
        super(ConsoleBuffer, self).__init__(*args)
        self._prompt = '> '
        self._chistory = []
        self._to_bottom = False

    @property
    def prompt(self):
        return self._prompt

    def get_lines(self, window):
        if window == cui.selected_window() and self._to_bottom:
            first_row = max(self.line_count() - window.dimensions[0], 0)
            self.set_variable(['win/buf', 'first-row'], first_row)
            self._to_bottom = False

        yield from iter(self._chistory[window._state['first-row']:])
        yield self.buffer_line(cursor=True)

    def line_count(self):
        return len(self._chistory) + 1

    def send_current_buffer(self):
        self._chistory.append(self.buffer_line(cursor=False))
        super(ConsoleBuffer, self).send_current_buffer()

    def extend(self, *args):
        self._chistory.extend(args)
        self._to_bottom = True
