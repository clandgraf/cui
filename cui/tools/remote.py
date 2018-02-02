# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui

from .server import LineBufferedSession, Server

cui.def_variable(['cui-remote', 'host'], 'localhost')
cui.def_variable(['cui-remote', 'port'], 5000)

class RemoteSession(LineBufferedSession):
    def __init__(*args, **kwargs):
        super(RemoteSession, self).__init__(*args, encoding='unicode_escape', **kwargs)

    def handle_line(self, line):
        print(line)

cui.def_variable(
    ['cui-remote', 'server'],
    Server(RemoteSession, ['cui-remote', 'host'], ['cui-remote', 'port'])
)

@cui.api_fn
def remote_start():
    cui.def_variable(['cui-remote', 'server']).start()

@cui.api_fn
def remote_stop():
    cui.def_variable(['cui-remote', 'server']).shutdown()
