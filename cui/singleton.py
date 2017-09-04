

def combine_meta_classes(*args, **kwargs):
    return type('Combined(%s)'
                % ', '.join(map(lambda c: c.__name__, args)),
                tuple(args),
                kwargs)


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
