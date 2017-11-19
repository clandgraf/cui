# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
The IOSelector class provides an abstraction on the select syscall.
"""

import cui
import os
import select

# TODO remove as_update_func

class IOSelector(object):
    """
    The IOSelector class provides an abstraction on the select syscall.

    This class keeps a list of waitables as defined in the select
    documentation, as well as a handler for each waitable. A handler must
    be a callable with the signature ``fn(waitable)`` to process the waitable.
    New waitables may be registered by calling method register
    and unregistered by calling unregister. If a registered waitable has pending
    input, the corresponding handler will be invoked on the next call to select.

    In order to execute asynchronuous events on the thread that calls select,
    an IOSelector object provides a self-pipe. Handlers for such events may
    be registered and unregistered by the register_async and unregister_async
    calls respectively. If an event, identified by a provided string is
    dispatched by calling post_async_event, the corresponding handler function
    will be invoked on select. Note that names must not contain line-breaks,
    as these are used as separators for events on the pipe.

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
        try:
            self._waitables.remove(waitable)
            del self._handlers[id(waitable)]
            if not self._waitables and cui.is_update_func(self.select):
                cui.message('Stopping socket selector')
                cui.remove_update_func(self.select)
        except ValueError:
            pass

    def select(self):
        if not self._waitables:
            return

        readables, _, _ = select.select(self._waitables, [], [], self._timeout)
        for waitable in readables:
            self._handlers[id(waitable)](waitable)

    def register_async(self, name, handler):
        if '\n' in name:
            cui.message('Line-breaks not allowed in async-handler names.')
            return
        self._async_handlers[name] = handler

    def unregister_async(self, name):
        try:
            del self._async_handlers[name]
        except KeyError:
            pass

    def post_async_event(self, name):
        self._fd_write.write('%s\n' % name)
        self._fd_write.flush()

    def _process_async_event(self, name):
        name = self._fd_read.readline()[:-1]
        if name in self._async_handlers:
            self._async_handlers[name](name)
