
class KeymapTest(object):
    __metaclass__ = WithKeymapMeta
    __keymap__ = {
        'C-i C-M-k': lambda: 0
    }

    def __init__(self):
        self._keymap = Keymap({}, self.__class__)


class KeymapTest1(KeymapTest):
    pass
