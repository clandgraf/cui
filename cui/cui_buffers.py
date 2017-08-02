import curses

from cui.cui_constants import COLOR_DEFAULT, COLOR_HIGHLIGHTED

class Buffer(object):
    __keymap__ = {}

    def __init__(self, core):
        self.core = core
        self.keymap = {}
        self._init_keymap()

    def _init_keymap(self):
        class_ = self.__class__
        while class_:
            if hasattr(class_,'__keymap__'):
                self.keymap.update(class_.__keymap__)
            class_ = class_.__base__

    def handle_input(self, c):
        key_fn = self.keymap.get(c)
        if key_fn:
            key_fn(self)

    def name(self):
        return '*empty*'

    def fill_row(self, screen, row, col, string, sep=' ', attr=None):
        l = (screen.getmaxyx()[1] - len(string)) - col - 1
        if attr:
            screen.addstr(row, col, '%s%s' % (string, sep * l), attr)
        else:
            screen.addstr(row, col, '%s%s' % (string, sep * l))

    def render_mode_line(self, screen):
        max_y, max_x = screen.getmaxyx()
        fixed = '--- [ %s ] ' % self.name()
        self.fill_row(screen, max_y - 1, 0, fixed, sep='-')

    def render_content(self, screen):
        pass

    def render(self, screen):
        self.render_content(screen)
        self.render_mode_line(screen)


class ListBuffer(Buffer):
    __keymap__ = {
        '<up>':   lambda b: b.key_up(),
        '<down>': lambda b: b.key_down(),
        'C-j':    lambda b: b.on_item_selected()
    }

    def __init__(self, core):
        super(ListBuffer, self).__init__(core)
        self.selected_item = 0

    def key_down(self):
        self.selected_item = min(self.item_count() - 1, self.selected_item + 1)

    def key_up(self):
        self.selected_item = max(0, self.selected_item - 1)

    def render_content(self, screen):
        for index in range(0, self.item_count()):
            item = self.render_item(screen, index)
            self.fill_row(screen, index, 0, item,
                          attr=curses.color_pair(COLOR_HIGHLIGHTED \
                                                 if index == self.selected_item else \
                                                 COLOR_DEFAULT))

    def on_item_selected(self):
        pass

    def item_count(self):
        pass

    def render_item(self, screen, index):
        pass


class LogBuffer(ListBuffer):
    def name(self):
        return "Logger"

    def item_count(self):
        return len(self.core.logger.messages)

    def render_item(self, screen, index):
        return self.core.logger.messages[index]
