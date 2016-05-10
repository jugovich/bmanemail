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

import re, codecs, os, datetime
from itertools import chain
from . import Loader, Saver, register, FileLoader, FileSaver
from ..errors import *
from ..variables import VariableSpec, _c
from .options import option, loads
from ..util import memoize
from itertools import izip

@option(default = '\t', convert = unicode)
def delimiter(options):
    pass

@option(default = os.linesep, convert = unicode)
def line_delimiter(options):
    pass

@option(default = '\\', convert = unicode)
def escape_char(options):
    pass

@option(default = True)
def escape_eol_chars(options):
    pass

@option(default = 'utf-8')
def encoding(options):
    pass

@option(default = None)
def dataset(options):
    pass

@option(default = None)
def var_names(options):
    """List of variable names"""
    pass

@option(default = False)
def overwrite(options):
    pass

_save_var_map = {
    'float' : lambda v: repr(v),
    'date' : lambda v: '%04d/%02d/%02d' % (v.year, v.month, v.day),
    'datetime' : lambda v: '%04d/%02d/%02d %02d:%02d:%02d' % (v.year, v.month, v.day, v.hour, v.minute, v.second),
    'time' : lambda v: '%02d:%02d:%02d' % (v.hour, v.minute, v.second),
    'integer' : lambda v: unicode(v),
    'decimal' : lambda v: unicode(v),
    'boolean' : lambda v: '1' if v else '0',
    'binary' : lambda v: v.encode('base64'),
}

for f in _save_var_map.keys():
    _save_var_map[f] = memoize(_save_var_map[f])

_save_var_map['string'] = lambda v: v
_save_var_map['nominal'] = lambda v: v

def _var_to_text(v, value):        
    if value is None:
        return ''
    
    return _save_var_map[v.format.key](value)

def _conv_dt(pat, func):
    """ Creates the date conversion function...
    """
    pat = re.compile(pat)
    def _exec(value):
        m = pat.match(value)
        if m:
            return func(*(int(i) for i in m.groups()))
        else:
            raise LoadError('Unrecognized format: %r' % value)
        
    return _exec

_load_var_map = {
    'float' : lambda v: float(v),
    'date' : _conv_dt(r'^\s*(\d{4})/(\d{2})/(\d{2})\s*$', datetime.date),
    'datetime' : _conv_dt(r'^\s*(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})\s*$', datetime.datetime),
    'time' : _conv_dt(r'^\s*(\d{2}):(\d{2}):(\d{2})\s*$', datetime.time),
    'integer' : lambda v: int(v),
    'decimal' : lambda v: Decimal(v),
    'boolean' : lambda v: True if v in ('1', 'true', 'True') else False,
    'binary' : lambda v: bytes(v.decode('base64'))
}

for f in _load_var_map.keys():
    _load_var_map[f] = memoize(_load_var_map[f])

_load_var_map['string'] = lambda v: v

def text_to_var(v, value):
    if value == '':
        return None
    
    return _load_var_map[v.format.key](value)

