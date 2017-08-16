

def get_base_classes(object_, is_class=True):
    bases_ = []
    class_ = __class__.__base__ if is_class else object_.__class__
    while class_:
        bases_.append(class_)
        class_ = class_.__base__
    return bases_


def deep_put(dict_, key_path, value):
    if len(key_path) == 0:
        raise KeyError('Can not deep_put using empty path.')

    dict_anchor = dict_
    for key in key_path[:-1]:
        if key not in dict_anchor:
            dict_anchor[key] = {}
        dict_anchor = dict_anchor[key]
    dict_anchor[key_path[-1]] = value


def deep_get(dict_, key_path):
    if len(key_path) == 0:
        raise KeyError('Can not deep_get using empty path.')

    dict_anchor = dict_
    for key in key_path:
        if not hasattr(dict_anchor, 'get'):
            return None
        dict_anchor = dict_anchor.get(key)
        if dict_anchor is None:
            return None
    return dict_anchor
