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

__all__ = ['Format', 'STRING', 'DATETIME', 'TIME', 'TIMEDELTA', 'DATE', 'FLOAT', 'DECIMAL', 'INTEGER', 'BOOLEAN', 'BINARY', 'NOMINAL', 'ALL_FORMATS', 'lookup_format', ]

from .util import as_tuple
from .errors import FormatError

from datetime import date, time, datetime, timedelta
from decimal import Decimal

_loaded = False

class Format(object):
    def __new__(cls, key, types = None, instances = None, exclude = None, convert = None):
        """Returns an object representing a standard format in :mod:`Cardsharp`.  *key* is the
        identifying string.  After initialization,
        this method is identical to :func:`lookup_format`, except it requires the key
        be a string.

        >>> Format('integer')
        Format('integer')
        >>> Format(int)
        Traceback (most recent call last):
            ...
        TypeError: Cannot create a format with a <type 'int'> key
        """
        if not isinstance(key, basestring):
            raise TypeError('Cannot create a format with a %r key' % key)

        if _loaded:
            if types is not None or instances is not None:
                raise ValueError('Attempt to define format "%s" after initialization' % key)

            return lookup_format(key)

        self = object.__new__(cls)
        self._key = unicode(key).lower()
        self._hash = hash(key) * 23
        self._types = as_tuple(types, if_none = ())
        self._type = self._types[0] if types else None
        self._exclude = as_tuple(exclude, if_none = None)
        if instances:
            self._instances = as_tuple(instances)
        else:
            self._instances = self._types
        self._convert = convert
        return self

    @property
    def key(self):
        return self._key

    @property
    def types(self):
        return self._types

    @property
    def type(self):
        return self._type

    def __getnewargs__(self):
        return (self._key, )

    def __getstate__(self):
        return self._key

    def __setstate__(self, state):
        f = lookup_format(state)
        self._key = f._key
        self._hash = f._hash
        self._types = f._types
        self._type = f._type
        self._exclude = f._exclude
        self._instances = f._instances
        self._convert = f._convert

    def __eq__(self, x):
        return self is x or self._key == getattr(x, 'key', None)

    def __hash__(self):
        return self._hash

    def __str__(self):
        return self._key

    def __repr__(self):
        return 'Format(%r)' % str(self._key)

    def validate(self, v, var_name = None, as_type = False):
        """Ensures the value can be stored in the given format without potentially losing
        information.  The value returned will be converted to the appropriate type, if
        necessary.

        .. note::

            This method enforces some type restrictions which Python does not.  For example,
            this doesn't work:

            >>> INTEGER.validate(True)
            Traceback (most recent call last):
                ...
            FormatError: Cannot store True in Format('integer') on None

            Specifically, you cannot convert :type:datetime.date objects into :type:datetime.datetime objects,
            and you cannot convert :type:bool objects into other types of numbers.  These conversions need to
            be handled explicitly by the programmer.  See :mod:cardsharp.convert for additional information.

        >>> INTEGER.validate(1)
        1
        >>> from datetime import datetime, date
        >>> DATETIME.validate(datetime(2000, 1, 1))
        datetime.datetime(2000, 1, 1, 0, 0)
        >>> DATETIME.validate(date(2000, 1, 1))
        Traceback (most recent call last):
            ...
        FormatError: Cannot store datetime.date(2000, 1, 1) in Format('datetime') on None

        This method can also accept a type object by passing a boolean to the *as_type* parameter.  In this case
        it verifies the type can be stored in this format.  It will either raise a
        :exc:`FormatError`, or return `None`.

        >>> STRING.validate(unicode, as_type = True)
        >>> BOOLEAN.validate(int, as_type = True)
        Traceback (most recent call last):
            ...
        FormatError: Cannot store <type 'int'> in Format('boolean') on None
        """
        if v is None:
            return None

        if as_type:
            if (self._exclude is not None and issubclass(v, self._exclude)) or not issubclass(v, self._instances):
                raise FormatError('Cannot store %r in %r on %s' % (v, self, var_name))
            
            return None
        
        if (self._exclude is not None and isinstance(v, self._exclude)) or not isinstance(v, self._instances):
            raise FormatError('Cannot store %r in %r on %s' % (v, self, var_name))

        if self._convert is None:
            return v
        else:
            return self._convert(v)

STRING = Format('string', types = (unicode, str), instances = basestring, convert = unicode)
DATETIME = Format('datetime', types = datetime)
TIME = Format('time', types = time)
TIMEDELTA = Format('timedelta', types = timedelta)
DATE = Format('date', types = date, exclude = datetime)
FLOAT = Format('float', types = float, instances = (float, int, long, Decimal), convert = float, exclude = bool)
DECIMAL = Format('decimal', types = Decimal, instances = (int, long, Decimal), convert = Decimal, exclude = bool)
INTEGER = Format('integer', types = (int, long), exclude = bool)
BOOLEAN = Format('boolean', types = bool)
BINARY = Format('binary', types = str)
NOMINAL = Format('nominal', types = (unicode, str, int), convert = unicode)

ALL_FORMATS = (BINARY, STRING, DATETIME, DATE, TIME, TIMEDELTA, FLOAT, DECIMAL, INTEGER, BOOLEAN, NOMINAL)
_formats = dict()
for f in ALL_FORMATS:
    _formats[f] = f
    _formats[f.key] = f
    _formats.update([(t, f) for t in f.types])

_loaded = True

def lookup_format(f):
    """Locates an appropriate format.

    *f* can be a string or a type.  If *f* is a string, it is converted to lowercase and the
    return value is the :class:`Format` instance with the matching :attr:`key`.
    If *f* is a type, the return value is a :class:`Format` capable of storing that type.
    A :exc:`ValueError` is raised if no matching :class:`Format` was found.

    >>> lookup_format('integer')
    Format('integer')
    >>> lookup_format(int)
    Format('integer')
    >>> lookup_format(12)
    Traceback (most recent call last):
        ...
    KeyError: u'Unable to find matching format for 12'
    """

    try:
        if isinstance(f, basestring):
            f = f.lower()

        return _formats[f]
    except KeyError:
        raise KeyError('Unable to find matching format for %r' % f)