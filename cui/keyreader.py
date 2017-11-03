# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import curses
import re

EVT_RESIZE = 'key_resize'

KEYCHORD_MAP = {
    'C-m':        '<enter>',
    'C-i':        '<tab>'
}

KEYNAME_MAP = {
    'KEY_HOME':      '<home>',
    'KEY_END':       '<end>',
    'KEY_SHOME':     'S-<home>',
    'kHOM3':         'M-<home>',
    'kHOM4':         'M-S-<home>',
    'kHOM5':         'C-<home>',
    'kHOM6':         'C-S-<home>',
    'kHOM7':         'C-M-<home>',
    'KEY_SEND':      'S-<end>',
    'kEND3':         'M-<end>',
    'kEND4':         'M-S-<end>',
    'kEND5':         'C-<end>',
    'kEND6':         'C-S-<end>',
    'kEND7':         'C-M-<end>',

    'KEY_NPAGE':     '<pgdown>',
    'KEY_SNEXT':     'S-<pgdown>',
    'kNXT3':         'M-<pgdown>',
    'kNXT4':         'M-S-<pgdown>',
    'kNXT5':         'C-<pgdown>',
    'kNXT6':         'C-S-<pgdown>',
    'kNXT7':         'C-M-<pgdown>',
    'KEY_PPAGE':     '<pgup>',
    'KEY_SPREVIOUS': 'S-<pgup>',
    'kPRV3':         'M-<pgup>',
    'kPRV4':         'M-S-<pgup>',
    'kPRV5':         'C-<pgup>',
    'kPRV6':         'C-S-<pgup>',
    'kPRV7':         'C-M-<pgup>',

    'KEY_DC':        '<del>',
    'KEY_BTAB':      'S-<tab>',

    'KEY_UP':        '<up>',
    'KEY_SR':        'S-<up>',
    'kUP3':          'M-<up>',
    'kUP4':          'M-S-<up>',
    'kUP5':          'C-<up>',
    'kUP6':          'C-S-<up>',
    'kUP7':          'C-M-<up>',

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


def translate_keychord(keyname, meta=False):
    mkeys = translate_keyname(keyname, meta)
    return KEYCHORD_MAP.get(mkeys, mkeys)


def read_keychord(screen, timeout, receive_input=False):
    key = screen.getch()
    if key == -1:
        return None, None
    if key == 27:
        try:
            screen.timeout(0)
            key = screen.getch()
            if key == -1:
                return '<esc>', False
            else:
                return translate_keychord(curses.keyname(key).decode('utf-8'),
                                          meta=True), False
        finally:
            screen.timeout(timeout)
    else:
        keyname = curses.keyname(key).decode('utf-8')
        if receive_input and len(keyname) == 1:
            return keyname, True
        return translate_keychord(keyname), False
