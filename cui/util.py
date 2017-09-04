

def get_base_classes(object_, is_class=True):
    bases_ = []
    class_ = __class__.__base__ if is_class else object_.__class__
    while class_:
        bases_.append(class_)
        class_ = class_.__base__
    return bases_


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
