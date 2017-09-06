import curses

from cui.util import get_base_classes, deep_get, deep_put
from cui.keymap import WithKeymap
from cui import core


class Buffer(WithKeymap):
    __keymap__ = {}

    @classmethod
    def name(cls, *args):
        return None

    def __init__(self, *args):
        super(Buffer, self).__init__()
        self.args = args
        self._state = {'win/buf': {}}

    def def_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=True)

    def set_variable(self, path, value=None):
        deep_put(self._state, path, value, create_path=False)
        selected_window = core.Core().selected_window()
        if path[0] == 'win/buf' and self == selected_window.buffer():
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
        'C-<up>':   lambda: core.Core().current_buffer().scroll_up(),
        'C-<down>': lambda: core.Core().current_buffer().scroll_down(),
        'C-j':    lambda: core.Core().current_buffer().on_item_selected()
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

    def item_up(self):
        pass

    def item_down(self):
        pass

    def _prepare_item(self, index, num_cols):
        soft_tabs = ' ' * core.Core().get_variable(['tab-stop'])
        # XXX python3
        return list(map(lambda l: l.replace('\t', soft_tabs)[:num_cols],
                        self.render_item(index)
                            .split('\n', self.item_height)[:self.item_height]))

    def line_count(self):
        return self.item_count() * self.item_height

    def get_lines(self, window, num_rows, num_cols):
        first_row = window._state['first-row']
        item = None
        for row_index in range(first_row, min(self.line_count(),
                                              num_rows + first_row)):
            item_index = row_index // self.item_height
            line_index = row_index % self.item_height
            if item is None or line_index == 0:
                item = self._prepare_item(item_index, num_cols)
            yield item[line_index] if line_index < len(item) else ''

    # def key_down(self):
    #     self.selected_item = min(self.item_count() - 1, self.selected_item + 1)

    #     max_y, max_x = screen.getmaxyx()
    #     max_lines = max_y - 1
    #     if self.selected_item * self.item_height < self.first_line:
    #         self.first_line = max(0, self.first_line - max_lines / 2)

    # def key_up(self):
    #     self.selected_item = max(0, self.selected_item - 1)

    #     max_y, max_x = screen.getmaxyx()
    #     max_lines = max_y - 1
    #     if self.selected_item * self.item_height > self.first_line + max_lines - 1:
    #         self.first_line = min(self.item_count() * self.item_height - max_lines,
    #                               self.first_line + self.max_lines / 2)

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
