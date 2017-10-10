import cui
import subprocess

FUNCTION_TEMPLATE = "(defun %(name)s (%(args)s) %(body)s)"

FUNCTION_LIST = []

cui.def_variable(['cui_emacsclient'], 'emacsclient')

class LispException(Exception):
    pass

def _convert_arg(arg):
    if isinstance(arg, str):
        return "\"%s\"" % arg
    elif isinstance(arg, int):
        return repr(arg)

    raise LispException("Unsupported arg-type: %s" % type(arg))

def eval_in_emacs(string):
    proc = subprocess.run([cui.get_variable(['cui_emacsclient']), "-e", string], stdout=subprocess.PIPE)
    if (proc.returncode != 0):
        raise LispException(proc.stdout)
    return proc.stdout

def defun(e_name, e_args, body):
    lisp = FUNCTION_TEMPLATE % {'name': e_name,
                                'args': ' '.join(e_args),
                                'body': body}
    if cui.running():
        out = eval_in_emacs(lisp)
    else:
        FUNCTION_LIST.append(lisp)

    def _fn(*args):
        return eval_in_emacs("(%s %s)"
                             % (e_name,
                                ' '.join(map(_convert_arg, args))))
    return _fn


@cui.post_init_func
def initialize_lisp():
    proc = subprocess.run([cui.get_variable(['cui_emacsclient']), '--version'], stdout=subprocess.PIPE)
    if (proc.returncode != 0):
        raise LispException(proc.stdout)
    cui.message(proc.stdout)
    while len(FUNCTION_LIST):
        eval_in_emacs(FUNCTION_LIST.pop(0))


display_line = defun("cui--display-line", ["file-name line-number"],
                     """(let ((buffer (find-file-noselect file-name)))
                          (if (null buffer)
                            (message "Cannot access file.")
                            (select-window (display-buffer buffer))
                            (goto-char 0)
                            (forward-line (- line-number 1))))""")
