# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This module provides metaclass-based utilities.
"""

def combine_meta_classes(*args, **kwargs):
    """
    Combine multiple metaclasses into one.

    When a class hierarchy employs metaclasses the subclasses
    metaclass must always be a subclass of the parents metaclass.

    This function combines multiple metaclasses into one. Suppose
    you have two metaclasses Meta_A(type) and Meta_B(type) and the
    following class hierarchy:

    .. code-block:: python

       class Meta_A(type):
         pass

       class Meta_B(type):
         pass

       class A(object, metaclass=Meta_A):
         pass

       class B(object, metaclass=Meta_B):
         pass

    Class B will raise an error, as Meta_B must be a subclass of
    the parents subclass which is Meta_A. This can be solved by
    defining Meta_B as:

    .. code-block:: python

       class Meta_B(Meta_A):
         pass

    Since this is not always wanted, e.g., if you want to use
    Meta_B in file hierarchies where Meta_A is not used, you
    may use this function to create a combined metaclass:

    .. code-block::

       class B(object, metaclass=combine_meta_classes(Meta_B, Meta_A))
         pass
    """
    return type('Combined(%s)'
                % ', '.join(map(lambda c: c.__name__, args)),
                tuple(args),
                kwargs)


class Singleton(type):
    """
    Metaclass that implements the singleton pattern.

    Overrides Class Constructor, so that class is only
    created the first time it is called. After that, the
    previously created instance will be returned.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
