# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import cui

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
    def _fn(*args, **kwargs):
        return fn(cui.current_buffer(), *args, **kwargs)
    return _fn


def close_buffer():
    """
    Kill current buffer and delete selected window.
    """
    cui.kill_current_buffer()
    cui.delete_selected_window()
