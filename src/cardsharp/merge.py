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

__all__ = ['Catalog', 'FieldCatalog', 'KeyGenerator', 'merge_catalog', 'create_catalog', 'merge']

from .variables import VariableSet, VariableMap
from .util import SafeIterationSet
from .errors import *
from .tasks import Task
from itertools import chain

class KeyGenerator(object):
    def __init__(self, fields, key_gen):
        self.fields = VariableSet(fields)
        self.key_gen = key_gen
        
    def __call__(self, row):
        return self.key_gen(row)
    
    def key_map(self, key):
        return VariableMap(self.fields, key)
    
class Catalog(object):
    def __init__(self, key_generator, cataloged_fields = (), unique_source = True, unique_target = False):
        self.generate_key = key_generator
        self._catalog = dict()
        self._matches = dict()
        self._unmatched = set()
        self.cataloged_fields = VariableSet(cataloged_fields)
        self._marks = SafeIterationSet()
        self.unique_source = unique_source
        self.unique_target = unique_target
        self.voided = False
        
    def key_map(self, key):
        return self.generate_key.key_map(key)
        
    def register(self, row):
        map = row.get_map()
        for f in map.keys():
            if f not in self.cataloged_fields:
                map.pop(f)
        
        key = self.generate_key(row)
        if self.unique_source and key in self._catalog:
            raise MergeError('Catalog key is not unique: %r' % key)
        
        self._catalog[key] = map
        self._matches[key] = 0
        self._unmatched.add(key)
        
    def match(self, key):
        row = self._catalog.get(key)
        if row:
            count = self._matches[key]
            if count and self.unique_target:
                raise MergeError('Target key is not unique: %r' % key)
            
            self._matches[key] = count + 1
            self._unmatched.discard(key)
            
        return row
    
    def has_unmatched(self):
        return len(self._unmatched) > 0
    
    def get_unmatched(self):
        key = self._unmatched.pop()
        return key, self._catalog[key]
    
    def wait(self):
        while self._marks:
            for m in self._marks:
                with m.flag:
                    if m.active:
                        m.flag.wait()
                    else:
                        self._marks.discard(m)
                        
    def finished(self):
        for m in self._marks:
            if m.active:
                return False
        
        return True
        
class FieldCatalog(Catalog):
    def __init__(self, fields, dataset, unique_source = True, unique_target = False):
        def key_gen(row):
            return tuple(row[f] for f in fields)
        
        Catalog.__init__(self, KeyGenerator(fields, key_gen), (v for v in dataset.variables if v.name not in fields), unique_source = unique_source, unique_target = unique_target)

def merge_catalog(data, catalog, missing_keys = 'error', extra_keys = 'ignore'):
    missing_keys = missing_keys.lower()
    if missing_keys not in ('error', 'ignore'):
        raise ValueError('Valid values for missing_keys are "error" and "ignore"')
        
    extra_keys = extra_keys.lower()
    if extra_keys not in ('error', 'ignore', 'add'):
        raise ValueError('Valid values for extra_keys are "error" and "ignore"')
        
    with data.rows._row_lock:
        data.variables.extend(catalog.cataloged_fields)
        m1 = data.rows.create_mark('Merging data')
        if extra_keys == 'add':
            m2 = data.rows.create_mark('Adding unmatched rows from catalog')
        
    class MergeTask(Task):
        def __init__(self):
            def func(row):
                if not catalog.finished():
                    raise TaskWaiting()
                
                if catalog.voided:
                    raise MergeError('Catalog has been voided')
                
                key = catalog.generate_key(row)
                match = catalog.match(key)
                if match:
                    row.update(match)
                elif missing_keys == 'error':
                    raise MergeError('Key %r in data missing from catalog' % key)

            Task.__init__(self, func, 'Merging data', m1)
            
        def __exit__(self, ex_type, ex_value, ex_tb):
            if ex_type:
                return
            
            if extra_keys == 'error':
                if catalog.has_unmatched():
                    raise MergeError('Unmatched key %r in catalog missing from data' % catalog.get_unmatched()[0])
    
    data.add_task(MergeTask())
    
    if extra_keys == 'add':
        def add_merge_rows():
            if m1.active:
                raise TaskWaiting()
            
            try:
                key, row_data = catalog.get_unmatched()
                row = m2.add_row()
                row.update(catalog.key_map(key))
                row.update(row_data)
            except KeyError:
                raise TaskFinished()
            
        data.add_task(Task(add_merge_rows, 'Adding unmatched merge rows', m2))

def create_catalog(data, catalog):
    mark = data.rows.create_mark('Cataloging')
    catalog._marks.add(mark)
    
    def task(row):
        try:
            catalog.register(row)
        except:
            catalog.voided = True
            raise
        
    data.add_task(Task(task, 'Cataloging', mark))

def merge(source, target, catalog, missing_keys = 'ignore', extra_keys = 'ignore'):
    create_catalog(source, catalog)
    merge_catalog(target, catalog, missing_keys = missing_keys, extra_keys = extra_keys)
    