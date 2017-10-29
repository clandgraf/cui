from cui.util import add_to_sys_path, local_file

add_to_sys_path(local_file(__file__, 'themes'))

import cui
import cui_emacs
import cui_pydevd
import cui_pydevd.emacs
import tomorrow_night_blue

cui.set_variable(['emacs', 'emacsclient'], 'c:/Program Files/emacs/bin/emacsclient')
cui.set_variable(['emacs', 'file-mapping'], [('/',           'c:/cygwin/'),
                                             ('/cygdrive/c', 'c:/')])
cui.set_variable(['logging', 'pydevds-comm'], True)
