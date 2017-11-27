# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import imp
import os
import pathlib
import shutil
import traceback


def create_init_file():
    default_init_path = cui.base_directory('init.py')
    user_init_path = os.path.expanduser(os.path.join(pathlib.Path.home(), '.cui_init.py'))
    if not os.path.exists(user_init_path):
        shutil.copyfile(default_init_path, user_init_path)
    return user_init_path


def main():
    user_init_path = create_init_file()
    imp.load_source('cui._user_init', user_init_path)
    with cui.context() as c:
        try:
            c.run()
        except:
            cui.exception()


if __name__ == '__main__':
    main()
