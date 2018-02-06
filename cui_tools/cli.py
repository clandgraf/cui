# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
CommandLine provides a wrapper around the GNU readline interface.

It enhances the python readline package to be used in an
asynchronuous event loop based on cui_tools.io_selector. In order to
adjust the system to correctly load the library, the function
set_readline_path may be used.
"""

import sys

LIBREADLINE_PATH = 'cygreadline7.dll'


def set_readline_path(path):
    global LIBREADLINE_PATH
    LIBREADLINE_PATH = path


def _patch():
    import readline
    import ctypes

    if not hasattr(readline, 'callback_handler_remove'):
        rl_path = LIBREADLINE_PATH
        rl_lib = ctypes.cdll.LoadLibrary(rl_path)

        readline.callback_handler_remove = rl_lib.rl_callback_handler_remove
        readline.callback_read_char = rl_lib.rl_callback_read_char

        rlcallbackfunctype = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)

        def setcallbackfunc(prompt, thefunc):
            rl_lib.rl_callback_handler_install(prompt, rlcallbackfunctype(thefunc))

        readline.callback_handler_install = setcallbackfunc

    return readline


class CommandLine(object):
    def __init__(self, prompt, callback, env=None, encoding='utf-8'):
        self._env = env
        self._prompt = prompt.encode(encoding)
        self._encoding = encoding
        self._rl = _patch()
        self._callback = callback
        self._internal_callback = None

    def start(self):
        def input_callback(_):
            self._rl.callback_read_char()

        self._internal_callback = self.on_line_read
        self._rl.callback_handler_install(self._prompt, self._internal_callback)
        self._env.register_waitable(sys.stdin, input_callback)

    def is_active(self):
        return self._internal_callback != None

    def on_line_read(self, line):
        self._callback(None if line is None else line.decode(self._encoding))

    def stop(self):
        self._env.unregister_waitable(sys.stdin)
        self._rl.callback_handler_remove()
        self._internal_callback = None

    def redisplay(self):
        self._rl.callback_handler_install(self._prompt, self._internal_callback)

    def clear(self):
        sys.stdout.write('\r')

    def write(self, buf):
        self.clear()
        print(buf)
        self.redisplay()
