import pydevds

def initialize(core):
    core.def_colors('white',      '#e8dfd7')
    core.def_colors('black',      '#203439')
    core.def_colors('light_grey', '#d3cbc4')
    core.def_colors('dark_grey',  '#304247')
    core.def_colors('purple',     '#fc5a7b')

    core.def_foreground('modeline_active',   'purple')
    core.def_foreground('modeline_inactive', 'purple')
    core.def_background('modeline_active',   'dark_grey')
