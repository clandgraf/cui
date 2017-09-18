import curses
import itertools

from cui.util import get_base_classes, deep_get, deep_put, minmax
from cui.keymap import WithKeymap
from cui import core


def pad_left(width, string):
    if len(string) > width:
        return '%s%s' % ('...', string[-(width - 3):])
    return string


def with_window(f):
    """Decorator that runs function only if buffer is in selected window.
    Note that this modifies the argument list of f, inserting window as
    second positional argument.
    """
    def _with_window(*args, **kwargs):
        self = args[0]
        win = self.window()
        if win:
            f(args[0], win, *args[1:], **kwargs)
    return _with_window


class Buffer(WithKeymap):
    __keymap__ = {}

    @classmethod
    def name(cls, *args):
        return None

    def __init__(self, *args):
        super(Buffer, self).__init__()
        self.args = args
        self._state = {'win/buf': {}}

    def window(self):
        selected_window = core.Core().selected_window()
        return selected_window if self == selected_window.buffer() else None

    def def_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=True)

    def set_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=False)
        if path[0] == 'win/buf':
            selected_window = self.window()
            if selected_window:
                selected_window.update_state(path[1:], value)

    def get_variable(self, path):
        return deep_get(self._state, path, return_none=False)

    def buffer_name(self):
        return self.name(*self.args)

    def prepare(self):
        pass

    def line_count(self):
        pass

    def get_lines(self, window):
        pass


class ListBuffer(Buffer):
    __keymap__ = {
        '<up>':     lambda: core.Core().current_buffer().item_up(),
        '<down>':   lambda: core.Core().current_buffer().item_down(),
        'S-<up>':   lambda: core.Core().current_buffer().scroll_up(),
        'S-<down>': lambda: core.Core().current_buffer().scroll_down(),
        'C-l':      lambda: core.Core().current_buffer().recenter(),
        'C-j':      lambda: core.Core().current_buffer().on_item_selected()
    }

    def __init__(self, *args):
        super(ListBuffer, self).__init__(*args)
        self._item_height = 1
        self.def_variable(['win/buf', 'first-row'], 0)
        self.def_variable(['win/buf', 'selected-item'], 0)

    def scroll_up(self):
        first_row = self.get_variable(['win/buf', 'first-row'])
        if first_row > 0:
            self.set_variable(['win/buf', 'first-row'],
                              first_row - 1)

    def scroll_down(self):
        first_row = self.get_variable(['win/buf', 'first-row'])
        if first_row + 4 < self.line_count():
            self.set_variable(['win/buf', 'first-row'],
                              first_row + 1)

    @with_window
    def recenter(self, window, out_of_bounds=False):
        max_lines = window.dimensions[0]
        first_row = self.get_variable(['win/buf', 'first-row'])
        selected_row = self.get_variable(['win/buf', 'selected-item']) * self._item_height
        selected_row_offset = selected_row - first_row
        if not out_of_bounds or \
           selected_row_offset < 0 or \
           selected_row_offset > max_lines - 1:
            center = first_row - (max_lines // 2 - (selected_row - first_row))
            self.set_variable(['win/buf', 'first-row'],
                              minmax(0, center, self.line_count() - 4))

    def item_up(self):
        self.set_variable(['win/buf', 'selected-item'],
                          max(0, self.get_variable(['win/buf', 'selected-item']) - 1))
        self.recenter(out_of_bounds=True)

    def item_down(self):
        self.set_variable(['win/buf', 'selected-item'],
                          min(self.get_variable(['win/buf', 'selected-item']) + 1,
                              self.item_count() - 1))
        self.recenter(out_of_bounds=True)

    def selected_item(self):
        return self.items()[self.get_variable(['win/buf', 'selected-item'])]

    def line_count(self):
        return self.item_count() * self._item_height

    def hide_selection(self):
        return False

    def get_lines(self, window):
        hide_selection = self.hide_selection()
        first_row = window._state['first-row']
        selected_item = window._state['selected-item']
        item = None
        for row_index in range(first_row, min(self.line_count(),
                                              window.dimensions[0] + first_row)):
            item_index = row_index // self._item_height
            line_index = row_index % self._item_height
            if item is None or line_index == 0:
                item = self.render_item(window, self.items()[item_index], item_index)
            yield (
                {
                    'content': item[line_index],
                    'foreground': 'selection',
                    'background': 'selection'
                } if selected_item == item_index and not hide_selection else (
                    item[line_index]
                )
            ) if line_index < len(item) else ''

    def on_item_selected(self):
        pass

    def items(self):
        return []

    def item_count(self):
        return len(self.items())

    def render_item(self, window, item, index):
        return [item]


class LogBuffer(ListBuffer):
    @classmethod
    def name(cls, *args):
        return "Logger"

    def items(self):
        return core.Core().logger.messages

    def render_item(self, window, item, index):
        return item.split('\n', self._item_height)[:self._item_height]


class BufferListBuffer(ListBuffer):
    @classmethod
    def name(cls, *args):
        return "Buffers"

    def items(self):
        return core.Core().buffers

    def on_item_selected(self):
        core.Core().select_buffer(self.selected_item())

    def render_item(self, window, item, index):
        return [item.buffer_name()]


class TreeBuffer(ListBuffer):
    def __init__(self, *args):
        super(TreeBuffer, self).__init__(*args)
        self._flattened = []

    def get_children(self, item):
        return []

    def get_roots(self):
        return []

    def prepare(self):
        self._flattened = []
        node_stack = list(map(lambda n: {'item': n, 'depth': 0},
                              self.get_roots()))
        while node_stack:
            n = node_stack.pop(0)
            self._flattened.append(n)
            node_stack[0:0] = list(map(lambda child: {'item': child,
                                                      'depth': n['depth'] + 1},
                                       self.get_children(n['item'])))

    def items(self):
        return self._flattened

    def selected_item(self):
        return super(TreeBuffer, self).selected_item()['item']

    def render_item(self, window, item, index):
        tree_tab = core.Core().get_variable(['tree-tab'])
        rendered_node = self.render_node(window, item['item'], item['depth'],
                                         window.dimensions[1] - tree_tab * item['depth'])
        return [[self.render_tree_tab(window, line, tree_tab, item['depth'],
                                      line == rendered_node[0],
                                      line == rendered_node[-1]),
                 line]
                for line in rendered_node]

    def render_tree_tab(self, window, line, tree_tab, depth, first, last):
        return (' ' * depth * tree_tab)

    def render_node(self, window, item, depth, width):
        return [item]
