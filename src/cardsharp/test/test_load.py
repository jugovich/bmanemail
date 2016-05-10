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

from __future__ import unicode_literals, absolute_import

import cardsharp as cs
from cardsharp.test import construct_random_dataset, get_temp_file, construct_dataset, assert_raises, assert_cs_raises
from ..convert import *
import datetime
from cardsharp.errors import SaveError
import re

from itertools import izip_longest

format_info = {
#    'sas' : {
#        'ext' : 'sas7bdat',
#    },
    'text' : {
        'ext' : 'txt',
    },
    'del' : {
        'ext' : 'del',
    },
    'excel' : {
        'ext' : 'xls',
    },
    'spss' : {
        'ext' : 'sav',
    },
    'csharp' : {
        'ext' : 'csharp',
    },
    'csv' : {
        'ext' : 'csv',
    },
    'mysql' : {
        'ext' : 'mysql',
    },
}

def _row_test(i, r1, r2):
    assert tuple(r1 or ()) == tuple(r2 or ()), 'Row %i does not match after saving and loading' % i

def _roundtrip(ext, d1, row_test = _row_test, **kw):
    '''Testing function to ensure that every loader is able to save data to its respective format 
    and that when it loads the saved data the data matches the original csharp dataset.
    '''
    with get_temp_file(ext) as temp:
        if kw['format'] == 'mysql':
            d1.save(filename = 'test', **kw)            
        else:
            d1.save(filename = temp.name, **kw)
        cs.wait()
        if kw['format'] == 'mysql':
            d2 = cs.load(filename = 'test', **kw)
        else:
            d2 = cs.load(filename = temp.name, **kw)    
        
        for i, (r1, r2) in enumerate(izip_longest(d1, d2)):
            assert r1 is not None and r2 is not None, 'Datasets do not have the same length' 
            row_test(i, r1, r2)

def _text_row_test(i, r1, r2):
    r1 = (r1[0], unicode(r1[1]), unicode(r1[2]), unicode(repr(r1[3])), unicode(r1[4]).replace('-', '/'), 
            unicode(r1[5]).replace('-', '/'), unicode(r1[6]), 
            u'1' if r1[7] else u'0', r1[8].encode('base64'))
    r2 = tuple(x or u'' for x in r2)
    assert r1 == r2, 'Row %i does not match after saving and loading for text handler' % i
    
def _xls_row_test(i, r1, r2):
    r1, r2 = tuple(r1 or ()), tuple(r2 or ())
    t_r1 = (r1[0], unicode(r1[1]), unicode(r1[2]), unicode(r1[3]), r1[4], r1[5], r1[6], unicode(r1[7]), r1[8])
    t_r2 = (r2[0] or '', r2[1].replace('.0',''), r2[2], r2[3], 
            str_to_datetime(r2[4], '%m/%d/%Y %H:%M:%S'), str_to_date(r2[5], '%m/%d/%Y'), 
            str_to_time(r2[6], '%H:%M:%S'), r2[7], r1[8])
    assert t_r1 == t_r2, 'Row %i does not match after saving and loading for excel handler' % i

def _mysql_row_test(i, r1, r2):
    #time is returned as timedelta from mysqldb - value not tested here
    r1 = (r1[0], r1[1], r1[2], r1[3], r1[4], r1[5], r1[7], r1[8])
    r2 = (r2[0], r2[1], r2[2], r2[3], r2[4], r2[5], r2[7], r2[8])
    assert r1 == r2, 'Row %i does not match after saving and loading for text handler' % i

def test_csharp_roundtrip():
    ds = construct_random_dataset()
    _roundtrip('csharp', ds, format = 'csharp')

def test_csv_roundtrip():
    ds = construct_random_dataset(unicode_range = (1, 127))
    _roundtrip('csv', ds, format = 'csv', row_test = _text_row_test)

#need to document setting up mysql server
'''Currently only testing strings in ASCII range unicode_range(32, 126). Time not tested because
    MySQLdb returns as timedelta.
''' 
def test_mysql_roundtrip():    
    #TODO: need to check whole unicode range
    ds = construct_random_dataset(year_range = (1000, 9999), binary_length = 1)
    ds['a'].rules.length = 4000
    ds['a'].flags.string_width_override = True
    ds['i'].rules.length = 4000
    ds['i'].flags.string_width_override = True
    
    _roundtrip('test', ds, row_test = _mysql_row_test, format = 'mysql', user = 'root', pwd = 'pass', 
               dataset = 'test_r', overwrite = True)

