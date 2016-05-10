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

import xlrd, xlwt, xlutils 
from xlutils.copy import copy
from . import Loader, Saver, register, DatasetInfo, FileLoader, FileSaver, LOADING
from ..util import as_iter, memoize
from ..errors import *
from ..variables import VariableSpec
from itertools import count, izip
from functools import wraps
from . import LOADING
from .options import option, saves, loads, VARIABLES_STAGE
import os, datetime


def _get_from_convert(options, datemode):
    '''Internal helper function to load excel data into csharp dataset. 
    '''
    delete_empty_string = True

    def check_empty(func):
        '''Checks to see if the value passed to one of the conversion functions is empty. 
        If it is then *None* is returned. If the value passed to the conversion function 
        is a single whitespace character then *None* is also returned.
        '''
        if delete_empty_string:
            @wraps(func)
            def _exec(value):
                #if we do unicode(value).strip() then load_test will fail 
                #when trying to save single whitespace unicode value i.e. unichar(10)
                if unicode(value).strip() == '':
                    return None
                return func(value)
            return _exec
        else:
            return func

    _CONVERT_FROM = dict()
    def convert_from(types, fs):
        def _exec(func):
            for t in as_iter(types):
                for f in as_iter(fs):
                    _CONVERT_FROM[(t, f)] = func
            return func
        return _exec

    @convert_from(xlrd.XL_CELL_DATE, 'string')
    def _conv_date_str(value):
        if unicode(value).strip() == '':
            return None
        year, month, day, hour, minute, second  = xlrd.xldate_as_tuple(value, datemode)
        if 1 > value >= 0:
            return '%i:%i:%i' % (hour, minute, second)
        elif value - int(value) == 0:
            return '%i/%i/%i' % (month, day, year)
        else:
            return '%i/%i/%i %i:%i:%i' % (month, day, year, hour, minute, second)  
        
    @convert_from((xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_TEXT, xlrd.XL_CELL_NUMBER), 'string')
    @check_empty
    def _conv_str(value):
        return unicode(value)

    @convert_from((xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_TEXT, xlrd.XL_CELL_NUMBER), 'binary')
    @check_empty
    def _conv_binary(value):
        return bytes(value)

    @convert_from(xlrd.XL_CELL_ERROR, ('string', 'binary'))
    @check_empty
    def _conv_err_str(value):
        if value == 0: # Null
            return None
        return xlrd.error_text_from_code(value)

    @convert_from(xlrd.XL_CELL_ERROR, ('date', 'datetime', 'time', 'integer', 'boolean', 'decimal'))
    @check_empty
    def _conv_err(value):
        if value == 0: # Null
            return None
        raise LoadError('Cannot convert an Excel error (%s) to a value' % xlrd.error_text_from_code(value))

    @convert_from((xlrd.XL_CELL_TEXT, xlrd.XL_CELL_NUMBER), 'float')
    @check_empty
    def _conv_float(value):
        return repr(float(value))
    
    @convert_from(xlrd.XL_CELL_BOOLEAN, 'string')
    @check_empty
    def _conv_bool(value):
        return 'True' if value == 1 else 'False'
    
    @convert_from(xlrd.XL_CELL_BOOLEAN, 'boolean')
    @check_empty
    def _conv_bool(value):
        return True if value == 1 else False
    

    @convert_from((xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE), 'date')
    @check_empty
    def _conv_date(value):
        return datetime.date(xlrd.xldate_as_tuple(value, datemode))

    #XL_CELL_EMPTY    empty string u''
    #XL_CELL_TEXT     a Unicode string
    #XL_CELL_NUMBER   float
    #XL_CELL_DATE     float
    #XL_CELL_BOOLEAN  int; 1 means TRUE, 0 means FALSE
    #XL_CELL_ERROR    int representing internal Excel codes; for a text representation, refer to the supplied dictionary error_text_from_code
    #XL_CELL_BLANK

    def _convert(var, value, cell_type):
        converter = _CONVERT_FROM[(cell_type, var.format.key)]
        if converter is None:
            raise LoadError('Cannot load %s from cell %s in Excel' % (var.format.key, cell_type))
        return converter(value)

    return _convert

@option(default = 'Sheet1')
def dataset(options):
    '''Dataset option for excel loader. The default is set to *Sheet1*.'''
    pass
@saves
@option(default = 'error')
def invalid_date(options):
    '''invalid_date option determines what to do when a date with a value < 1900 (windows) and 1904 (mac) is encountered during saving.
    If invalid_date == "error" then a SaveError will be raised. If invalid_date == *None* then 'invalid_date_range'
    is saved to the excel file. 
    '''
    pass

