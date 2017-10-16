# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import os
import subprocess

from cui.util import local_file
from cui_emacs.parser import parse
from cui_emacs.util import LispException

FUNCTION_TEMPLATE = "(defun %(name)s (%(args)s) %(body)s)"

FUNCTION_LIST = []

DEFERRED_FN_INFO = []

cui.def_variable(['emacsclient'], 'emacsclient')
cui.def_variable(['logging', 'emacs-calls'], False)

def _convert_arg(arg):
    if isinstance(arg, str):
        return ("\"%s\"" % arg).encode('unicode_escape').decode('utf-8')
    elif isinstance(arg, int):
        return repr(arg)

    raise LispException("Unsupported arg-type: %s" % type(arg))

def evaluate(string):
    if cui.get_variable(['logging', 'emacs-calls']):
        cui.message(string)

    proc = subprocess.run([cui.get_variable(['emacsclient']), "-e", string],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if (proc.returncode != 0):
        raise LispException(proc.stderr.decode('utf-8'))
    return parse(proc.stdout.decode('utf-8').strip())

def _set_function_info(fn, info):
    fn.__doc__ = info

def _retrieve_function_info(symbol, info_fn='#\'documentation'):
    return evaluate("(funcall %s #'%s)" % (info_fn, symbol))

def _retrieve_function_infos(symbols, info_fn='#\'documentation'):
    return evaluate("(mapcar %s (list %s))"
                    % (info_fn,
                       ' '.join(('#\'%s' % sym for sym in symbols))))

def declare_function(name):
    """Declare an existing function in emacs lisp."""
    def _fn(*args):
        return evaluate("(%s %s)"
                        % (name,
                           ' '.join(map(_convert_arg, args))))
    if (cui.has_run(initialize)):
        _set_function_info(_fn, _retrieve_function_info(name))
    else:
        DEFERRED_FN_INFO.append((name, _fn))
    return _fn


def defun(e_name, e_args, body=None, path_to_body=None):
    """Define a function from python code."""
    argstring = ' '.join(e_args)
    if not body:
        if not path_to_body:
            raise LispException('No definition for %s(%s)' % (ename, argstring))
        with open(path_to_body, 'r') as f:
            body = f.read()

    lisp = FUNCTION_TEMPLATE % {'name': e_name,
                                'args': argstring,
                                'body': body}
    if cui.has_run(initialize):
        out = evaluate(lisp)
    else:
        FUNCTION_LIST.append(lisp)
    return declare_function(e_name)


@cui.post_init_func
def initialize():
    proc = subprocess.run([cui.get_variable(['emacsclient']), '--version'],
                          universal_newlines=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if (proc.returncode != 0):
        raise LispException(proc.stderr)
    cui.message(proc.stdout)
    # define functions from python
    while len(FUNCTION_LIST):
        evaluate(FUNCTION_LIST.pop(0))

    # retrieve doc for declared functions
    global DEFERRED_FN_INFO
    while DEFERRED_FN_INFO:
        fns = DEFERRED_FN_INFO[:10]
        for fn, info in zip((fn for _, fn in fns),
                            _retrieve_function_infos((sym for sym, _ in fns))):
            _set_function_info(fn, info)
        DEFERRED_FN_INFO = DEFERRED_FN_INFO[10:]
