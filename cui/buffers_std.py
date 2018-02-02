# Copyright (c) 2017-2018 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from cui import api
from cui import buffers
from cui import core


@buffers.with_current_buffer
def display_help(buffer_object):
    """
    Display a help buffer
    """
    return api.buffer_visible(HelpBuffer, buffer_object.__class__, to_window=True)


class HelpBuffer(buffers.ScrollableBuffer):
    """
    Display documentation and shortcuts defined for a specific buffer.

    Use q to close the buffer again.
    """

    __keymap__ = {
        'q': buffers.close_buffer,
        '<up>': buffers.scroll_up,
        '<down>': buffers.scroll_down,
        '<pgup>': buffers.scroll_page_up,
        '<pgdown>': buffers.scroll_page_down,
    }

    @classmethod
    def name(cls, buffer_class, **kwargs):
        return "Help: %s" % buffer_class.__name__

    def __init__(self, buffer_class):
        super(HelpBuffer, self).__init__(buffer_class)
        self._buffer_class = buffer_class
        self._render_lines()

    def _render_lines(self):
        keymap = self._buffer_class.__keymap__.flattened()
        self._lines = []
        self._lines.extend([
            {'content': self._buffer_class.__name__, 'attributes': ['bold']},
            {'content': '=' * len(self._buffer_class.__name__), 'attributes': ['bold']},
        ])
        if self._buffer_class.__doc__:
            self._lines.extend((line.strip() for line in self._buffer_class.__doc__.split('\n')))
        else:
            self._lines.append('')
        for k, v in keymap.items():
            self._lines.append([{'content': '%s' % k, 'attributes': ['bold']},
                                ': %s' % (v.__name__)])
            self._lines.extend(('  %s' % line.strip()
                                for line in (v.__doc__ or '\n<No documentation>\n').split('\n')))

        self._lines.extend([
            '',
            {'content': 'Global Keys', 'attributes': ['bold']},
            {'content': '===========', 'attributes': ['bold']},
            ''
        ])
        for k, v in core.Core.__keymap__.flattened().items():
            self._lines.append([{'content': '%s' % k, 'attributes': ['bold']},
                                ': %s' % (v.__name__)])
            self._lines.extend(('  %s' % line.strip()
                                for line in (v.__doc__ or '\n<No documentation>\n').split('\n')))

    def line_count(self):
        return len(self._lines)

    def get_lines(self, window):
        yield from iter(self._lines[window._state['first-row']:])


@api.buffer_keys('C-x C-b', 'list_buffers')
class BufferListBuffer(buffers.ListBuffer):
    @classmethod
    def name(cls, *args, **kwargs):
        return "Buffers"

    def items(self):
        return core.Core().buffers

    def on_item_selected(self):
        core.Core().select_buffer(self.selected_item())

    def render_item(self, window, item, index):
        return [item.buffer_name()]


@api.buffer_keys('C-x C-e', 'show_eval_python')
class EvalBuffer(buffers.ConsoleBuffer):
    """
    Evaluate Python expressions in the context of cui.
    """
    @classmethod
    def name(cls, **kwargs):
        return 'cui-eval'

    def on_send_current_buffer(self, b):
        result = api.eval_python(b)
        if result is not None:
            self.extend(str(result))


@api.buffer_keys('C-x C-l', 'show_log')
class LogBuffer(buffers.ListBuffer):
    """
    Displays messages posted via cui.message or cui.exception.

    The maximum can be set via variable message-limit.
    """

    @classmethod
    def name(cls, **kwargs):
        return "Logger"

    def items(self):
        return core.Core().logger.messages

    def render_item(self, window, item, index):
        return item.split('\n', self._item_height)[:self._item_height]


class CompletionsBuffer(buffers.ListBuffer):
    """
    Displays the available completions
    """

    @classmethod
    def name(cls, runloop_id, **kwargs):
        return "Completions <%s>" % runloop_id

    def __init__(self, runloop_id):
        super(CompletionsBuffer, self).__init__(runloop_id)
        self._id = runloop_id
        self._completions = []

    def set_completions(self, completions):
        self._completions = completions

    def items(self):
        return self._completions


class StaticBuffer(buffers.ListBuffer):
    """
    Display content serialized as JSON
    """

    @classmethod
    def name(cls, json_file, **kwargs):
        return "JSON: %s" % json_file

    def __init__(self, json_file):
        super(StaticBuffer, self).__init__(json_file)
        with open(json_file, 'r') as json_fp:
            self.rows = list(map(lambda r: [r],
                                 json.load(json_fp)))

    def items(self):
        return self.rows
