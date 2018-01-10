# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from operator import itemgetter


class FileMapping(object):
    def __init__(self, from_mapping=[]):
        self._from = []
        self._to = []

        self.add_all(from_mapping)

    def add(self, from_prefix, to_prefix):
        self._from.append((from_prefix, to_prefix))
        self._from.sort(key=itemgetter(0), reverse=True)
        self._to.append((to_prefix, from_prefix))
        self._to.sort(key=itemgetter(0), reverse=True)

    def add_all(self, mappings):
        for from_prefix, to_prefix in mappings:
            self.add(os.path.join(from_prefix, ''),
                     os.path.join(to_prefix, ''))

    def remove(self, from_prefix, to_prefix):
        self._from.remove((from_prefix, to_prefix))
        self._to.remove((to_prefix, from_prefix))

    def remove_all(self, mappings):
        for from_prefix, to_prefix in mappings:
            self.remove(from_prefix, to_prefix)

    def _translate(self, file_path, reverse=False):
        for mapping in self._to if reverse else self._from:
            if file_path.startswith(mapping[0]):
                return mapping[1] + file_path[len(mapping[0]):]
        return file_path

    def to_other(self, file_path):
        return self._translate(file_path)

    def to_this(self, file_path):
        return self._translate(file_path, reverse=True)
