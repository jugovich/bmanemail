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

from .errors import *
from .util import memoize
from .format import ALL_FORMATS
from .format import lookup_format as _lf
from datetime import datetime
import decimal
 
_DEFAULT_CONTEXT = decimal.Context(prec = 28, rounding = decimal.ROUND_HALF_EVEN, Emin = -999999999, Emax = 999999999,
        capitals = 1, flags = [], traps = [decimal.Overflow, decimal.DivisionByZero, decimal.InvalidOperation])

#need to change in future to read from config, had it working with importing cardsharp but that seems
#to heavy
debug = True

def as_str(v):
    """Converts *v* to a unicode string. If *v* is *None*, returns *None* instead. 
    
    >>> from datetime import datetime 
    >>> as_str(datetime(2007, 12, 5))
    u'2007-12-05 00:00:00'
    >>> as_str(None) is None
    True
    """
    
    if v is None:
        return None
    
    return unicode(v)

class ContextDict(dict):
    """Creates a dictionary which defines the const:DECIMAL_CONTEXTS to use when calling :func:round
    
    >>> D = ContextDict()
    >>> context, model = D[(2, decimal.ROUND_UP)]
    >>> context.rounding
    'ROUND_UP'
    >>> model
    Decimal('0.01')
    
    >>> context, model = D[(4, decimal.ROUND_DOWN)]
    >>> context.rounding
    'ROUND_DOWN'
    >>> model
    Decimal('0.0001')
    """
    
    def __missing__(self, key):
        decimals, rounding = key
        c = _DEFAULT_CONTEXT.copy()
        if rounding != None:
            c.rounding = rounding

        value = (c, decimal.Decimal(10) ** (-decimals))
        self[key] = value
        return value

DECIMAL_CONTEXTS = ContextDict()

def str_to_binary(s, encoding):
    #TODO: make xxx link
    """Encodes a string to binary using given encoding. Returns a binary (bytes string) Object. 
    If *s* is *None* returns *None* instead. 
        
    >>> str_to_binary('out_str', 'utf_8')
    'out_str'
    >>> str_to_binary('out_str', 'utf_16')
    '\\xff\\xfeo\\x00u\\x00t\\x00_\\x00s\\x00t\\x00r\\x00'
    >>> str_to_binary(None, 'utf_8') is None
    True
    """
    
    if s is None:
        return None
        
    return s.encode(encoding)

def binary_to_str(s, encoding):
    """Decodes from a binary to a string using given encoding. Returns a string (unicode Object).
    If *s* is *None* returns *None* instead.
    
    >>> binary_to_str('out_str', 'latin_1')
    u'out_str'
    >>> binary_to_str('\xff\xfeo\x00u\x00t\x00_\x00s\x00t\x00r\x00', 'utf_16') #doctest: +SKIP
    u'out_str'
    >>> binary_to_str(None, 'utf_8') is None
    True
    """
    
    if s is None:
        return None
    
    return s.decode(encoding)

def binary_to_binary(s, orig_encoding, new_encoding):
    """Converts from original binary encoding to new binary encoding. If *s* is *None* returns *None* instead.
    
    >>> binary_to_binary('out_str', 'latin_1', 'utf_16')
    '\\xff\\xfeo\\x00u\\x00t\\x00_\\x00s\\x00t\\x00r\\x00'
    >>> binary_to_binary(None, 'utf_8', 'utf_8') is None
    True
    """
    if s is None:
        return None
    
    return s.decode(orig_encoding).encode(new_encoding)

def round(v, decimals, rounding = decimal.ROUND_HALF_EVEN):
    """Round to the nearest decimals places. If *v* is *None* returns *None* instead.
    
    *v* can be a float, str, or Decimal.
    *decimals* is an int 
    
    >>> from decimal import *
    >>> round(1.235, 1)
    Decimal('1.2')
    >>> round('1.235', 2)
    Decimal('1.24')
    >>> round(None,None) is None
    True
    
    If *decimals* > decimal place of *v* then round and add zeros for any missing decimal places.
    
    >>> round(Decimal('1.2'), 5)
    Decimal('1.20000')
    >>> round('1.229', 5)
    Decimal('1.22900')
    
    By default the rounding convention is set to ROUND_HALF_EVEN. If you supply a *rounding* argument 
    then *v* is rounded using supplied convention. 
    
    >>> round(Decimal('1.239'), 2, 'ROUND_DOWN')
    Decimal('1.23')
    """
    
    if v is None:
        return None
    
    c, model = DECIMAL_CONTEXTS[(decimals, rounding)]
    if isinstance(v, decimal.Decimal):
        d = v
    else:
        d = c.create_decimal(str(v))
    return d.quantize(model, context = c)

def round_int(v, rounding = decimal.ROUND_HALF_EVEN):
    """Round to the nearest integer. *v* can be a float, str, or Decimal. If *v* is None returns *None* instead.
    
    >>> round_int(1.235)
    1
    >>> round_int('1.5')
    2
    >>> round_int(None) is None
    True
    
    By default *rounding* is set to :const:ROUND_HALF_EVEN. Pass a rounding argument to have *v* 
    rounded using the passed rounding convention.
    """
    if v is None:
        return None
    
    return int(round(v, decimals = 0, rounding = rounding))

def datetime_to_date(d, format_str=None):
    """Converts a datetime Object to a date Object. If *d* is *None* returns *None* instead.
    
    >>> from datetime import datetime
    >>> d = datetime(2007, 12, 15, 12, 10, 10) 
    >>> datetime_to_date(d)
    datetime.date(2007, 12, 15)
    >>> datetime_to_date(None) is None
    True
    """
    if d is None:
        return None
    
    return d.date()

