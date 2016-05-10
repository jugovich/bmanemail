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

import re, codecs, os
from itertools import chain
from . import Loader, Saver, register, FileLoader, FileSaver
from ..errors import LoadError, SaveError
from ..variables import VariableSpec
from .options import option, saves
from ..util import memoize

@option(default = 'utf-8')
def encoding(options):
    """Option for specify the file encoding. Default is utf-8."""
    pass

@option(default = 'd1')
def dataset(options):
    """Option for setting the relation name. Default = d1"""
    pass

@option(default = True)
def escape_eol_chars(options):
    """Option for escaping eol characters. This should not be changed."""
    pass

@saves
@option(default = {})
def nominal_map(options):
    """This is a list of the class mapping for nominal variables. If the dataset contains nominal variables and 
    this mapping is not supplied during saving the SaveErrors will be raised. If the nominal_map is supplied but
    does not cover all possible occurences then the arff file will not load correctly in weka."""
    pass

def _quote(v):
    """Helper function to remove quotes."""
    return '"' + v + '"' if ' ' in v else v

#dictionary to be used for variable conversions during saving
_save_var_map = {
    'float'    : lambda v: repr(v),
    'date'     : lambda v: '"%04d/%02d/%02d"' % (v.year, v.month, v.day),
    'datetime' : lambda v: '"%04d/%02d/%02d %02d:%02d:%02d"' % (v.year, v.month, v.day, v.hour, v.minute, v.second),
    'time'     : lambda v: '"%02d:%02d:%02d"' % (v.hour, v.minute, v.second),
    'integer'  : lambda v: repr(v),
    'decimal'  : lambda v: repr(v),
    'boolean'  : lambda v: '1' if v else '0',
    'binary'   : lambda v: _quote(v.encode('base64')),
}

#dictionary to be used for variable conversions during saving
_save_var_info = {
    'float'    : 'numeric',
    'date'     : 'date "yyyy-MM-dd"', 
    'datetime' : 'date "yyyy-MM-dd\'T\'HH:mm:ss"', 
    'time'     : 'date "\'T\'HH:mm:ss"', 
    'integer'  : 'numeric', 
    'decimal'  : 'numeric', 
    'boolean'  : '{1 0}',
    'binary'   : 'string',
    'string'   : 'string',
}

#add dictionary entries using memoization for processing speed-ups
for f in _save_var_map.keys():
    _save_var_map[f] = memoize(_save_var_map[f])

_save_var_map['nominal'] = lambda v: _quote(v)
_save_var_map['string'] = lambda v: _quote(v) 

#function for converting variable information to text for saving
def _var_to_text(v, value):        
    if value is None:
        return ''
    
    return _save_var_map[v.format.key](value)

#def _conv_dt(pat, func):
#    """ Creates the date conversion function...
#    """
#    pat = re.compile(pat)
#    def _exec(value):
#        m = pat.match(value)
#        if m:
#            return func(*(int(i) for i in m.groups()))
#        else:
#            raise LoadError('Unrecognized format: %r' % value)
#        
#    return _exec

#dictionary to be used for variable conversions during loading
_load_var_map = {
    'numeric' : lambda v: float(v),
    'integer' : lambda v: float(v),
    'real'    : lambda v: float(v),
    'float'   : lambda v: float(v),
    #'date' : _conv_dt(r'^\s*(\d{4})/(\d{2})/(\d{2})\s*$', datetime.date),
    #'datetime' : _conv_dt(r'^\s*(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})\s*$', datetime.datetime),
    #'time' : _conv_dt(r'^\s*(\d{2}):(\d{2}):(\d{2})\s*$', datetime.time),
    #'integer' : lambda v: int(v),
    #'decimal' : lambda v: Decimal(v),
    #'boolean' : lambda v: True if v in ('1', 'true', 'True') else False,
    #'binary' : lambda v: bytes(v.decode('base64'))
}

#dictionary to be used for variable conversions during loading
_var_info_map = {
    'numeric' : 'float',
    'integer' : 'float',
    'real'    : 'float',
    'string'  : 'string',
}

#add dictionary entries using memoization for processing speed-ups
for f in _load_var_map.keys():
    _load_var_map[f] = memoize(_load_var_map[f])

_load_var_map['string'] = lambda v: v
_load_var_map['nominal'] = lambda v: v

#function for converting text to variables during loading
def text_to_var(v, value):
    if value == '':
        return None
    
    return _load_var_map[v.format.key](value)

