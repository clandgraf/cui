import cui

# Predef. Colors
cui.def_colors('black',       '#2d2d2d')
cui.def_colors('red',         '#f2777a')
cui.def_colors('green',       '#99cc99')
cui.def_colors('yellow',      '#ffcc66')
cui.def_colors('blue',        '#6699cc')
cui.def_colors('magenta',     '#cc99cc')
cui.def_colors('cyan',        '#66cccc')
cui.def_colors('white',       '#cccccc')

# Addit. Colors
cui.def_colors('orange',      '#f99157')
cui.def_colors('light_grey',  '#999999')
cui.def_colors('medium_grey', '#515151')
cui.def_colors('dark_grey',   '#393939')

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
