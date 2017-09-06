import curses

from cui.util import get_base_classes, deep_get, deep_put, minmax
from cui.keymap import WithKeymap
from cui import core


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

    def line_count(self):
        pass

    def get_lines(self, num_rows, num_cols):
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
        self.item_height = 1
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
        selected_row = self.get_variable(['win/buf', 'selected-item']) * self.item_height
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

    def _prepare_item(self, index, num_cols):
        return self.render_item(index).split('\n', self.item_height)[:self.item_height]

    def line_count(self):
        return self.item_count() * self.item_height

    def get_lines(self, window, num_rows, num_cols):
        first_row = window._state['first-row']
        selected_item = window._state['selected-item']
        item = None
        for row_index in range(first_row, min(self.line_count(),
                                              num_rows + first_row)):
            item_index = row_index // self.item_height
            line_index = row_index % self.item_height
            if item is None or line_index == 0:
                item = self._prepare_item(item_index, num_cols)
            yield (
                {
                    'content': item[line_index],
                    'foreground': 'selection',
                    'background': 'selection'
                } if selected_item == item_index else item[line_index]
            ) if line_index < len(item) else ''

    def on_item_selected(self):
        pass

    def item_count(self):
        pass

    def render_item(self, index):
        pass


class LogBuffer(ListBuffer):
    @classmethod
    def name(cls, *args):
        return "Logger"

    def item_count(self):
        return len(core.Core().logger.messages)

    def render_item(self, index):
        return core.Core().logger.messages[index]
