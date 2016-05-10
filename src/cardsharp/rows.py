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

__all__ = ['Row', 'Rows', ]

from .errors import *
from .util import NOT_DEFINED, fill_variable_defaults
from .variables import VariableMap
from threading import RLock, Condition
from itertools import count
import sys

class Mark(object):
    _high_id = count(1).next
    
    def __init__(self, rows, info):
        self.index = None
        self.next_mark = None
        self.available_rows = 0
        self.info = info
        self.id = self._high_id()
        
        self.rows = rows
        self.variables = rows.variables.copy()
        
        self.current_row = None    
        self.lock = self.rows._row_lock
        self.flag = Condition()
        
        self.active = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize()
        return False
    
    def finalize(self):
        with self.lock:
            with self.flag:
                self.active = False
                self.flag.notify_all()
            
    def _next_active_mark(self):
        next_mark = self.next_mark
        while next_mark and not next_mark.active:
            next_mark = next_mark.next_mark
            
        return next_mark
    
    def _advance(self):
        if self.index is None:
            self.index = 0
            self.current_row = self.rows._first_row
        elif self.current_row:
            if not self.current_row.deleted:
                self.index += 1
                
            self.current_row = self.current_row._next_row
        
        while self.current_row and self.current_row.deleted:
            self.current_row = self.current_row._next_row
        
        if self.current_row:
            self.current_row._variables = self.variables
            
        with self.flag:
            self.flag.notify_all()
        
        if self.current_row is None:
            raise NoMoreRowsError()
        
    def available(self):
        with self.lock:
            if self.available_rows != 0:
                return self.available_rows
    
            next_mark = self._next_active_mark()
            if next_mark is None:
                self.available_rows = None
                return None
            
            if next_mark.index:
                self.available_rows = max(next_mark.index - (self.index or 0) - 1, 0)
                return self.available_rows
            
            self.available_rows = 0
            return 0
           
    def advance(self):
        while True:
            with self.lock:
                available = self.available()
                
                if available is None:
                    self._advance()
                    return
                
                if available:
                    self.available_rows -= 1
                    self._advance()
                    return
                
                next_mark = self._next_active_mark()
                
            with next_mark.flag:
                if next_mark.active:
                    next_mark.flag.wait()
                      
    def add_row(self, values = ()):
        row = self._create_row(values)
        self._add_row(row)
        return row 
    
    def _create_row(self, values = ()):
        return Row(self.rows, self.variables, fill_variable_defaults(self.variables, values))
    
    def _add_row(self, row):
        with self.lock:
            if not self.active:
                raise MarkInactiveError()
            
            if self.index is not None:
                self.index += 1
                row._next_row, self.current_row._next_row = self.current_row._next_row, row
                self.current_row = row
            
                next_mark = self.next_mark
                while next_mark:
                    next_mark.index += 1
                    next_mark = next_mark.next_mark
                
                self.rows._count += 1
                return row
            
        next_mark = self._next_active_mark()               
        while next_mark is not None:
            with next_mark.flag:
                if not next_mark.active:
                    next_mark = self._next_active_mark()
                    continue
                    
                if next_mark.index is not None:
                    break
                
                next_mark.flag.wait()
                
            next_mark = self._next_active_mark()
            
        with self.lock:
            self.index = 0
            self.current_row = row
            row._next_row, self.rows._first_row = self.rows._first_row, row
            next_mark = self.next_mark
            while next_mark:
                if next_mark.index is not None:
                    next_mark.index += 1
                
                next_mark = next_mark.next_mark
			
            self.rows._count += 1
            
			
    def void(self):
        with self.lock:
            if not self.rows._voided:
                ex_type, ex_value, ex_tb = sys.exc_info()
                while ex_type == VoidDatasetError:
                    ex_type, ex_value, ex_tb = ex_value.exc_info()
                    
                self.rows._voided = (ex_type, ex_value, ex_tb)

            self.finalize()
            
    def __repr__(self):
        return '<Mark %i@%s (%s)>' % (self.id, self.index, self.info)
        
class Rows(object):
    def __init__(self, data, variables):
        self._dataset = data
        self._variables = variables
        
        self._row_lock = RLock()
        
        self._last_mark = None
        self._first_row = None
        self._marks = set()
        self._count = 0
        self._voided = None
    
    @property
    def variables(self):
        if self._voided:
            raise VoidDatasetError(self._voided)
            
        return self._variables
        
    def __len__(self):
        return self._count

    def create_mark(self, info):
        with self._row_lock:
            if self._voided:
                raise VoidDatasetError(self._voided)
            
            mark = Mark(self, info)
            self._last_mark, mark.next_mark = mark, self._last_mark
            self._marks.add(mark)
            
        return mark
    
    def __iter__(self):
        with self.create_mark('Iterating') as mark:
            while True:
                try:
                    mark.advance()
                except NoMoreRowsError:
                    return
                
                if self._voided:
                    raise VoidDatasetError(self._voided)
                
                yield mark.current_row
                
    def add_row(self, values):
        with self.create_mark('Adding Row') as mark:
            mark.add_row(values)
    
    def wait(self):
        with self._row_lock:
            marks = set()
            next_mark = self._last_mark
            while next_mark:
                if next_mark.active:
                    marks.add(next_mark)
                
                next_mark = next_mark.next_mark
                
        for mark in marks:
            with mark.flag:
                while mark.active:
                    mark.flag.wait()

        if self._voided:
            raise VoidDatasetError(self._voided)
            
class Row(object):
    def __init__(self, rows, variables, values):
        self._rows = rows
        self._lock = self._rows._row_lock
        self._next_row = None
        self._deleted = False
        self._variables = variables
        self._values = values
        
    @property
    def deleted(self):
        return self._deleted
    
    def delete(self):
        if not self._deleted:
            self._deleted = True
            self._rows._count -= 1
    
    def __unicode__(self):
        return unicode(self._values)
    
    def __str__(self):
        return self.__unicode__().encode('utf-8')
    
    def __repr__(self):
        return 'Row([' + ', '.join(repr(v) for v in self._values) + '])'
    
    def __eq__(self, o):
        try:
            return all(v1 == v2 for v1, v2 in izip_longest(self, o, fillvalue = NOT_DEFINED))
        except:
            return False
                
    def __getitem__(self, i):
        return self._values[self._variables.index(i)]    
            
    def __setitem__(self, i, value):
        variable = self._variables[i]
        value = variable.validate(value, variable.name)
        self._values[self._variables.index(variable)] = value
    
    def update(self, d):
        for var, value in d.iteritems():
            self[var] = value
            
    def __iter__(self):
        return iter(self._values)
    
    def get_map(self):
        return VariableMap(self._variables, self._values)