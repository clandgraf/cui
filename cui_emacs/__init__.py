# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import os
import subprocess

from cui.util import local_file

FUNCTION_TEMPLATE = "(defun %(name)s (%(args)s) %(body)s)"

FUNCTION_LIST = []

cui.def_variable(['emacsclient'], 'emacsclient')

class LispException(Exception):
    pass

def _convert_arg(arg):
    if isinstance(arg, str):
        return ("\"%s\"" % arg).encode('unicode_escape').decode('utf-8')
    elif isinstance(arg, int):
        return repr(arg)

    raise LispException("Unsupported arg-type: %s" % type(arg))


def evaluate(string):
    proc = subprocess.run([cui.get_variable(['emacsclient']), "-e", string],
                          universal_newlines=True,
                          stdout=subprocess.PIPE)
    stdout = proc.stdout
    if (proc.returncode != 0):
        raise LispException(stdout)
    return stdout


def declare_function(name):
    def _fn(*args):
        return evaluate("(%s %s)"
                        % (name,
                           ' '.join(map(_convert_arg, args))))
    return _fn


def defun(e_name, e_args, body=None, path_to_body=None):
    argstring = ' '.join(e_args)
    if not body:
        if not path_to_body:
            raise LispException('No definition for %s(%s)' % (ename, argstring))
        with open(path_to_body, 'r') as f:
            body = f.read()

    lisp = FUNCTION_TEMPLATE % {'name': e_name,
                                'args': argstring,
                                'body': body}
    if cui.running():
        out = evaluate(lisp)
    else:
        FUNCTION_LIST.append(lisp)
    return declare_function(e_name)


@cui.post_init_func
def initialize():
    proc = subprocess.run([cui.get_variable(['emacsclient']), '--version'],
                          universal_newlines=True,
                          stdout=subprocess.PIPE)
    stdout = proc.stdout
    if (proc.returncode != 0):
        raise LispException(stdout)
    cui.message(stdout)
    while len(FUNCTION_LIST):
        evaluate(FUNCTION_LIST.pop(0))
