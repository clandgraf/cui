# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import json

from cui_tools.server import LineBufferedSession, Server
from cui_tools.util import last_exception_repr, unescape_c, escape_c

cui.def_variable(['cui-remote', 'host'], 'localhost')
cui.def_variable(['cui-remote', 'port'], 5000)

class RemoteSession(LineBufferedSession):
    def __init__(self, *args, **kwargs):
        super(RemoteSession, self).__init__(*args, encoding='utf-8', **kwargs)

    def handle_line(self, line):
        # Echo Server Test
        try:
            msg = json.loads(line)
            if msg['type'] == 'eval':
                self.send_response('result', str(cui.eval_python(unescape_c(msg.get('line')))))
        except:
            cui.exception()

            _, trace = last_exception_repr()
            self.send_response('trace', trace)

    def send_response(self, rtype, line):
        self.send_line(json.dumps({
            'type': rtype,
            'line': escape_c(line),
        }))

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
