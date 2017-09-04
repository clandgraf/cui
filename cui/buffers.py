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

    def buffer_name(self):
        return self.name(*self.args)

    def line_count(self):
        pass

    def get_lines(self, first_row, num_rows, num_cols):
        pass

class ListBuffer(Buffer):
    __keymap__ = {
        #'<up>':   lambda b: b.key_up(),
        #'<down>': lambda b: b.key_down(),
        'C-j':    lambda b: b.on_item_selected()
    }

    def __init__(self, *args):
        super(ListBuffer, self).__init__(*args)
        self.item_height = 1
        self.selected_item = 0

    def _prepare_item(self, index, num_cols):
        soft_tabs = ' ' * core.Core().get_variable(['tab-stop'])
        # XXX python3
        return list(map(lambda l: l.replace('\t', soft_tabs)[:num_cols],
                        self.render_item(index)
                            .split('\n', self.item_height)[:self.item_height]))

    def line_count(self):
        return self.item_count() * self.item_height

    def get_lines(self, first_row, num_rows, num_cols):
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
