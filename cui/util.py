# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from operator import add
from functools import reduce

def translate_path(file_map, file_path, reverse=False):
    from_index = 1 if reverse else 0
    to_index =   0 if reverse else 1

    for mapping in file_map:
        from_prefix = mapping[from_index]
        to_prefix =   mapping[to_index]
        if file_path.startswith(from_prefix):
            return to_prefix + file_path[len(from_prefix):]
    return file_path

def add_to_sys_path(p):
    sys.path.append(p)

def local_file(module_file, path):
    return os.path.join(os.path.dirname(module_file), path)

def intersperse(lst, sep):
    return reduce(add, [(e, sep) for e in lst])[:-1]

def get_base_classes(object_, is_class=True):
    bases_ = []
    class_ = __class__.__base__ if is_class else object_.__class__
    while class_:
        bases_.append(class_)
        class_ = class_.__base__
    return bases_


def minmax(minimum, value, maximum):
    return max(minimum, min(value, maximum))


def _deep_error(path):
    raise KeyError('Path %s does not exist.' % path)


def deep_put(dict_, key_path, value, create_path=True):
    if len(key_path) == 0:
        raise KeyError('Can not deep_put using empty path.')

    dict_anchor = dict_
    for key in key_path[:-1]:
        if key not in dict_anchor:
            if create_path:
                dict_anchor[key] = {}
            else:
                _deep_error(key_path)
        dict_anchor = dict_anchor[key]
    dict_anchor[key_path[-1]] = value


def deep_get(dict_, key_path, return_none=True):
    if len(key_path) == 0:
        raise KeyError('Can not deep_get using empty path.')

    dict_anchor = dict_
    for key in key_path:
        if not hasattr(dict_anchor, 'get'):
            if return_none:
                return None
            else:
                _deep_error(key_path)
        dict_anchor = dict_anchor.get(key)
        if dict_anchor is None:
            if return_none:
                return None
            else:
                _deep_error(key_path)
    return dict_anchor
