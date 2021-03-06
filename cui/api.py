# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import functools
import os
import pathlib

from cui.core import \
    context, core_api_ns, Core, \
    init_func, update_func, post_init_func, \
    runloop_cancel, runloop_result, \
    run_interactive, interactive
from cui.colors import ColorException
from cui.util import add_to_sys_path


with core_api_ns(globals()) as core_api:
    core_api('message')
    core_api('exception')
    core_api('is_update_func')
    core_api('remove_update_func')
    core_api('add_exit_handler')
    core_api('remove_exit_handler')
    core_api('running')
    core_api('bye',                    'C-x C-c')
    core_api('runloop_enter')
    core_api('runloop_level')
    core_api('activate_minibuffer')

    core_api('def_variable')
    core_api('get_variable')
    core_api('set_variable')

    core_api('current_buffer')
    core_api('create_buffer')
    core_api('select_buffer')
    core_api('get_buffer')
    core_api('get_buffers')
    core_api('kill_buffer_object')
    core_api('previous_buffer',        'S-<tab>')
    core_api('next_buffer',            '<tab>')

    core_api('new_window_set',         'C-x 5 2')
    core_api('has_window_set')
    core_api('delete_window_set',      'C-x 5 0')
    core_api('delete_window_set_by_name')
    core_api('next_window_set',        'C-M-n')
    core_api('previous_window_set',    'C-M-p')
    core_api('split_window_below',     'C-x 2')
    core_api('split_window_right',     'C-x 3')
    core_api('select_window')
    core_api('find_window')
    core_api('selected_window')
    core_api('select_next_window',     'M-n')
    core_api('select_previous_window', 'M-p')
    core_api('select_left_window',     'M-<left>')
    core_api('select_right_window',    'M-<right>')
    core_api('select_top_window',      'M-<up>')
    core_api('select_bottom_window',   'M-<down>')
    core_api('delete_all_windows',     'C-x 1')
    core_api('delete_selected_window', 'C-x 0')

    core_api('get_colors')
    core_api('get_backgrounds')
    core_api('get_foregrounds')


def base_directory(*args):
    return os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), *args)

def user_directory(*args):
    return os.path.join(os.path.expanduser(os.path.join(pathlib.Path.home(), '.cui')), *args)

# Shortcuts

def _set_key(keymap, keychord, fn):
    old_fn = keymap.get_keychord(keychord)
    if old_fn:
        message('Overwriting shortcut \'%s\'.' % old_fn.__name__)
    return keymap.set_keychord(keychord, fn)


def set_global_key(keychord, fn):
    return _set_key(Core, keychord, fn)


def set_local_key(buffer_class, keychord, fn):
    return _set_key(buffer_class, keychord, fn)


def global_key(keychord):
    def _global_key(fn):
        set_global_key(keychord, fn)
        return fn
    return _global_key


def local_key(buffer_class, keychord):
    def _local_key(fn):
        set_local_key(buffer_class, keychord, fn)
        return fn
    return _local_key


def api_fn(fn):
    globals()[fn.__name__] = fn
    return fn


def buffer_keys(keychord, name=None):
    def _buffer_keys(class_):
        def switch_to_buffer():
            switch_buffer(class_)
        if name:
            switch_to_buffer.__name__ = name
        switch_to_buffer.__doc__ = '\nSwitch to buffer %s\n' % class_.__name__
        api_fn(set_global_key(keychord, switch_to_buffer))
        return class_
    return _buffer_keys


def has_run(fn):
    """
    Determine if an init_func or a post_init_func
    has been successfully executed.
    """
    return getattr(fn, '__has_run__')

# =============== Minibuffer Input primitives ===================

def complete_from_list(list_function):
    def _complete_from_list(display_completions):
        def __complete_from_list(completion_id, buffer_content):
            matches = list(filter(lambda m: m.startswith(buffer_content), list_function()))
            prefix = os.path.commonprefix(matches)
            if len(matches) == 0:
                message('No completions.')
                return buffer_content
            elif len(matches) > 1:
                display_completions(completion_id, matches)
            return prefix
        return __complete_from_list
    return _complete_from_list


