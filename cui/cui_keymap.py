from cui.util import deep_put, deep_get, get_base_classes

skey_map = set(['<tab>', '<down>', '<up>'])
modifiers = ['C', 'M', 'S']
modifier_set = set(modifiers)


def parse_keychord_list(ks):
    return ['-'.join(normalize_modifiers(chord[:-1]) + [parse_key(chord[-1])])
            for chord in [chord.split('-')
                          for chord in ks]]


def parse_keychord_string(s):
    return parse_keychord_list(filter(lambda seq: len(seq) != 0, s.split(' ')))


def parse_key(k):
    if len(k) > 1 and k not in skey_map:
        raise KeyError('Unknown special key: %s' % k)

    return k


def normalize_modifiers(ms):
    unknown_modifiers = filter(lambda m: m not in modifiers, ms)
    if unknown_modifiers:
        raise KeyError('Encountered unknown modifiers: %s' % unknown_modifiers)

    return sorted(ms, key=modifiers.index)


class Keymap(object):
    def __init__(self, keymap, super_=None):
        self.super_ = super_
        self._keymap = {}
        for key in keymap:
            self.__setitem__(parse_keychord_string(key),
                             keymap[key])

    def __getitem__(self, keychords):
        fn = deep_get(self._keymap, keychords)
        if fn is None and self.super_:
            fn = self.super_.__keymap__[keychords]
        return fn

    def __setitem__(self, keychords, fn):
        deep_put(self._keymap, keychords, fn)


class WithKeymapMeta(type):
    """Metaclass for handling keyboard input.
    This class should not be used directly, you should rather subclass WithKeymap.
    """
    def __init__(cls, name, bases, dct):
        """Convert a keymap specified as a dictionary to a Keymap object.
        """
        # Find base with keymap
        keymap_bases = filter(lambda base: isinstance(base, WithKeymapMeta), bases)
        if len(keymap_bases) > 1:
            raise TypeError('WithKeymap class should have only one base class with __keymap__')

        cls.__keymap__ = Keymap(dct.get('__keymap__', {}),
                                keymap_bases[0] if len(keymap_bases) else None)
        super(WithKeymapMeta, cls).__init__(name, bases, dct)


class WithKeymap(object):
    """Superclass for objects handling keyboard input.
    """
    __metaclass__ = WithKeymapMeta

    def __init__(self):
        self._keymap = Keymap({}, self.__class__)

    def handle_input(self, keychords):
        """Handling input from cui.input.
        A return value is None means the received keychord prefix has no match in
        this handler, and should be directed to the next handler.
        If this method returns False, a prefix match is found, but the keychord is
        not yet complete.
        If this method returns True, the associated method has been executed.
        """
        key_fn = self._keymap[keychords]
        if key_fn is None:
            return None
        elif isinstance(key_fn, dict):
            return False
        else:
            key_fn(self)
            return True
