# Copyright (c) 2010 NORC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import division, unicode_literals, absolute_import

__all__ = ['NOT_DEFINED', 'as_tuple', 'as_iter', 'memoize', 'SafeIterationSet', 'Counter']

from functools import wraps
from threading import Lock
from .errors import *
from itertools import izip_longest

class NotDefined(object):
    """
    The :cls:`NotDefined` class creates an object suitable for use in parameter lists
    to distinguish between arguments which were left out.  This is useful if you need 
    to tell the difference between `None` and a missing parameter.
   
    It implements __nonzero__, so it compares as `False`.
    
    An instance of this class is available through the `NOT_DEFINED` constant in this module.
    
    >>> def func(arg = NOT_DEFINED):
    ...     return arg or 'Not Defined'
    >>> func(u'Hello')
    u'Hello'
    >>> func()
    u'Not Defined'
    """
    
    def __nonzero__(self):
        return False
    
NOT_DEFINED = NotDefined()

class SafeIterationSet(set):
    def __init__(self, *args, **kw):
        self._lock = Lock()
        set.__init__(self, *args, **kw)
        
    def add(self, *args, **kw):
        with self._lock:
            set.add(self, *args, **kw)
            
    def remove(self, *args, **kw):
        with self._lock:
            set.remove(self, *args, **kw)
    
    def discard(self, *args, **kw):
        with self._lock:
            set.discard(self, *args, **kw)
            
    def __iter__(self):
        with self._lock:
            s = set(set.__iter__(self))
        
        return iter(s)

class Counter(dict):
    def __missing__(self, key):
        return 0
    
def _skip_none_iter(func):
    @wraps(func)
    def _exec(*args):
        l = args[0] if len(args) == 1 else args
        l = list(x for x in l if x is not None)
        return None if len(l) == 0 else func(l)
    return _exec

sum_ = _skip_none_iter(sum)
min_ = _skip_none_iter(min)
max_ = _skip_none_iter(max)
    
def fill_variable_defaults(variables, values):
    """Returns a list of values.  If values is shorter than variables, fills in missing values with the defaults.
    If variables is shorter than values, throws a CardsharpError."""
    
    converted_values = []
    for variable, value in izip_longest(variables, values, fillvalue = NOT_DEFINED):
        if value is NOT_DEFINED:
            value = variable.default
        elif variable is NOT_DEFINED:
            raise CardsharpError('More values supplied than variables: %s' % values)
        
        converted_values.append(variable.validate(value, None))
    
    return converted_values

def as_tuple(o, if_none = (), skip_nones = False):
    """Converts *o* into a tuple.  If *o* is a string, this returns `(o, )`.  If *o* is an iterable (but not
    a string), this returns the iterable converted to a tuple.  If *o* is `None`, this function returns *if_none*
    (by default, `()`).  If *skip_nones* is `True` this will skip any `None` values in the
    iterable when constructing the tuple.  This method attempts to avoid creating a new tuple.

    >>> as_tuple(1)
    (1,)
    >>> as_tuple([1])
    (1,)
    >>> as_tuple(u'foo')
    (u'foo',)
    >>> as_tuple(None)
    ()
    >>> as_tuple(None, if_none = u'MISSING')
    u'MISSING'
    >>> as_tuple([1, None, 2])
    (1, None, 2)
    >>> as_tuple([1, None, 2], skip_nones = True)
    (1, 2)
    >>> x = tuple([1, 2, 3])
    >>> x is as_tuple(x)
    True
    >>> x = tuple([1, None, 3])
    >>> x is as_tuple(x, skip_nones = False)
    True
    >>> x is as_tuple(x, skip_nones = True)
    False
    """
    if o is None:
        return if_none

    if isinstance(o, tuple) and not (skip_nones and None in o):
        return o
    else:
        return tuple(as_iter(o, skip_nones = skip_nones))

def memoize(func):
    """This function integrates memoization, an optimization technique, into cardsharp. 
    Memoize wraps a function with a single argument.  When it is called the first time, the result
    is cached with the argument as the key.  If it is called in the future with the same
    argument, it returns the cached value.
    
    >>> from random import random
    >>> func = lambda x: random()
    >>> func(1) == func(1)
    False
    >>> func = memoize(func)
    >>> func(1) == func(1)
    True
    """
    memo = dict()
    
    @wraps(func)
    def _func(arg):
        if arg in memo:
            return memo[arg]
        
        memo[arg] = value = func(arg)
        return value
    
    return _func
    
def as_iter(o, skip_nones = False):
    """Converts *o* into a iterator object.  There are two major differences between this function
    and the built-in *iter* function.  First, this preserves strings, rather than iterating over them.
    
    >>> a = iter('abc')
    >>> a.next()
    u'a'
    >>> a = as_iter('abc')
    >>> a.next()
    u'abc'
    
    Second (and relatedly), this will accept a single value as a valid argument, returning it in the iterator.
    
    >>> a = iter(12)
    Traceback (most recent call last):
        ...
    TypeError: 'int' object is not iterable
    >>> a = as_iter(12)
    >>> a.next()
    12
    
    You can call as_iter with *skip_nones* set to True (default False) to skip any *None* values in the iteration stream.
    
    >>> a = as_iter([1, None, 2])
    >>> ' '.join(str(x) for x in a)
    u'1 None 2'
    
    >>> a = as_iter([1, None, 2], skip_nones = True)
    >>> ' '.join(str(x) for x in a)
    u'1 2'
    
    """
    if o is None:
        if not skip_nones:
            yield None
    elif isinstance(o, basestring):
        yield o
    else:
        try:
            for i in o:
                if skip_nones and i is None:
                    continue
                else:
                    yield i
        except TypeError:
            yield o