def test_mysql_constraint(): 
    ds1 = cs.Dataset([('a', 'integer'), ('b', 'integer'), 'c'])
    ds1['a'].flags.primary_key = 'p_id'
    ds1['b'].flags.primary_key = 'p_id'
    ds1['c'].flags.unique = 'u_id'
    ds1['a'].flags.not_null = True
    ds1['a'].flags.auto_inc = True
    ds1['a'].flags.foreign_key = ['fk_id', 'test_c2(a)']
    ds1.add_row([None, 4, '1'])
    ds1.add_row([None, 5, '2'])
    
    ds2 = cs.Dataset([('a', 'integer'), 'b', 'c'])
    ds2['a'].rules.not_null = True
    ds2['a'].flags.primary_key = 'p_id'
    ds2.add_row([1, '1', '1'])
    ds2.add_row([2, '2', '2'])
    
    try:
        cs.drop(filename = 'test', format = 'mysql', user = 'root', pwd = 'pass', dataset = 'test_c1')
        cs.drop(filename = 'test', format = 'mysql', user = 'root', pwd = 'pass', dataset = 'test_c2')
    except:
        print 'Tables not dropped. If not initial test run than there is a bug. Remove try and rerun.'
        
    cs.wait()
    ds2.save(filename = 'test', format = 'mysql', user = 'root', pwd = 'pass', dataset = 'test_c2')
    cs.wait()
    ds1.save(filename = 'test', format = 'mysql', user = 'root', pwd = 'pass', dataset = 'test_c1')
    import MySQLdb
    from contextlib import closing
    cnxn = MySQLdb.connect(host = 'localhost', user = 'root', passwd = 'pass', db = 'test', port = 3306)
    with closing(cnxn.cursor()) as cursor:
        cursor.execute('select * FROM information_schema.columns where table_name = \'test_c1\'')
        c = cursor.fetchall()
        #check NOT NULL,  Primary Key, and auto_increment
        assert ((c[0][6] == 'NO') and (c[0][15] == 'PRI')  and (c[1][15] == 'PRI') and (c[0][16] == 'auto_increment'))
        cursor.execute('select * FROM information_schema.key_column_usage where table_name = \'test_c1\'')
        c = cursor.fetchall()
        #check foreign key
        assert ((c[3][2] == 'fk_id') and (c[3][6] == 'a') and (c[3][10] == 'test_c2')  and (c[3][11] == 'a'))
    ds3 = cs.load(filename = 'test', format = 'mysql', user = 'root', pwd = 'pass', dataset = 'test_c1')
    assert((ds3['a'].flags.primary_key == 'PRIMARY' and ds3['a'].flags.not_null == True and
            ds3['a'].flags.auto_inc == True and ds3['a'].flags.foreign_key == ['fk_id', 'test_c2(a)']))
    #con = 'FOREIGN KEY (b) REFERENCES test_r(b)'
    
def test_xls_roundtrip():                    
    ds = construct_random_dataset(unicode_range = (0, 55295), year_range = (1900, 9999))
    _roundtrip('xls', ds, row_test = _xls_row_test, format = 'ms_excel')

def test_xls_dataset():                    
    ds = construct_random_dataset(unicode_range = (0, 55295), unicode_length = 100, binary_length = 100, year_range = (1900, 9999))
    with get_temp_file('xls') as temp:
        ds.save(filename = temp.name, format = 'ms_excel', dataset = 'xlutils_copy')
        cs.wait()
        ds.save(filename = temp.name, format = 'ms_excel', overwrite = True, dataset = 'csharp_saver')
        cs.wait()
        d1 = cs.load(filename = temp.name, format = 'ms_excel', dataset = 'xlutils_copy')
        d2 = cs.load(filename = temp.name, format = 'ms_excel', dataset = 'csharp_saver')
        for i, (r1, r2) in enumerate(izip_longest(d1, d2)):
            assert r1 is not None and r2 is not None, 'Datasets do not have the same length' 
            _row_test(i, r1, r2)

def test_xls_date_save_error():
    def _test_date(date):
        with get_temp_file('xls') as temp:
            d1 = construct_dataset(date, 1)
            d1.save(filename = temp.name, format = 'ms_excel')
            assert_cs_raises(SaveError, d1) 
    
    _test_date([('a', 'datetime', lambda: datetime.datetime(year = 1899, month = 12, day = 28, hour = 23, minute = 59, second = 59))])
    _test_date([('a', 'datetime', lambda: datetime.datetime(year = 1899, month = 12, day = 28))])
        
def test_xls_unicode_load_error():
    xls_error_vars = [
         ('a', 'string', lambda: unichr(55296)),
    ]
    
    with get_temp_file('xls') as temp:
        d1 = construct_dataset(xls_error_vars, 1)
        d1.save(filename = temp.name, format = 'ms_excel')
        cs.wait()
        assert_raises(UnicodeDecodeError, cs.get_info, filename = temp.name, format = 'ms_excel')
        
def test_txt_roundtrip(): 
    ds = construct_random_dataset()
    _roundtrip('txt', ds, row_test = _text_row_test, format = 'text', encoding = 'utf_8')
    
def test_txt_delimiter():
    ds = construct_random_dataset()
    for delim, line_delim in (
        ('\t', '\n'), 
        ('\r\r', '!!!!!'),
        ('1279811', '####')):
        with get_temp_file('txt') as temp:
            ds.save(filename = temp.name, format = 'text', line_delimiter = line_delim, delimiter = delim)
            cs.wait()
            d1 = cs.load(filename = temp.name, format = 'text', line_delimiter = line_delim, delimiter = delim)
            for i, (r1, r2) in enumerate(izip_longest(ds, d1)):
                assert r1 is not None and r2 is not None, 'Datasets do not have the same length' 
                _text_row_test(i, r1, r2)
            
