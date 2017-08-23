import curses
import re

KEYNAME_MAP = {
    'KEY_UP':     '<up>',
    'KEY_SR':     'S-<up>',
    'kUP3':       'M-<up>',
    'kUP4':       'M-S-<up>',
    'kUP5':       'C-<up>',
    'kUP6':       'C-S-<up>',
    'kUP7':       'C-M-<up>',

    'KEY_DOWN':   '<down>',
    'KEY_SF':     'S-<down>',
    'kDN3':       'M-<down>',
    'kDN4':       'M-S-<down>',
    'kDN5':       'C-<down>',
    'kDN6':       'C-S-<down>',
    'kDN7':       'C-M-<down>',

    'KEY_LEFT':   '<left>',
    'KEY_SLEFT':  'S-<left>',
    'kLFT3':      'M-<left>',
    'kLFT4':      'M-S-<left>',
    'kLFT5':      'C-<left>',
    'kLFT6':      'C-S-<left>',
    'kLFT7':      'C-M-<left>',

    'KEY_RIGHT':  '<right>',
    'KEY_SRIGHT': 'S-<right>',
    'kRIT3':      'M-<right>',
    'kRIT4':      'M-S-<right>',
    'kRIT5':      'C-<right>',
    'kRIT6':      'C-S-<right>',
    'kRIT7':      'C-M-<right>',
}

KEY_FN_PATTERN = re.compile('KEY_F\\((\d+)\\)')

def translate_keyname(keyname, meta=False):
    if keyname.startswith('^'):
        return 'C-' + translate_keyname(keyname[1:], meta=meta)
    elif meta:
        return 'M-' + translate_keyname(keyname)

    fn_match = KEY_FN_PATTERN.match(keyname)
    if fn_match:
        fn_idx = int(fn_match.group(1))
        return \
            ('<f%s>'     % (fn_idx))      if fn_idx < 13 else \
            ('S-<f%s>'   % (fn_idx - 12)) if fn_idx < 25 else \
            ('C-<f%s>'   % (fn_idx - 24)) if fn_idx < 37 else \
            ('C-S-<f%s>' % (fn_idx - 36))

    return KEYNAME_MAP.get(keyname, keyname.lower())


def read_keychord(screen, timeout):
    key = screen.getch()
    if key == -1:
        return None
    if key == 27:
        try:
            screen.timeout(0)
            key = screen.getch()
            if key == -1:
                return '<esc>'
            else:
                return translate_keyname(curses.keyname(key), meta=True)
        finally:
            screen.timeout(timeout)
    else:
        return translate_keyname(curses.keyname(key))
