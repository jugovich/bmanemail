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

import sys, os, tempfile
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..', '..', 'code')))

from random import Random
from nose.tools import assert_raises, assert_almost_equal
import random
import base64
import cardsharp as cs

def assert_cs_raises(excClass, ds):
    try:
        ds.wait()
    except cs.VoidDatasetError as vde:
        ex_type, _, _ = vde.exc_info()
        if ex_type == excClass:
            return
        
        if hasattr(excClass, '__name__'): 
            excName = excClass.__name__
        else:
            excName = str(excClass)
            
        raise AssertionError, '%s not raised' % excName

    raise AssertionError, 'No error raised'

def random_caps(s):
    _r = Random()
    _r.seed(hash(s))

    return ''.join(c.upper() if _r.randint(0, 1) else c.lower() for c in s)

def construct_random_dataset(rows = None, unicode_range = (0, 65535), year_range = (0, 9999), unicode_length = 1000, binary_length = 1000):
    if not rows:
        rows = cs.config.test_rows
    
    _r = Random()
    _r.seed(1)

    import datetime
    from decimal import Decimal
    from functools import partial

    _r0 = partial(_r.randint, 0)
    _r1 = partial(_r.randint, 1)
    
    def _rint(range):
        return _r.randint(*range)
    
    def _rfloat(range):
        return _r.uniform(*range)
    
    quotes = ('\'','"')
    def _check_quotes(val):
        try: 
            if val[0] in quotes and val[-1] not in quotes: 
                val[-1] =  val[0]
        except:
            pass
        return val
    
    vars = [
        ('a', 'string', lambda: _check_quotes(''.join([unichr(_rint(unicode_range)) for _ in xrange(_r0(unicode_length))]))),
        ('b', 'integer', lambda: _r.randint(-10000, 10000)),
        ('c', 'decimal', lambda: Decimal(str(_r.uniform(-10000, 10000)))),
        ('d', 'float', lambda: _r.uniform(-10000, 10000)),
        ('e', 'datetime', lambda: datetime.datetime(year = _rint(year_range), month = _r1(12), day = _r1(28), hour = _r0(23), minute = _r0(59), second = _r0(59))),
        ('f', 'date', lambda: datetime.date(year = _rint(year_range), month = _r1(12), day = _r1(28))),
        ('g', 'time', lambda: datetime.time(hour = _r0(23), minute = _r0(59), second = _r0(59))),
        ('h', 'boolean', lambda: True if _r0(1) else False),
        ('i', 'binary', lambda: ''.join([unichr(_rint(unicode_range)) for _ in xrange(_r0(binary_length))]).encode('utf-8')),
    ]

    d = cs.Dataset([(v, f) for v, f, func in vars])

    for _ in xrange(rows):
        r = [func() for v, f, func in vars]
        d.add_row(r)
          
    return d

def construct_dataset(vars, rows):
    d = cs.Dataset([(v, f) for v, f, func in vars])

    for _ in xrange(rows):
        r = [func() for v, f, func in vars]
        d.add_row(r)
          
    return d

def get_temp_file(suffix):
    class TempFile(object):
        def __init__(self):
            self.name = tempfile.mktemp(suffix = '.' + suffix, prefix = 'test_', dir = os.path.join(os.path.dirname(__file__), 'test'))
        
        def __enter__(self):
            return self
        
        def __exit__(self, ex_type, ex_value, ex_tb):
            if os.path.exists(self.name) and cs.config.test_remove_temp_files:
                try:
                    os.remove(self.name)
                except:
                    pass
    
    return TempFile()

cs.config.add_option('remove_temp_files', converter = cs.configuration._bool, default = True, section = 'test')
cs.config.add_option('rows', converter = int, default = 1000, section = 'test')
