# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui

from cui.keymap import WithKeymap

from .base import ScrollableBuffer
from .util import with_current_buffer, close_buffer


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

@with_current_buffer
def delete_to_eol(buf):
    """
    Delete text from the cursor to the end of the line
    """
    buf.delete_chars(len(buf.buffer()) - buf.cursor)

@with_current_buffer
def complete_input(buf):
    """
    Invoke the complete-function associated with the buffer
    and replace the buffer-contents with the result.
    """
    buf.auto_complete()

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
        'C-k':     delete_to_eol,
        '<left>':  previous_char,
        '<right>': next_char,
        '<up>':    previous_history_item,
        '<down>':  next_history_item,
        '<tab>':   complete_input,
    }

    def __init__(self, *args, **kwargs):
        super(InputBuffer, self).__init__(*args, **kwargs)
        self._bhistory = []
        self._bhistory_index = -1
        self._saved_buffer = ''

    @property
    def takes_input(self):
        return True

    def buffer(self):
        return self._buffer

    def insert_chars(self, string):
        self._buffer = self._buffer[:self._cursor] + string + self._buffer[self._cursor:]
        self._cursor += len(string)

    def delete_chars(self, length):
        if self._cursor < len(self._buffer):
            self._buffer = self._buffer[:self._cursor] + self._buffer[self._cursor + length:]

    def reset_buffer(self, new_content=''):
        self._buffer = new_content
        self._cursor = len(self._buffer)

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

    @classmethod
    def get_buffer_line(self, prompt, buffer, cursor, show_cursor=False):
        bstring = buffer + ' '
        return [prompt, [
            bstring[:cursor],
            {'content': bstring[cursor],
             'foreground': 'special',
             'background': 'special'},
            bstring[cursor + 1:]
        ] if show_cursor else buffer]

    def buffer_line(self, cursor):
        bstring = self._buffer + ' '
        return [
            str(self._bhistory_index) if self._bhistory_index != -1 else '',
            *InputBuffer.get_buffer_line(self.prompt, self._buffer, self._cursor, show_cursor=cursor)
        ]

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

    def auto_complete(self):
        if self._cursor != len(self._buffer):
            return

        self._buffer = self.on_auto_complete()
        self._cursor = len(self._buffer)

    def on_auto_complete(self):
        return self._buffer


class ConsoleBuffer(InputBuffer, ScrollableBuffer):
    __keymap__ = {
        'C-d': close_buffer
    }

    def __init__(self, *args):
        super(ConsoleBuffer, self).__init__(*args)
        self._prompt = '> '
        self._buffer = ''
        self._cursor = 0
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
