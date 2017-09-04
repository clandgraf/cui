from cui.core import Core

def def_colors(name, string):
    return Core().def_colors(name, string)

def def_foreground(fg_type, color_name):
    return Core().def_foreground(fg_type, color_name)

def def_background(bg_type, color_name):
    return Core().def_background(bg_type, color_name)

def def_variable(path, value=None):
    return Core().def_variable(path, value)

def set_variable(path, value=None):
    return Core().set_variable(path, value)

def get_variable(path):
    return Core().get_variable(path)

def switch_buffer(buffer_class, *args):
    return Core().switch_buffer(buffer_class, *args)

def message(msg):
    return Core().logger.log(msg)