def _get_load_iterators(options):
    """Helper function to use for loading .arff data"""
    
    #declare delimiters and field/line iterators
    field_delimiter = ','
    line_delimiter = '\n'
    escape_char    = '\\'
    
    line_pattern = re.compile('(?s)^(.*?)' + re.escape(line_delimiter) + '(.*)$')
    field_pattern = re.compile('(?s)^(.*?)' + re.escape(field_delimiter) + '(.*)$')
    
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
                yield ''.join(m.group(1))
                s = m.group(2)
            else:
                yield ''.join(_unescape(s))
                return
                
    return _line_iter, _field_iter

#currently does not support relational instances or dates
def _get_var(var_info):
    name = var_info[0]
    #format = _var_info_map[var_info[1].replace('\r', '')]
    if '{' not in var_info[1] and var_info[1].replace('\r', '') in _var_info_map:
        format = _var_info_map[var_info[1].replace('\r', '')]
    elif var_info[1].startswith('{'):
        format = 'nominal'
    else:
        raise LoadError("Unsupported Variable Format: %s" % var_info[1])
    
    return (name, format)

#get the format
def _get_format(opt, var):
    if str(var.format) == 'nominal' and var.name not in opt['nominal_map']:
        raise SaveError('Unable to save nominal variable: %s, because it has no entry in nominal_map option' % var.name)
    
    if str(var.format) == 'nominal':
        return '{' + ','.join(opt['nominal_map'][var.name]) + '}'  
    else:
        return _save_var_info[str(var.format)]
           
class ArffHandler(FileLoader, FileSaver):
    """Arff handler for loading and saving .arff files (weka)."""
    id = ('cardsharp.loaders.arff',)
    formats = ('arff',)
    
    def list_datasets(self, options):
        return None
    
    def get_dataset_info(self, options):
        """Get the relation name and variable information."""
        _line_iter, _field_iter = _get_load_iterators(options)
        vars = []
        
        with codecs.open(options['filename'], 'rb', options['encoding']) as in_stream:    
            f = _line_iter(in_stream)
            for line in f:
                line = line.lower() if line else ''
                if line.startswith('@attribute'):
                    var = _get_var(re.search('@attribute (.+?) (.+)', line).groups())
                    vars.append(var)
                elif line.startswith('@relation'):
                    options['dataset'] = line.replace('@relation ', '')
                elif line.startswith('@data'):
                    break
                    #can add mark to get cases if desired
            options['_variables'] = VariableSpec(vars)
                
        
        options['_cases'] = None
        options['format'] = 'arff'

    #check to see if we can load
    def can_load(self, options):
        if options.get('format') in ('arff',):
            return 5000

        f = options.get('filename')
        if f and (f.endswith('.arff')):
            return 5000

        return 0
                
    class loader(Loader):
        """arff loader"""
        #iterate over rows loading in new inforamation
        def rows(self):   
            opt = self.options
            _line_iter, _field_iter = _get_load_iterators(opt)

            #open the file and load
            with codecs.open(opt['filename'], 'rb', opt['encoding']) as in_stream:
                f = _line_iter(in_stream)
                data = False 
                for line in opt['_filter'].filter(f):
                    line = line if line else ''
                    if not data:
                        if line.lower().startswith('@data'):
                            data = True
                    else:
                        if line:
                            yield (text_to_var(var, value) for var, value in opt['_variables'].pair_filter(_field_iter(line)))
                    
    #check to see if we can save
    def can_save(self, options):
        if options.get('format') in ('arff',):
            return 5000
        
        return 0

    class saver(Saver):
        """arff saver"""
        #save the row data
        def rows(self):
            opt = self.options
            
            escape_char = '\\' 
            field_delimiter = ','
            line_delimiter = os.linesep
            
            #escapes!
            escape_map = { escape_char : escape_char + escape_char }
            
            escape_map['\n'] = escape_char + 'n'
            escape_map['\r'] = escape_char + 'r'
                
            for c in chain(field_delimiter, line_delimiter):
                escape_map.setdefault(c, escape_char + c)
                
            def _escape_field(s):
                return ''.join(escape_map.get(c, c) for c in s)
            
            if os.path.exists(opt['filename']) and not opt['overwrite']:
                raise SaveError('%s file already exists and overwrite not enabled' % opt['filename'])
            
            with codecs.open(opt['filename'], 'wb', opt['encoding']) as out:
                out.write('@relation %s%s' % (opt['dataset'], line_delimiter))
                out.write(line_delimiter)
                for var in opt['_variables'].filter():
                    format = _get_format(opt, var)
                    out.write('@attribute %s %s%s' % (var.name, format, line_delimiter))
                out.write(line_delimiter + '@data' + line_delimiter)
                while True:
                    row = (yield)
                    out.write(','.join(_escape_field(_var_to_text(var, value)) for var, value in opt['_variables'].pair_filter(row)) + line_delimiter)
   
register(ArffHandler())