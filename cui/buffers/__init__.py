# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
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

Buffer Arguments
================

Buffer classes are instantiated with a set of arguments. These arguments
must be serializable to a string representation and need to be able to
- along with the buffer class of the object - uniquely identify a
buffer to the system. This must be done for each buffer class by
implementing the classmethod ``name(cls, *args)``, where ``*args``
corresponds to the set of arguments passed to the constructor.

If you want to pass arguments to a buffer, which are not considered
static.
"""

from .base import \
    Buffer, ScrollableBuffer, ListBuffer, \
    scroll_up, scroll_down, scroll_page_up, scroll_page_down

from .editable import \
    InputBuffer, ConsoleBuffer

from .trees import \
    TreeBuffer, with_selected_item, DefaultTreeBuffer, node_handlers, NodeHandler, \
    with_node_handler, invoke_node_handler

from .util import \
    with_current_buffer, with_window, close_buffer
