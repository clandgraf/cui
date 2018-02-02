# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This module provides the classes that manage the content of one frame.
A running cui instance may consists of severel frames that correspond
to the terminals or windowing system-based windows through which the
user interacts with the application. How the content of each of these
terminals is displayed is implemented in the submodules of this module.

While the Frame class and its subclasses, defined in cui.term is
responsible for managing interation with the user and abstracting platform
specific details, each Frame instance has a corresponding WindowManager
instance, that is responsible for layouting the windows displayed in its
frame.

Therefore, each WindowManager has a list of 1..n WindowSet instances,
each of which contain a set of windows that can be displayed on the
screen simultaneously. The active window set of the window manager is
the window set that will be displayed, and the user may switch between
different window sets, resulting in a different set of windows being
displayed on the terminal.

The WindowSet class in turn is responsible for layouting its set of
windows and the creation and deletion of windows. Each WindowSet has
at least one window. New windows may be created by splitting an existing
window vertically or horizontally, and windows are deleted by merging
two neighbouring windows together. WindowSet stores the layout of its
windows in a tree structure, where each leaf node represents a window
and the inner nodes represent either horizontal or vertical splits.
"""

from cui.windows.manager import WindowManager
