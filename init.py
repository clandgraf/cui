from cui.util import add_to_sys_path, local_file

add_to_sys_path(local_file(__file__, 'themes'))

import cui
import cui_emacs
import pydevds
import pydevds.emacs
import tomorrow_night_eighties

cui.set_variable(['emacsclient'], 'c:/Program Files/emacs/bin/emacsclient')
#cui.set_variable(['logging', 'emacs-calls'], True)
