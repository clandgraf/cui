# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui

from cui.util import forward

from cui.windows.window import MiniBufferWindow
from cui.windows.window_set import WindowSet


@forward(lambda self: self.active_window_set(),
         ['selected_window',
          'select_next_window',
          'select_previous_window',
          'select_left_window',
          'select_right_window',
          'select_top_window',
          'select_bottom_window',
          'split_window_below',
          'split_window_right',
          'delete_selected_window',
          'delete_all_windows'],
         WindowSet)
class WindowManager(object):
    def __init__(self, screen, minibuffer_height):
        self._screen = screen
        self._window_sets = [WindowSet(screen, minibuffer_height)]
        self._minibuffer_height = minibuffer_height
        self._named_window_sets = {}
        self._active_window_set = 0
        self._mini_buffer_win = MiniBufferWindow(self._screen, minibuffer_height)

    @property
    def window_set_index(self):
        return self._active_window_set

    @property
    def window_set_count(self):
        return len(self._window_sets)

    def active_window_set(self):
        return self._window_sets[self._active_window_set]

    def new_window_set(self, name=None):
        """
        Creates a new window set, optionally associating it with ``name``.

        If name is provided, the window set may be referred to by its name,
        when deleting or selecting it.

        :param name: The name by which the window set may be referred to
        """
        if name and name in self._named_window_sets:
            return self._window_sets[self._named_window_sets[name]]

        idx = self._active_window_set + 1
        ws = WindowSet(self._screen, self._minibuffer_height)
        self._window_sets.insert(idx, ws)
        if name:
            self._named_window_sets[name] = idx
        self._active_window_set += 1
        return ws

    def has_window_set(self, name):
        """
        Returns true if a window set associated with ``name`` exists.

        :param name: The name with which the window set is to be associated.
        """
        return name in self._named_window_sets

    def _delete_window_set_by_index(self, index):
        if index == 0:
            cui.message('Can not delete window set 1.')
            return

        self._named_window_sets = {k:v for k, v in self._named_window_sets.items()
                                   if v != index}
        self._window_sets.pop(index)
        if index <= self._active_window_set:
            self._active_window_set -= 1

    def delete_window_set(self):
        """
        Deletes the currently selected window set.
        The previous window set will become selected.
        """
        self._delete_window_set_by_index(self._active_window_set)

    def delete_window_set_by_name(self, name):
        """
        If a window set associated with ``name`` exists, it will be deleted.
        """
        index = self._named_window_sets.get(name)
        if index:
            self._delete_window_set_by_index(index)

    def next_window_set(self):
        self._active_window_set += 1
        self._active_window_set %= len(self._window_sets)

    def previous_window_set(self):
        self._active_window_set += len(self._window_sets) - 1
        self._active_window_set %= len(self._window_sets)

    def resize(self, minibuffer_height):
        self._minibuffer_height = minibuffer_height
        self._mini_buffer_win.resize(minibuffer_height)
        for ws in self._window_sets:
            ws.resize(minibuffer_height)

    def render(self, minibuffer_height):
        if self._minibuffer_height != minibuffer_height:
            self.resize(minibuffer_height)
        self.active_window_set().render()
        self._mini_buffer_win.render()

    def replace_buffer(self, old_buffer_object, new_buffer_object):
        for ws in self._window_sets:
            ws.replace_buffer(old_buffer_object, new_buffer_object)

    def select_window(self, window):
        for idx, ws in enumerate(self._window_sets):
            w = ws.select_window(window)
            if w:
                self._active_window_set = idx
                return w

    def find_window(self, predicate, current_window_set=False):
        if current_window_set:
            return self.active_window_set().find_window(predicate)
        for ws in self._window_sets:
            w = ws.find_window(predicate)
            if w:
                return w
        return None