def datetime_to_time(d, format_str = None):
    """Converts a datetime Object to a time Object. If *d* is *None* returns *None* instead.
    
    >>> from datetime import datetime
    >>> d = datetime(2007, 12, 5, 12, 10, 10) 
    >>> datetime_to_time(d)
    datetime.time(12, 10, 10)
    >>> datetime_to_date(None) is None
    True
    """
    if d is None:
        return None
    
    return d.time()

def str_to_date(d, format_str = None):
    """Converts a str Object to a date Object explicitly following the corresponding format_str. 
    If *d* is *None* returns *None* instead.
    
    >>> d = '05-10-1900'  
    >>> str_to_date(d, '%m-%d-%Y')  
    datetime.date(1900, 5, 10)
    >>> d = '10051900'  
    >>> str_to_date(d, '%m%d%Y')
    datetime.date(1900, 10, 5)
    >>> str_to_date(None) is None
    True
    """
    if d is None:
        return None

    d = datetime.strptime(d, format_str)
    return d.date()

def str_to_datetime(d, format_str):
    """Converts a str Object to a datetime Object explicitly following the corresponding format_str. 
    If *d* is *None* returns *None* instead.
    
    >>> d = '05-10-1900 12:00:01' 
    >>> str_to_datetime(d, '%m-%d-%Y %H:%M:%S')
    datetime.datetime(1900, 5, 10, 12, 0, 1)
    >>> d = '10051900 120001'
    >>> str_to_datetime(d, '%m%d%Y %H%M%S')
    datetime.datetime(1900, 10, 5, 12, 0, 1)
    >>> str_to_datetime(None, None) is None
    True
    """
    if d is None:
        return None
    
    return datetime.strptime(d, format_str)

def str_to_time(d, format_str):
    """Converts a str Object to a time Object explicitly following the corresponding format_str. 
    If *d* is *None* returns *None* instead.
    
    >>> d = '12:00:01' 
    >>> str_to_time(d, '%H:%M:%S')
    datetime.time(12, 0, 1)
    >>> d = '120001'
    >>> str_to_time(d, '%H%M%S')
    datetime.time(12, 0, 1)
    >>> str_to_time(None, None) is None
    True
    """
    if d is None:
        return None
    
    d = datetime.strptime(d, format_str)
    return d.time()

def str_to_float(s, format_str=None):
    """Converts a string to a float. 
    If *s* is *None* returns *None* instead.
    
    >>> str_to_float('1')
    1.0
    >>> str_to_float('1.1')
    1.1000000000000001
    """
    if s is None:
        return None
    else:
        return float(s)
    
def str_to_boolean(s):
    """Converts a string to a boolean. 
    
    Convert map:
    -------------------
    | 1     | *True*  |
    -------------------
    | true  | *True*  |
    -------------------
    | 0     | *False* |
    -------------------
    | false | *False* |
    -------------------
    
    If *s* is *None* returns *None* instead.
    
    >>> str_to_boolean('1')
    True
    >>> str_to_boolean(0)
    False
    >>> str_to_boolean('  FAlse  ')
    False
    >>> str_to_boolean('3')
    Traceback (most recent call last):
        ...
    FormatError: Invalid input data, 3: must be true, false, 1 or 0
    """
    if s is None:
        return None
    else:
        if str(s) == '1' or str(s).strip().lower() == 'true':
            return True
        elif str(s) == '0' or str(s).strip().lower() == 'false':
            return False
        else:
            raise FormatError('Invalid input data, %s: must be true, false, 1 or 0' % s) 

def nominal(v):
    return None if v is None else str(v)
        
_converters = dict()
for source in ALL_FORMATS:
    _converters[(source.key, 'string')] = as_str

del _converters[('string', 'string')]

_converters[('datetime', 'date')] = datetime_to_date
_converters[('datetime', 'time')] = datetime_to_time
_converters[('integer', 'decimal')] = memoize(round_int)
_converters[('integer', 'boolean')] = str_to_boolean
_converters[('float', 'decimal')] = round
_converters[('float', 'integer')] = memoize(round_int)
_converters[('string', 'integer')] = memoize(round_int)
_converters[('string', 'datetime')] = str_to_datetime
_converters[('string', 'date')] = str_to_date
_converters[('string', 'time')] = str_to_time
_converters[('string', 'decimal')] = round
_converters[('string', 'boolean')] = str_to_boolean
_converters[('string', 'float')] = memoize(str_to_float)
_converters[('string', 'binary')] = str_to_binary
_converters[('binary', 'string')] = binary_to_str
_converters[('binary', 'binary')] = binary_to_binary
_converters[('decimal', 'decimal')] = round
_converters[('integer', 'nominal')] = nominal
_converters[('string', 'nominal')] = nominal
_converters[('float', 'nominal')] = nominal
_converters[('decimal', 'nominal')] = nominal
_converters[('binary', 'nominal')] = nominal

def get_format_converter(source, dest):
    """This function locates a conversion function to convert format *source* into format *dest*.
    
    >>> c = get_format_converter('string', 'integer')
    >>> c('12')
    12
    >>> c = get_format_converter('string', 'date')
    >>> c('1/1/2000', '%m/%d/%Y')
    datetime.date(2000, 1, 1)
    
    If no conversion is required (e.g., converting from a *float* to a *float*) this function returns *None*.  It will throw an
    exception if no conversion is possible. 
    
    >>> get_format_converter('time', 'time') is None
    True
    >>> get_format_converter('time', 'datetime')
    Traceback (most recent call last):
        ...
    FormatError: Cannot automatically convert from time to datetime
    
    """
    source, dest = _lf(source).key, _lf(dest).key
    
    try:
        return _converters[(source, dest)]
    except:
        if source == dest:
            return None
        else:
            raise FormatError('Cannot automatically convert from %s to %s' % (source, dest))