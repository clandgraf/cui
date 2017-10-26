# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
The IOSelector class provides an abstraction on the select syscall.
"""

import cui
import os
import select

class IOSelector(object):
    """
    The IOSelector class provides an abstraction on the select syscall.

    This class keeps a list of waitables as defined in the select
    documentation, as well as a handler for each waitable. A handler must
    be a callable with the signature ``fn(waitable)`` to process the waitable.
    New waitables may be registered by calling method register
    and unregistered by calling unregister.

    On each call to select, all waitables with pending input are dispatched
    to their corresponding handler.

    To customize the behaviour of IOSelector, use the parameters ``timeout``,
    which controls the timeout of the select-function and ``as_update_func``,
    which, if set, registers the IOSelector as a cui update-function.
    """

    def __init__(self, timeout=0, as_update_func=True):
        self._timeout = timeout
        self._as_update_func = as_update_func
        self._waitables = []
        self._handlers = {}
        self._async_handlers = {}

        # Initialize self-pipe to handle async events
        # TODO buffersize, ensure name doesnt blow bufsize
        self._pipe = os.pipe()
        self._fd_read = os.fdopen(self._pipe[0], 'r')
        self._fd_write = os.fdopen(self._pipe[1], 'w')
        self.register(self._fd_read, self._process_async_event)

    def register(self, waitable, handler):
        if self._as_update_func and not cui.is_update_func(self.select):
            cui.message('Starting socket selector')
            cui.update_func(self.select)
        self._waitables.append(waitable)
        self._handlers[id(waitable)] = handler

    def unregister(self, waitable):
        self._waitables.remove(waitable)
        del self._handlers[id(waitable)]
        if not self._waitables and cui.is_update_func(self.select):
            cui.message('Stopping socket selector')
            cui.remove_update_func(self.select)

    def select(self):
        if not self._waitables:
            return

        readables, _, _ = select.select(self._waitables, [], [], self._timeout)

        for waitable in readables:
            self._handlers[id(waitable)](waitable)

    def register_async(self, name, handler):
        # TODO name should contain no '\n', and not exceed bufsize
        self._async_handlers[name] = handler

    def unregister_async(self, name):
        del self._async_handlers[name]

    def post_async_event(self, name):
        self._fd_write.write('%s\n' % name)
        self._fd_write.flush()

    def _process_async_event(self, name):
        name = self._fd_read.readline()
        # TODO check if handler exists
        self._async_handlers[name[:-1]](name[:-1])
