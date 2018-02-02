# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class Symbol(object):
    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

SYM_VLINE = Symbol()
SYM_HLINE = Symbol()
SYM_LLCORNER = Symbol()
SYM_LTEE = Symbol()
SYM_RARROW = Symbol()
SYM_DARROW = Symbol()
