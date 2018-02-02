# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import subprocess

from . import file_mapping

MOUNT_DRIVE_RE = re.compile('([A-Z]): on (\S+) *')

def _cygwin_home():
    return subprocess.check_output(['cygpath', '-w', '/']) \
                     .decode('utf-8').split('\n')[0]

def _cygwin_drives():
    for line in subprocess.check_output(['mount']) \
                          .decode('utf-8').split('\n'):
        match = MOUNT_DRIVE_RE.match(line)
        if match:
            yield (match.group(2), match.group(1))

def cygwin_file_mappings():
    yield ('/', _cygwin_home())
    yield from ((cygwin_path, '%s:/' % drive_letter.lower())
                for cygwin_path, drive_letter in _cygwin_drives())


FILE_MAPPING = file_mapping.FileMapping(cygwin_file_mappings())
