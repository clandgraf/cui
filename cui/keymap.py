# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from cui.util import deep_put, deep_get, get_base_classes

skey_map = set(['<f1>', '<f2>', '<f3>', '<f4>', '<f5>', '<f6>', '<f7>', '<f8>',
                '<f9>', '<f10>', '<f11>', '<f12>',
                '<tab>', '<del>', '<enter>', '<down>', '<up>', '<left>', '<right>',
                '<pgup>', '<pgdown>', '<home>', '<end>'])
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
    unknown_modifiers = list(filter(lambda m: m not in modifiers, ms))
    if unknown_modifiers:
        raise KeyError('Encountered unknown modifiers: %s' % unknown_modifiers)

    return sorted(ms, key=modifiers.index)


class Keymap(object):
    def __init__(self, keymap, supers=[]):
        self.supers = supers
        self._keymap = {}
        for key in keymap:
            self.__setitem__(parse_keychord_string(key),
                             keymap[key])

    def flattened(self):
        # TODO must include parent classes keymaps
        flat = {}
        for super_ in self.supers:
            flat.update(super_.__keymap__.flattened())
        kstack = [{'keymap': self._keymap, 'keys': list(self._keymap.keys())}]
        prefix = []
        while kstack:
            while kstack[0]['keys']:
                current_key = kstack[0]['keys'].pop(0)
                prefix.append(current_key)
                keymap_or_fn = kstack[0]['keymap'][current_key]
                if isinstance(keymap_or_fn, dict):
                    kstack.insert(0, {'keymap': keymap_or_fn, 'keys': list(keymap_or_fn.keys())})
                    break
                else:
                    flat[' '.join(prefix)] = keymap_or_fn
                    prefix.pop(-1)
            else:
                kstack.pop(0)
                if len(kstack):
                    prefix.pop(-1)
        return flat


    def __getitem__(self, keychords):
        fn = deep_get(self._keymap, keychords)
        if fn is None:
            for super_ in self.supers:
                fn = super_.__keymap__[keychords]
                if fn:
                    break
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
        keymap_bases = list(filter(lambda base: isinstance(base, WithKeymapMeta), bases))
        cls.__keymap__ = Keymap(dct.get('__keymap__', {}), keymap_bases)
        super(WithKeymapMeta, cls).__init__(name, bases, dct)


class WithKeymap(object, metaclass=WithKeymapMeta):
    """Superclass for objects handling keyboard input.
    """
    def __init__(self):
        self._keymap = Keymap({}, [self.__class__])

    def input_delegate(self):
        return None

    def _handle_input(self, keychords):
        key_fn = self._keymap[keychords]
        if key_fn is None:
            # keychord prefix is undefined in this keymap
            return None
        elif isinstance(key_fn, dict):
            # Incomplete keychord
            return False
        else:
            # keychord is handled
            key_fn()
            return True

    def handle_input(self, keychords):
        """Handling input from cui.input.
        A return value is None means the received keychord prefix has no match in
        this handler, and should be directed to the next handler.
        If this method returns False, a prefix match is found, but the keychord is
        not yet complete.
        If this method returns True, the associated method has been executed.
        """
        is_keychord_handled = None
        delegate = self.input_delegate()
        if delegate:
            is_keychord_handled = delegate.handle_input(keychords)
        if is_keychord_handled is None:
            is_keychord_handled = self._handle_input(keychords)

        return is_keychord_handled
