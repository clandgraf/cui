import cui

# Core Faces
cui.def_foreground('modeline_active',   'white')
cui.def_background('modeline_active',   'medium_grey')
cui.def_foreground('modeline_inactive', 'light_grey')
cui.def_background('modeline_inactive', 'dark_grey')
cui.def_foreground('selection',         None)
cui.def_background('selection',         'dark_grey')
cui.def_foreground('divider',           'medium_grey')
cui.def_foreground('special',           None)
cui.def_background('special',           'medium_grey')

# Pydevds Faces
cui.def_foreground('comment',           'light_grey')
cui.def_foreground('keyword',           'green')
cui.def_foreground('function',          'orange')
cui.def_foreground('string',            'cyan')
cui.def_foreground('string_escape',     'medium_grey')
cui.def_foreground('string_interpol',   'medium_grey')
cui.def_foreground('py_decorator',      'blue')
