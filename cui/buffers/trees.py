# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui
import functools

from .base import ListBuffer
from .util import with_current_buffer
from cui import symbols
from cui.meta import combine_meta_classes
from cui.util import find_value


@with_current_buffer
def expand_node(b):
    """
    Expand the currently selected node.
    """
    item = b.selected_item()
    if not b.is_expanded(item) and b.has_children(item):
        b.set_expanded(item, True)


@with_current_buffer
def collapse_node(b):
    """
    Collapse the currently selected node.
    """
    item = b.selected_item()
    if b.is_expanded(item) and b.has_children(item):
        b.set_expanded(item, False)


class TreeBuffer(ListBuffer):
    __keymap__ = {
        '<left>': collapse_node,
        '<right>': expand_node
    }

    def __init__(self, *args, show_handles=False):
        super(TreeBuffer, self).__init__(*args)
        self._flattened = []
        self._show_handles = show_handles

    def get_children(self, item):
        return []

    def is_expanded(self, item):
        False

    def set_expanded(self, item, expanded):
        pass

    def has_children(self, item):
        False

    def fetch_children(self, item):
        pass

    def _fetch_children(self, item):
        self.fetch_children(item)
        return self.get_children(item)

    def get_roots(self):
        return []

    def on_pre_render(self):
        self._flattened = []
        def _create_internal_nodes(nodes, parent=None):
            return list(map(lambda n: {'item': n,
                                       'first': n == nodes[0],
                                       'last': n == nodes[-1],
                                       'parent': parent,
                                       'depth': 0 if parent is None else parent['depth'] + 1},
                            nodes))

        roots = self.get_roots()
        node_stack = _create_internal_nodes(roots)
        while node_stack:
            n = node_stack.pop(0)
            self._flattened.append(n)
            if self.has_children(n['item']) and self.is_expanded(n['item']):
                node_stack[0:0] = _create_internal_nodes(self.get_children(n['item']) or \
                                                         self._fetch_children(n['item']),
                                                         n)

    def items(self):
        return self._flattened

    def selected_node(self):
        return super(TreeBuffer, self).selected_item()

    def selected_item(self):
        return self.selected_node()['item']

    def render_item(self, window, item, index):
        tree_tab = cui.get_variable(['tree-tab'])
        rendered_node = self.render_node(window, item['item'], item['depth'],
                                         window.dimensions[1] - tree_tab * item['depth'])
        return [[self.render_tree_tab(window, item, line, tree_tab, line == rendered_node[0]),
                 line]
                for line in rendered_node]

    def render_tree_tab(self, window, item, line, tree_tab, first_line):
        lst = []

        if item['depth'] != 0:
            lst.append((symbols.SYM_LLCORNER if item['last'] else symbols.SYM_LTEE) \
                       if first_line else \
                       (' ' if item['last'] else symbols.SYM_VLINE))
        if self._show_handles:
            lst.append((symbols.SYM_DARROW if self.is_expanded(item['item']) else symbols.SYM_RARROW) \
                       if first_line and self.has_children(item['item']) else \
                       ' ')
        lst.append(' ')

        while item['depth'] > 1:
            item = item['parent']
            lst = (['  '] if item['last'] else [symbols.SYM_VLINE, ' ']) + \
                  ([' '] if self._show_handles else []) + \
                  lst
        if item['depth'] == 1:
            lst = (['  '] if self._show_handles else [' ']) + lst

        return lst

    def render_node(self, window, item, depth, width):
        return [item]


def with_selected_item(fn):
    @functools.wraps(fn)
    @with_current_buffer
    def _fn(b, *args, **kwargs):
        return fn(b.selected_item(), *args, **kwargs)
    return _fn


################################
# TreeBuffer with NodeRenderers
################################


class DefaultTreeBufferMeta(type):
    def __init__(cls, name, bases, dct):
        cls.__node_handlers__ = []
        for parent in filter(lambda base: isinstance(base, DefaultTreeBufferMeta), bases):
            cls.__node_handlers__.extend(parent.__node_handlers__)
        super(DefaultTreeBufferMeta, cls).__init__(name, bases, dct)


def node_handlers(*nrs):
    def _node_handlers(cls):
        cls.__node_handlers__.extend(nrs)
        return cls
    return _node_handlers


def NodeHandler(is_expanded_=False, has_children_=False):
    class _NodeHandler(object):
        IS_EXPANDED = is_expanded_
        HAS_CHILDREN = has_children_
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def matches(self, item):
            return False

        def is_expanded(self, item):
            return _NodeHandler.IS_EXPANDED

        def set_expanded(self, item, expanded):
            pass

        def has_children(self, item):
            return _NodeHandler.HAS_CHILDREN

        def get_children(self, item):
            return []

        def fetch_children(self, item):
            pass

        def render(self, window, item, depth, width):
            return [item]
    return _NodeHandler


class DefaultTreeBuffer(TreeBuffer,
                        metaclass=combine_meta_classes(DefaultTreeBufferMeta,
                                                       TreeBuffer.__class__)):
    def __init__(self, *args, **kwargs):
        super(DefaultTreeBuffer, self).__init__(*args, **kwargs)
        self._node_handlers = [handler(*args, **kwargs)
                               for handler in self.__node_handlers__]

    def on_pre_render(self):
        # Invalidate handler-cache
        self._node_handler_cache = {}
        super(DefaultTreeBuffer, self).on_pre_render()

    def _get_handler(self, item):
        item_id = id(item)
        if item_id in self._node_handler_cache:
            return self._node_handler_cache[item_id]

        handler = find_value(self._node_handlers,
                             lambda handler, _: handler.matches(item))
        if handler is None:
            raise ValueError('No NodeHandler found for %s' % repr(item))
        self._node_handler_cache[item_id] = handler

        return handler

    def get_children(self, item):
        return self._get_handler(item).get_children(item)

    def is_expanded(self, item):
        return self._get_handler(item).is_expanded(item)

    def set_expanded(self, item, expanded):
        self._get_handler(item).set_expanded(item, expanded)

    def has_children(self, item):
        return self._get_handler(item).has_children(item)

    def fetch_children(self, item):
        return self._get_handler(item).fetch_children(item)

    def render_node(self, window, item, depth, width):
        return self._get_handler(item).render(window, item, depth, width)


def with_node_handler(fn):
    @functools.wraps(fn)
    @with_current_buffer
    def _fn(b, *args, **kwargs):
        item = b.selected_item()
        handler = b._get_handler(item)
        return fn(handler, item, *args, **kwargs)
    return _fn


def invoke_node_handler(fn_name):
    @with_node_handler
    def fn(handler, item, *args, **kwargs):
        handler_fn = getattr(handler, fn_name, None)
        if handler_fn:
            return handler_fn(item, *args, **kwargs)
    return fn
