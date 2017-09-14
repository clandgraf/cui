from cui.core import Core as _Core

def def_colors(name, string):
    return _Core().def_colors(name, string)

def def_foreground(fg_type, color_name):
    return _Core().def_foreground(fg_type, color_name)

def def_background(bg_type, color_name):
    return _Core().def_background(bg_type, color_name)

def def_variable(path, value=None):
    return _Core().def_variable(path, value)

def set_variable(path, value=None):
    return _Core().set_variable(path, value)

def get_variable(path):
    return _Core().get_variable(path)

def switch_buffer(buffer_class, *args):
    return _Core().switch_buffer(buffer_class, *args)

def current_buffer():
    return _Core().current_buffer()

def message(msg):
    return _Core().logger.log(msg)
