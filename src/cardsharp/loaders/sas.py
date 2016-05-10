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

from . import Loader, Saver, register, FileLoader, FileSaver
from .options import option, after
from ..errors import *
from ..variables import Variable, VariableSpec

from contextlib import closing
import os
#import pyodbc
import _winreg
import datetime
from threading import Lock

@option(required = False)
def filename(options):
    if 'library' in options:
        if 'filename' in options:
            raise OptionError('Cannot define both library and filename')
    elif 'filename' not in options:
        raise OptionError('You must specify a library or a filename')

@after('filename')
@option()
def library(options):
    if 'library' not in options:
        options['library'], filename = os.path.split(options['filename'])
        if not filename.lower().endswith('.sas7bdat'):
            raise OptionError('Unidentified file extension: %s' % filename)
        
        options['dataset'] = filename[:-9]

@after('library')
@option(required = True)
def dataset(options):
    pass

@option(default = 255, convert = int)
def max_string_width(options):
    pass
    
_connection_lock = Lock()
def _get_cnxn(options):
    with _connection_lock:
        with _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r'Software\ODBC\Odbc.ini\sas_odbc', 0, _winreg.KEY_WRITE) as key:
            _winreg.SetValueEx(key, 'LIBHOST_x_crdshrp', 0, _winreg.REG_SZ, options['library'])
            _winreg.FlushKey(key)
    
        return pyodbc.connect(dsn = 'sas_odbc', autocommit = True)

def _conv_var(var, value, opt):
    key = var.format.key
    if key == 'string':
        if value is None:
            return None
        
        return value.encode('utf-8')
        
    return value

def _get_var_type(var, opt):
    key = var.format.key
    if key == 'string':
        length = var.rules.length
        if length is None:
            length = opt['max_string_width']
            
        return 'VARCHAR (%s)' % length
    
    if key == 'float':
        return 'FLOAT'
    
    if key == 'decimal':
        return 'DECIMAL'
    
    if key == 'integer':
        return 'INTEGER'
    
    if key == 'date':
        return 'DATE'
    
    if key == 'time':
        return 'TIME'
    
    if key == 'datetime':
        return 'TIMESTAMP'
    
    raise SaveError('Cannot save datatype %s to SAS' % key)
        
class SasOdbcHandler(FileLoader, FileSaver):
    id = 'cardsharp.loaders.sas'
    formats = ('sas', )
    
    def list_datasets(self, options):
        with closing(_get_cnxn(options)) as cnxn:
            with closing(cnxn.cursor()) as cursor:
                return [row.table_name for row in cursor.tables()]
    
    def get_dataset_info(self, options):
        with closing(_get_cnxn(options)) as cnxn:
            with closing(cnxn.cursor()) as cursor:
                cursor.execute('select * from crdshrp.%s' % options['dataset'])
                vars = []
                for var_desc in cursor.description:
                    name = var_desc[0]
                    type_code = var_desc[1]
                    
                    if type_code == str:
                        vars.append(Variable(name, 'string', length = var_desc[3]))
                    elif type_code == float:
                        vars.append((name, 'float'))
                    elif type_code == datetime.date:
                        vars.append((name, 'date'))
                    elif type_code == datetime.time:
                        vars.append((name, 'time'))
                    elif type_code == datetime.datetime:
                        vars.append((name, 'datetime'))
                    else:
                        raise LoaderError('Unknown datatype for SAS: %r' % type_code)
                
                cursor.execute('select count(*) from crdshrp.%s' % options['dataset'])
                options['_cases'] = int(cursor.fetchone()[0])
                options['_variables'] = VariableSpec(vars)
                options['format'] = 'sas'

    def can_load(self, options):
        if options.get('format') == 'sas':
            return 5000

        if 'library' in options and 'dataset' in options:
            return 2500
        
        f = options.get('filename')
        if f and os.path.splitext(f)[1].lower() == '.sas7bdat':
            return 5000

        return 0
   
    class loader(Loader):
        def rows(self):
            opt = self.options
            with closing(_get_cnxn(opt)) as cnxn:
                with closing(cnxn.cursor()) as cursor:
                    cursor.execute('select * from crdshrp.%s' % opt['dataset'])
                    for row in opt['_filter'].filter(cursor):
                        yield opt['_variables'].filter(row)
                        
    def can_save(self, options):
        if options.get('format') == 'sas':
            return 5000

        return 0

    class saver(Saver):
        def rows(self):
            opt = self.options
            with closing(_get_cnxn(opt)) as cnxn:
                with closing(cnxn.cursor()) as cursor:
                    var_text = ', '.join('%s %s' % (v.name, _get_var_type(v, opt)) for v in opt['_variables'].filter())
                    cursor.execute('create table crdshrp.%s (%s)' % (opt['dataset'], var_text))
                    try:
                        while True:
                            row = (yield)
                            inserts, questions = [], []
                            for var, value in opt['_variables'].pair_filter(row):
                                if value is None:
                                    questions.append('null')
                                else:
                                    inserts.append(_conv_var(var, value, opt))
                                    questions.append('?')
                                    
                            cursor.execute('insert into crdshrp.%s VALUES (%s)' % (opt['dataset'], ', '.join(questions)), *inserts)
                                            
                    except (GeneratorExit, StopIteration):
                        pass

register(SasOdbcHandler())