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

import os, datetime, re
#from itertools import chain
from . import Loader, Saver, register, FileLoader, FileSaver
#from ..errors import *
from ..variables import VariableSpec, _c, Variable
from .options import option
from ..util import memoize
#from itertools import izip

import csv

@option(default = ',')
def delimiter(options):
    pass

@option(default = True)
def double_quote(options):
    pass

@option(default = os.linesep)
def line_delimiter(options):
    pass

@option(default = '')
def escape_char(options):
    pass

@option(default = '"')
def quote_char(options):
    pass

@option(default = csv.QUOTE_MINIMAL)
def quoting(options):
    pass

@option(default = False)
def skip_init_space(options):
    pass

@option(default = 'utf-8')
def encoding(options):
    pass

@option(default = None)
def dataset(options):
    pass

'''
list of variable names
'''
@option(default = None)
def var_names(options):
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
                        
class CSVHandler(FileLoader, FileSaver):
    id = ('cardsharp.loaders.csv', 'cardsharp.loaders.comma',)
    formats = ('csv', 'comma',)
    
    def list_datasets(self, options):
        return None
    
    def get_dataset_info(self, options):
        f = csv.reader(open(options['filename'], 'rb'), delimiter = str(options['delimiter']), 
                       doublequote = options['double_quote'], quotechar = str(options['quote_char']), 
                       escapechar = str(options['escape_char']), lineterminator = options['line_delimiter'],
                       quoting = options['quoting'], skipinitialspace = options['skip_init_space'])
        
        if options['var_names']:
            options['_variables'] = VariableSpec(options['var_names'])
        else:
            options['_variables'] = VariableSpec(f.next())
            
        options['_cases'] = None
        options['format'] = 'csv'

    def can_load(self, options):
        if options.get('format') in ('comma', 'csv',):
            return 5000

        f = options.get('filename')
        if f and f.endswith('.csv'):
            return 5000

        return 0
                
    class loader(Loader):
        def rows(self):   
            opt = self.options
            f = csv.reader(open(opt['filename'], 'rb'), delimiter = str(opt['delimiter']), 
                       doublequote = opt['double_quote'], quotechar = str(opt['quote_char']), 
                       escapechar = str(opt['escape_char']), lineterminator = opt['line_delimiter'],
                       quoting = opt['quoting'], skipinitialspace = opt['skip_init_space'])
            
            #assumes first row is header row if variable names are not specified
            if not opt['var_names']:
                f.next()
                
            for line in opt['_filter'].filter(f):
                yield (text_to_var(var, value) for var, value in opt['_variables'].pair_filter(line))
                    
    def can_save(self, options):
        if options.get('format') in ('comma', 'csv',):
            return 5000

        return 0

    class saver(Saver):         
        def rows(self):
            opt = self.options
            
            out = csv.writer(open(opt['filename'], 'wb'), delimiter = str(opt['delimiter']), 
                       doublequote = opt['double_quote'], quotechar = str(opt['quote_char']), 
                       escapechar = str(opt['escape_char']), lineterminator = opt['line_delimiter'],
                       quoting = opt['quoting'], skipinitialspace = opt['skip_init_space'])

            out.writerow([v.name for v in opt['_variables'].filter()])
            while True:
                row = (yield)
                out.writerow([_var_to_text(var, value) for var, value in opt['_variables'].pair_filter(row)])
   
register(CSVHandler())