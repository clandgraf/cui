# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class Logger(object):
    def __init__(self):
        self.messages = []

    def log(self, msg):
        if (len(self.messages) > 1000):
            self.messages.pop(0)
        self.messages.append(msg)

    def clear(self):
        self.messages = []
