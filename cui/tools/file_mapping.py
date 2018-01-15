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

    def copy(self):
        fm = FileMapping()
        fm._from = list(self._from)
        fm._to = list(self._to)
        return fm


class TwoStepMapping(FileMapping):
    """
    This class is useful in the rare case, where you want to make a
    mapping between file paths, e.g., because you are using a remote
    debugger, and also need to apply a static mapping after that.

    This is usually the case when you are running on Windows and cui
    is running inside a Cygwin argument. If now you are using a remote
    debugger you may instantiate a file mapping as follows:

    .. code-block:: python

       debugger_mapping = TwoStepMapping(
         cygwin.FILE_MAPPING,
         my_network_mapping
       )

    Note that this class provides no interface to modify static_mapping,
    and its copy method does not make a copy of static_mapping.
    """
    def __init__(self, static_mapping, from_mapping=[]):
        super(TwoStepMapping, self).__init__(from_mapping)
        self._static_mapping = static_mapping

    def _translate(self, file_path, reverse=False):
        if reverse:
            fp1 = super(TwoStepMapping, self)._translate(file_path, reverse)
            fp2 = self._static_mapping._translate(fp1, reverse)
            return fp2
        else:
            fp1 = self._static_mapping._translate(file_path, reverse)
            fp2 = super(TwoStepMapping, self)._translate(fp1, reverse)
            return fp2

    def copy(self):
        fm = TwoStepMapping(self._static_mapping)
        fm._from = list(self._from)
        fm._to = list(self._to)
        return fm