def _get_load_iterators(options):
    field_delimiter = options['delimiter']
    line_delimiter = options['line_delimiter']
    
    if options['escape_char'] == None:
        escape_char = '\\'
        line_pattern = re.compile('(?s)^(.*?)' + re.escape(line_delimiter) + '(.*)$')
        field_pattern = re.compile('(?s)^(.*?)' + re.escape(field_delimiter) + '(.*)$')
    else:
        escape_char = options['escape_char']
        line_pattern = re.compile('(?s)^(.*?)(?<!' + re.escape(escape_char) + ')' + re.escape(line_delimiter) + '(.*)$')
        field_pattern = re.compile('(?s)^(.*?)(?<!' + re.escape(escape_char) + ')' + re.escape(field_delimiter) + '(.*)$')

    def _line_iter(f):
        buffer = ''
        while True:
            next = f.read(1024 * 4)
            if next == '':
                if buffer:
                    yield buffer
                    
                return
            
            buffer += next
            while buffer:
                m = re.match(line_pattern, buffer)
                if m:
                    yield m.group(1)
                    buffer = m.group(2)
                else:
                    break

    unescape_map = dict()
    if options['escape_eol_chars']:
        unescape_map['n'] = '\n'
        unescape_map['t'] = '\t'
        unescape_map['r'] = '\r'

    def _unescape(s):
        in_escape = False
        for c in s:
            if in_escape:
                yield unescape_map.get(c, c)
                in_escape = False
            elif c == escape_char:
                in_escape = True
            else:
                yield c
                
    def _field_iter(s):
        while s:
            m = re.match(field_pattern, s)
            if m:
                if options['escape_char']: 
                    yield ''.join(_unescape(m.group(1)))  
                else: 
                    yield ''.join(m.group(1))
                
                s = m.group(2)
            else:
                yield ''.join(_unescape(s))
                return
                
    return _line_iter, _field_iter
                        
class TextHandler(FileLoader, FileSaver):
    id = ('cardsharp.loaders.tab', 'cardsharp.loaders.text', 'cardsharp.loaders.del')
    formats = ('text', 'del',)
    
    def list_datasets(self, options):
        return None
    
    def get_dataset_info(self, options):
        _line_iter, _field_iter = _get_load_iterators(options)
        
        with codecs.open(options['filename'], 'rb', options['encoding']) as in_stream:
            f = _line_iter(in_stream)
            if options['var_names']:
                options['_variables'] = VariableSpec(options['var_names'])
            else:
                options['_variables'] = VariableSpec(_field_iter(f.next()))
        
        options['_cases'] = None
        options['format'] = 'text'

    def can_load(self, options):
        if options.get('format') in ('tab', 'delimited', 'text', 'del'):
            return 5000

        f = options.get('filename')
        if f and (f.endswith('.txt') or f.endswith('.del')):
            return 5000

        return 0
                
    class loader(Loader):
        def rows(self):   
            opt = self.options
            _line_iter, _field_iter = _get_load_iterators(opt)

            with codecs.open(opt['filename'], 'rb', opt['encoding']) as in_stream:
                f = _line_iter(in_stream)
                if not opt['var_names']:
                    #print 'warning: loading text file without var_names option. Using first row in data as var names.' 
                    f.next() 
                for line in opt['_filter'].filter(f):
                    yield (text_to_var(var, value) for var, value in opt['_variables'].pair_filter(_field_iter(line)))
                    
    def can_save(self, options):
        if options.get('format') in ('tab', 'delimited', 'text', 'del'):
            return 5000
        
        return 0

    class saver(Saver):         
        def rows(self):
            opt = self.options
            
            escape_char = opt['escape_char'] if opt['escape_char'] else '\\' 
            field_delimiter = opt['delimiter']
            line_delimiter = opt['line_delimiter']
            
            escape_map = { escape_char : escape_char + escape_char }
            if opt['escape_eol_chars']:
                escape_map['\n'] = escape_char + 'n'
                escape_map['\t'] = escape_char + 't'
                escape_map['\r'] = escape_char + 'r'
                
            for c in chain(field_delimiter, line_delimiter):
                escape_map.setdefault(c, escape_char + c)
                
            def _escape_field(s):
                return ''.join(escape_map.get(c, c) for c in s)
            
            if os.path.exists(opt['filename']) and not opt['overwrite']:
                raise SaveError('%s file already exists and overwrite not enabled' % opt['filename'])
            
            with codecs.open(opt['filename'], 'wb', opt['encoding']) as out:
                out.write(field_delimiter.join(_escape_field(v.name) for v in opt['_variables'].filter()) + line_delimiter)
                while True:
                    row = (yield)
                    out.write(opt['delimiter'].join(_escape_field(_var_to_text(var, value)) for var, value in opt['_variables'].pair_filter(row)) + line_delimiter)
   
register(TextHandler())