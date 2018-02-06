# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
import traceback

def last_exception_repr():
    exc_type, exc_value, exc_tb = sys.exc_info()
    return (
        traceback.format_exception_only(exc_type, exc_value)[-1],
        traceback.format_exc()
    )


def escape_c(string):
    return string.encode('unicode_escape').decode('utf-8')


def unescape_c(string):
    return string.encode('utf-8').decode('unicode_escape')