def test_txt_encoding():
    #need to limit unicode range to 55295 because utf_16 encoding can not handle some characters above unichr(55295)
    ds = construct_random_dataset(unicode_range = (0, 55295))
    ds['a'].rules.length = 1000
    
    for enc in ('utf-8', 'utf-16'):
        with get_temp_file('txt') as temp:
            ds.save(filename = temp.name, format = 'text', encoding = enc)
            cs.wait()
            d1 = cs.load(filename = temp.name, format = 'text', encoding = enc)
            for i, (r1, r2) in enumerate(izip_longest(ds, d1)):
                assert r1 is not None and r2 is not None, 'Datasets do not have the same length' 
                _text_row_test(i, r1, r2)

def test_del_roundtrip(): 
    ds = construct_random_dataset()
    _roundtrip('del', ds, row_test = _text_row_test, format = 'del', encoding = 'utf_8')
    
def test_del_delimiter():
    ds = construct_random_dataset()
    for delim, line_delim in (
        ('|', '\r'),
        ('\t', '\n'), 
        ('\r\r', '!!!!!'),
        ('1279811', '####')):
        with get_temp_file('del') as temp:
            ds.save(filename = temp.name, format = 'del', line_delimiter = line_delim, delimiter = delim)
            cs.wait()
            d1 = cs.load(filename = temp.name, format = 'del', line_delimiter = line_delim, delimiter = delim)
            for i, (r1, r2) in enumerate(izip_longest(ds, d1)):
                assert r1 is not None and r2 is not None, 'Datasets do not have the same length' 
                _text_row_test(i, r1, r2)
            
def test_del_encoding():
    #need to limit unicode range to 55295 because utf_16 encoding can not handle some characters above unichr(55295)
    ds = construct_random_dataset(unicode_range = (0, 55295))
    
    for enc in ('utf-8', 'utf-16'):
        with get_temp_file('del') as temp:
            ds.save(filename = temp.name, format = 'del', encoding = enc)
            cs.wait()
            d1 = cs.load(filename = temp.name, format = 'del', encoding = enc)
            for i, (r1, r2) in enumerate(izip_longest(ds, d1)):
                assert r1 is not None and r2 is not None, 'Datasets do not have the same length' 
                _text_row_test(i, r1, r2)
                
_test_keep_dataset = cs.Dataset('abcde')
_test_keep_dataset.add_row('abcde')
            
def do_keep_drop(format, stage, arg):
    with get_temp_file(format_info[format]['ext']) as temp:
        if stage == 'save':
            if format == 'mysql':
                if arg == 'keep':
                    _test_keep_dataset.save(filename = 'test', format = format, keep = 'ace',
                                            dataset = 'test_kb', user = 'root', pwd = 'pass', overwrite = True)
                else:
                    _test_keep_dataset.save(filename = 'test', format = format, drop = 'bd',
                                            dataset = 'test_kb', user = 'root', pwd = 'pass', overwrite = True)
            else:
                if arg == 'keep':
                    _test_keep_dataset.save(filename = temp.name, format = format, keep = 'ace')
                else:
                    _test_keep_dataset.save(filename = temp.name, format = format, drop = 'bd')
        else:
            if format == 'mysql':
                _test_keep_dataset.save(filename = 'test', format = format,
                                        dataset = 'test_kb', user = 'root', pwd = 'pass', overwrite = True)
            else:
                _test_keep_dataset.save(filename = temp.name, format = format)
            
        cs.wait()
        if stage == 'load':
            if format == 'mysql':
                if arg == 'keep':
                    ds = cs.load(filename = 'test', format = format, keep = 'ace',
                                 dataset = 'test_kb', user = 'root', pwd = 'pass', overwrite = True)
                else:
                    ds = cs.load(filename = 'test', format = format, drop = 'bd',
                                 dataset = 'test_kb', user = 'root', pwd = 'pass', overwrite = True)
            else:
                if arg == 'keep':
                    ds = cs.load(filename = temp.name, format = format, keep = 'ace')
                else:
                    ds = cs.load(filename = temp.name, format = format, drop = 'bd')
        else:
            if format == 'mysql':
                ds = cs.load(filename = 'test', format = format,
                             dataset = 'test_kb', user = 'root', pwd = 'pass', overwrite = True)
            else:
                ds = cs.load(filename = temp.name, format = format)
            
        assert [v.name for v in ds.variables] == ['a', 'c', 'e'], 'Variables do not match: ' + ''.join(v.name for v in ds.variables)
        for r in ds:
            assert [value for value in r] == ['a', 'c', 'e'], 'Row does not match'
       
def test_keep_or_drop():
    for format in format_info.iterkeys():
        for stage in ('load', 'save'):
            for arg in ('keep', 'drop'):
                yield do_keep_drop, format, stage, arg
                
#@TODO: loading delimited file, test variable lower and upper bounds limits
#@TODO: test excel dataset overwrite error