@saves
@option(stage = VARIABLES_STAGE)
def styles(options):
    styles = options.get('styles') or dict()
    vars = options['_variables']
    options['styles'] = dict((vars[var].name, s) for var, s in styles.iteritems())

class ExcelHandler(FileLoader, FileSaver):
    id = ('cardsharp.loaders.excel', 'cardsharp.loaders.ms_excel')
    formats = ('ms_excel', 'excel')
    
    def list_datasets(self, options):
        wb = xlrd.open_workbook(options['filename'])
        return wb.sheet_names()

    def get_dataset_info(self, options):
        wb = xlrd.open_workbook(options['filename'])
        sheet = wb.sheet_by_name(options['dataset'])
        options['_cases'] = sheet.nrows - 1
        variables = []
        for c in xrange(sheet.ncols):
            if not sheet.cell_value(0, c):
                break

            variables.append(unicode(sheet.cell_value(0, c)).strip())

        options['_variables'] = VariableSpec(variables)
        options['format'] = 'ms_excel'

    def can_load(self, options):
        if options.get('format') in ('excel', 'ms_excel'):
            return 5000

        f = options.get('filename')
        if f and f.endswith('.xls'):
            return 5000

        return 0

    class loader(Loader):
        def rows(self):
            wb = xlrd.open_workbook(self.options['filename'])
            sheet = wb.sheet_by_name(self.options['dataset'])
            convert = _get_from_convert(self.options, wb.datemode)
            for row in self.options['_filter'].filter(range(1, sheet.nrows)):  
                yield (convert(var, cell.value, cell.ctype) for var, cell in self.options['_variables'].pair_filter(sheet.row(row)))

    def can_save(self, options):
        if options.get('format') in ('excel', 'ms_excel'):
            return 5000

        return 0

    class saver(Saver):
        def rows(self):
            styles = {'date': 'DD-MMM-YYYY', 'time': 'hh:mm:ss', 'datetime': 'DD-MMM-YYYY hh:mm:ss'}
            
            @memoize
            def _get_style(s):
                style = xlwt.XFStyle()
                style.num_format_str = styles[s]
                return style
            
            opt = self.options
            try:
                rb = xlrd.open_workbook(self.options['filename'], formatting_info = True)
                if opt['dataset'] in rb.sheet_names():
                    if opt['overwrite'] == False:
                        raise SaveError('%s dataset already exists and overwrite not enabled' % opt['dataset'])
                    elif len(rb.sheet_names()) > 1:
                        wb = copy(rb)
                    else:
                        wb = xlwt.Workbook()
                else:
                    wb = copy(rb)
            except:
                wb = xlwt.Workbook()
            
            #need to add better fix
            #if opt['overwrite'] == False:         
            ws = wb.add_sheet(opt['dataset'])
            #else:
            #    ws = wb.add_sheet(opt['dataset'] + '_overwrite')
            for col, v in enumerate(opt['_variables'].filter()):
                if col == 256:
                    raise SaveError('Too many variables to save to Excel (255 maximum)')
                ws.write(0, col, v.name)
                f = v.format.key
                s = opt['styles'].get(v.name)
                
                if s:
                    ws.col(col).set_style(s)
                else:
                    if f in ('date', 'datetime', 'time'):
                        ws.col(col).set_style(_get_style(f))

            current_row = 1

            try:
                def _check_date(val, i_dt):
                    min_year = 1900 if os.name == 'nt' else 1904 
                     
                    if val.year < min_year:
                        if i_dt == 'error':
                            raise SaveError('%i is an invalid datetime: year less than %i' % (val.year, min_year))
                        else:
                            return 'invalid_date_range'
                    
                    return val
                    
                while True:
                    row = (yield)
                    for col, (v, value) in enumerate(opt['_variables'].pair_filter(row)):
                        f = v.format.key
                        s = opt['styles'].get(v.name)
                        
                        if value is None:
                            continue
            
                        if f in ('date', 'datetime', 'time'):
                            if not s:
                                s = _get_style(f)
                            if f == 'time':
                                ws.write(current_row, col, value, s)
                            else:
                                ws.write(current_row, col, _check_date(value, opt['invalid_date']), s)        
                        elif f == 'binary':
                            ws.write(current_row, col, unicode(value, 'utf-8'))
                        elif s:
                            ws.write(current_row, col, value, s)
                        else:
                            ws.write(current_row, col, value)

                    current_row += 1
            except (GeneratorExit, StopIteration):
                wb.save(opt['filename'])
                        
register(ExcelHandler())