def read_integer(prompt, default=''):
    while True:
        try:
            return int(read_string(prompt, default=default))
        except ValueError:
            message('Enter an integer.')


def read_bool(prompt, default=False):
    while True:
        result = read_string('%s (yes/no)' % prompt,
                             default=('yes' if default else 'no'))
        if result == 'yes':
            return True
        elif result == 'no':
            return False
        else:
            message('Enter yes or no.')


def read_string(prompt, default='', complete_fn=None):
    return runloop_enter(lambda: activate_minibuffer(
        '%s: ' % prompt,
        lambda b: runloop_result(b),
        default,
        complete_fn(display_completions) if complete_fn else None,
        close_completions
    ))


def complete_files(display_completions):
    def _complete_files(completion_id, buffer_content):
        basename = os.path.basename(buffer_content)
        dirname = os.path.dirname(buffer_content)
        matches = list(filter(lambda d: d.startswith(basename), os.listdir(dirname)))
        prefix = os.path.commonprefix(matches)
        result = os.path.join(dirname, prefix)
        if len(matches) == 0:
            message('No completions.')
            return buffer_content
        elif len(matches) == 1:
            if os.path.isdir(result):
                return os.path.join(result, '')
        else:
            display_completions(completion_id,
                                list(map(lambda match: [os.path.join(dirname, ''),
                                                        {'content': match,
                                                         'attributes': ['bold']}],
                                         matches)))
        return result
    return _complete_files


def read_file(prompt, default=None):
    """
    Read a file from minibuffer.

    If no ``default`` is provided, the ``cwd`` of the current buffer
    will be used as default. If this yields no value, the systems
    current working directory will be used.

    :param prompt: Prompt to be displayed
    :param default: If provided the default value of
                    the minibuffer is set to this
    """
    f = os.path.join(default or current_buffer(no_minibuffer=True).cwd, '')

    while True:
        f = read_string(prompt, f, complete_files)
        if os.path.exists(f):
            return f
        message('File \'%s\' does not exist.' % f)

# ==================== Execute functions =======================

@global_key('M-x')
@interactive(lambda: read_string('Command',
                                 complete_fn=complete_from_list(lambda: globals().keys())))
def exec_command(command):
    """
    Execute a command interactively.

    The command must be a callable defined in the ``cui.api`` namespace that
    either takes no parameters or is wrapped with the interactive decorator.
    To make a function available to ``exec_command`` you may use the api_fn
    decorator.

    :param command: The command to be executed.
    """
    result = run_interactive(globals()[command])
    if result:
        message(str(result))
    return result


@global_key('M-e')
@interactive(lambda: read_string('Eval'))
def eval_python(code_string):
    """
    Evaluate Python expression ``code_string``
    in the context of ``cui.api``.

    :param code_string: A string containing a python expression
    """
    try:
        code_object = compile(code_string, '<string>', 'eval')
    except SyntaxError:
        code_object = compile(code_string, '<string>', 'exec')

    return eval(code_object, globals())

# ==================== Event handling =======================

def register_waitable(waitable, handler):
    """
    Register object waitable to the cui event-loop.
    If input is available function handler will be executed,
    with the waitable as argument.

    :param waitable: The waitable object to be registered
    :param handler: A handler function that will be invoked,
                    when input is available on waitable
    """
    return Core().io_selector.register(waitable, handler)

def unregister_waitable(waitable):
    """
    Unregister the waitable object ``waitable``, which has
    previously been registered by a call to ``register_waitable``.

    :param waitable: The waitable object to be unregistered
    """
    return Core().io_selector.unregister(waitable)

def register_async_event(name, handler):
    """
    Introduces a new event type identified by ``name`` for
    asynchronuous events to the cui event-loop. The provided
    ``handler`` will be invoked, if ``post_async_event`` is
    called with ``name`` as parameter.

    This function is typically used to handle the results of
    asynchronuous processes, such as signals or threads, in
    the cui event-loop.

    :param name: A string that is used as an identifier for
                 the event type.
    :param handler: The handler function for the event type.
    """
    return Core().io_selector.register_async(name, handler)

