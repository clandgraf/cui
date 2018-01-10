# Copyright (c) 2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class FileMapping(object):
    def __init__(self, from_mapping=[]):
        self._from = sorted(from_mapping,
                            key=itemgetter(0))
        self._to = sorted([(to_prefix, from_prefix) for from_prefix, to_prefix in from_mapping],
                          key=itemgetter(0))

    def add(self, from_prefix, to_prefix):
        self._from.append((from_prefix, to_prefix))
        self._from.sort(key=itemgetter(0))
        self._from.append((to_prefix, from_prefix))
        self._from.sort(key=itemgetter(0))

    def add_all(self, mappings):
        for from_prefix, to_prefix in mappings:
            self.add(from_prefix, to_prefix)

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
        return self.translate(file_path)

    def to_this(self, file_path):
        return self.translate(file_path, reverse=True)
