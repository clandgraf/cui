# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui

from cui_tools.server import LineBufferedSession, Server

cui.def_variable(['cui-remote', 'host'], 'localhost')
cui.def_variable(['cui-remote', 'port'], 5000)

class RemoteSession(LineBufferedSession):
    def __init__(self, *args, **kwargs):
        super(RemoteSession, self).__init__(*args, encoding='unicode_escape', **kwargs)

    def handle_line(self, line):
        # Echo Server Test
        result = cui.eval_python(line)
        self.send_all((str(result) + '\n').encode('utf-8'))

cui.def_variable(
    ['cui-remote', 'server'],
    Server(
        RemoteSession,
        ['cui-remote', 'host'],
        ['cui-remote', 'port'],
        env=cui,
    )
)

@cui.api_fn
def remote_start():
    cui.get_variable(['cui-remote', 'server']).start()

@cui.api_fn
def remote_stop():
    cui.get_variable(['cui-remote', 'server']).shutdown()