def unregister_async_event(name):
    return Core().io_selector.unregister_async(name)

def post_async_event(name):
    """
    Invoke the asynchronuous event handler identified by ``name``.
    """
    return Core().io_selector.post_async_event(name)

# Hooks

def def_hook(path):
    return def_variable(path, [])

def add_hook(path, fn):
    hooks = get_variable(path)
    if fn not in hooks:
        hooks.append(fn)

def remove_hook(path, fn):
    hooks = get_variable(path)
    hooks.remove(fn)

def run_hook(path, *args, **kwargs):
    for hook in get_variable(path):
        hook(*args, **kwargs)

# Colors

@interactive(lambda: read_string('Color name',
                                 complete_fn=complete_from_list(get_colors)),
             lambda: read_string('Color (hex string)'))
def def_colors(name, string):
    """
    Define a new color or redefine an existing color.

    The color should be specified as a hex color-string in the format
    ``#rrggbb``. If the name provided already exists, the color will
    be redefined, if it is a new color, it will be created.

    :param name: The name of the color
    """
    try:
        return Core().def_colors(name, string)
    except ColorException as e:
        message('%s' % e)


@interactive(lambda: read_string('Background type',
                                 complete_fn=complete_from_list(get_backgrounds)))
def get_background(bg_type):
    return Core().get_background_color(bg_type)


@interactive(lambda: read_string('Background type',
                                 complete_fn=complete_from_list(get_backgrounds)),
             lambda: read_string('Color name',
                                 complete_fn=complete_from_list(get_colors)))
def def_background(bg_type, color_name):
    """
    Redefine an existing background definition.

    The name should correspond to a color definition previously
    defined with ``def_colors``. To get a list of available
    background types, the function ``get_backgrounds`` may be used.
    To get a list of defined color names, use the function
    ``get_colors``.

    :param bg_type: One of the background types in ``get_backgrounds``.
    :param color_name: One of the color names defined with ``def_colors``.
    """
    try:
        return Core().def_background(bg_type, color_name)
    except ColorException as e:
        message('%s' % e)


@interactive(lambda: read_string('Foreground type',
                                 complete_fn=complete_from_list(get_foregrounds)))
def get_foreground(fg_type):
    return Core().get_foreground_color(fg_type)


@interactive(lambda: read_string('Foreground type',
                                 complete_fn=complete_from_list(get_foregrounds)),
             lambda: read_string('Color name',
                                 complete_fn=complete_from_list(get_colors)))
def def_foreground(fg_type, color_name):
    try:
        return Core().def_foreground(fg_type, color_name)
    except ColorException as e:
        message('%s' % e)

# Buffers


def with_created_buffer(fn):
    def _fn(buffer_class, *args, **kwargs):
        return fn(create_buffer(buffer_class, *args), **kwargs)
    return _fn

@api_fn
def buffer_window(buffer_object, current_window_set=False):
    """
    Returns the first window that displays the provided buffer object.
    If current_window_set is set, restrict search to current window_set.

    :param buffer_object: A buffer_object
    :param current_window_set: If True search is restricted to current
                               window_set.
    """
    return find_window(lambda w: w.buffer() == buffer_object, current_window_set=current_window_set)

@with_created_buffer
def buffer_visible(buffer_object, split_method=split_window_below, to_window=False):
    """
    Ensures buffer exists and is visible in current window set.

    This function returns the window displaying the buffer_object
    identified by ``buffer_class`` and ``*args``, as well as the
    buffer_object itself. If the buffer does not exist it is
    instantiated, if it is not displayed a window will be chosen
    based on split_method and the buffer will be dipslayed in it.

    :param buffer_class:
    :param args:
    :param split_method:
        Method of creating the window. Pass as kwarg.
        - ``None`` uses the currently selected window.
        - ``cui.split_window_below`` will create a new
          window below the selected one.
        - ``cui.split_window_right`` will create a new
          window right of the selected one.
    :to_window: if set, the window will be selected
    """
    win = buffer_window(buffer_object, current_window_set=True)
    if not win:
        win = split_method() if split_method else selected_window()
        if win:
            win.set_buffer(buffer_object)
    if win and to_window:
        select_window(win)

    return (win, buffer_object)

