# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import imp
import traceback

from cui import core

def main():
    c = core.Core()
    try:
        imp.load_source('cui._user_init', './init.py')
        c.run()
    except:
        c.logger.log(traceback.format_exc())

if __name__ == '__main__':
    main()
