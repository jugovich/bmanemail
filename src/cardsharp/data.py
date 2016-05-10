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

__all__ = ['Dataset', ]

from .variables import Variable, VariableSet, _c
from .rows import Rows
from .util import NOT_DEFINED, SafeIterationSet
from .tasks import Task, task_manager
from .errors import *
from .merge import merge as _merge, FieldCatalog, Catalog

_all_datasets = SafeIterationSet()

class Dataset(object):
    def __init__(self, variables):
        variables = VariableSet(variables)
        variables._data = self
        self._rows = Rows(self, variables)
        _all_datasets.add(self)
        
    @property
    def variables(self):
        if self._rows._voided:
            raise VoidDatasetError(self._rows._voided)

        return self._rows.variables
    
    def __getitem__(self, x):
        return self.variables.__getitem__(x)

    def __delitem__(self, x):
        return self.variables.__delitem__(x)

    def __setitem__(self, x, value):
        vars = self[x]
        if isinstance(vars, Variable):
            vars = [vars]
             
        def _func(row):
            for v in vars:
                row[v] = value
            
        self.add_task(_func, 'Assigning %r to %s' % (value, ', '.join(v.name for v in vars)))
        
    @property
    def rows(self):
        if self._rows._voided:
            raise VoidDatasetError(self._rows._voided)

        return self._rows
    
    def __iter__(self):
        return iter(self._rows)
        
    def add_row(self, values):
        self._rows.add_row(values)
    
    """Add x number of empty rows to the dataset where x = num_rows with num_rows being an integer value.
    
    >>> ds = cs.Dataset('abc')
    >>> ds.add_row('123')
    >>> len(ds.rows)
    1
    >>> ds.add_empty_rows(2)
    >>> len(ds.rows)
    3
    >>> for row in ds:
    >>>     print row + '.'
    [1,2,3]
    .
    .
    >>> ds.add_empty_rows(-1)
    Traceback (most recent call last):
      ...
    ValueError: num_rows must be greater than or equal to 0.
    """
    def add_empty_rows(self, num_rows):
        if num_rows < 0:
            raise ValueError('num_rows must be greater than or equal to 0.')
        for x in xrange(num_rows):
            self._rows.add_row([])
            
    def add_task(self, task, description = None):
        if hasattr(task, '__call__'):
            task = Task(task, description or task.__name__)
        elif task.mark is None:
            task = task.copy()
            if description:
                task.description = description
                
        if task.mark is None:
            task.mark = self._rows.create_mark(task.description)
            
        task_manager.add_task(task)
        
    def wait(self):
        self._rows.wait()
        
    def save(self, filename = NOT_DEFINED, dataset = NOT_DEFINED, format = NOT_DEFINED, **kw):
        _save(self, filename, dataset, format, **kw)

    def merge(self, source, key, missing_keys = 'ignore', extra_keys = 'ignore', unique_source = True, unique_target = False):
        if isinstance(key, Catalog):
            catalog = key
        else:
            catalog = FieldCatalog(VariableSet(key), source, unique_source = unique_source, unique_target = unique_target)

        _merge(source, self, catalog, missing_keys = missing_keys, extra_keys = extra_keys)
        
from .loaders import _save