@with_created_buffer
def switch_buffer(buffer_object):
    return select_buffer(buffer_object)

@global_key('C-x C-k')
def kill_current_buffer():
    """
    Kill the current buffer.
    """
    kill_buffer_object(current_buffer())

# Windows

@contextlib.contextmanager
def window_selected(window):
    old_window = selected_window()
    yield select_window(window)
    select_window(old_window)

def exec_in_buffer_visible(expr, buffer_class, *args, **kwargs):
    """
    Run expr in a window of the current set that displays the buffer,
    creating the buffer and window if necessary.

    Finds the first window in the active set that displays the buffer_object
    specified by buffer_class and args, and executes expr with this window
    selected. If the buffer does not exist, it is created.

    If the window is not exist, a window will be chosen based on the value of
    split_method. split_method must be a function that returns a window.
    The default value is split_window_below. If split_method
    is None the buffer is displayed in the currently selected window.

    All arguments except ``expr`` correspond to ``buffer_visible``.

    :param expr: The expression to be executed
    """
    window, buffer_object = buffer_visible(buffer_class, *args, **kwargs)
    with window_selected(window):
        expr(buffer_object)

def exec_in_buffer_window(expr, buffer_class, *args):
    """
    Run expr in a window of the current set that displays the buffer,
    if that buffer exists and is displayed.

    Finds the first window in the active set that displays the buffer_object
    specified by buffer_class and args, and executes expr with this window
    selected. If no such window exists, expr is not executed

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    """
    buffer_object = get_buffer(buffer_class, *args)
    if buffer_object is None:
        return
    window = buffer_window(buffer_object, current_window_set=True)
    if window:
        with window_selected(window):
            expr(buffer_object)

def exec_if_buffer_exists(expr, buffer_class, *args):
    """
    Run expr with the buffer as argument.

    Finds the first window in the active set that displays the buffer_object
    specified by buffer_class and args, and executes expr with this window
    selected. If no such window exists, expr is not executed

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    """
    buffer_object = get_buffer(buffer_class, *args)
    if buffer_object:
        expr(buffer_object)


def kill_buffer(buffer_class, *args):
    """
    Remove the buffer.

    If the buffer, identified by class buffer_class and arguments args, exists,
    it will be removed from the list of buffers and replaced in all windows
    displaying it.

    :param buffer_class:
        The class of the buffer
    :param args:
        The arguments of the buffer
    """
    exec_if_buffer_exists(lambda b: kill_buffer_object(b),
                          buffer_class, *args)


def display_completions(completion_id, completions):
    """
    Displays the set of possible completions in a
    buffer that is displayed in the currently selected window.

    :param completions: The list of possible completion strings.
    """
    from cui import buffers_std
    exec_in_buffer_visible(lambda b: b.set_completions(completions),
                           buffers_std.CompletionsBuffer,
                           completion_id,
                           split_method=None)


def close_completions(completion_id):
    """
    """
    from cui import buffers_std
    kill_buffer(buffers_std.CompletionsBuffer,
                completion_id)


@interactive(lambda: read_file('JSON File'))
def display_static(json_file):
    from cui import buffers_std
    switch_buffer(buffers_std.StaticBuffer, json_file)


from cui.buffers import ListBuffer, with_current_buffer

@api_fn
@local_key(ListBuffer, 'M-g g')
@with_current_buffer
@interactive(lambda: read_integer('Item'))
def goto_item(b, item):
    return goto_item_in_buffer(b, item)

@api_fn
def goto_item_in_buffer(b, item):
    b.set_variable(['win/buf', 'selected-item'], item)
    b.recenter()
    return item
