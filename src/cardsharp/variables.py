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

__all__ = ['Variable', 'VariableSettings', 'VariableSet', 'VariableMap']

from .errors import *
from .format import lookup_format
from .rules import Rules, _rules
from .flags import Flags, _flags
from .convert import get_format_converter
from .tasks import Task
from .util import fill_variable_defaults

from functools import wraps
from itertools import izip

def _c(variable):
    if variable is None:
        return None
    elif isinstance(variable, Variable):
        return variable.name
    else:
        return variable.lower().strip()

class Variable(object):
    def __init__(self, name, format = None, **kw):
        if name is None:
            raise CardsharpError('Invalid variable name: %r' % name)
        
        self._name = _c(name)
        if format and isinstance(format, VariableSettings):
            self._settings = copy(format)
            if kw:
                raise CardsharpError('Unexpected keywords specified when passing settings object to Variable constructor')
        else:
            format = format or 'string'
            self._settings = VariableSettings(format = format, **kw)
        
        self._settings._variable = self
        self._set = None
        
    @property
    def name(self):
        return self._name
    
    @property
    def format(self):
        return self._settings.format
    
    @property
    def rules(self):
        return self._settings.rules
    
    @property
    def flags(self):
        return self._settings.flags
    
    @property
    def label(self):
        return self._settings.label
    
    @label.setter
    def label(self, value):
        self._settings.label = value
    
    @property
    def default(self):
        return self._settings.default
    
    @default.setter
    def default(self, value):
        self._settings.default = value
    
    def validate(self, value, name):
        value = self.format.validate(value, name)
        self._settings.rules.validate(value)
        return value
    
    def convert(self, format, *args, **kw):
        format = lookup_format(format)
        converter = get_format_converter(self.format, format)
        if converter is None:
            return
        
        self.convert_using(format, converter, *args, **kw)

    def convert_using(self, format, converter, *args, **kw):
        self._settings.format = lookup_format(format)

        if not self._set:
            return
        
        data = self._set._data
        if not data:
            return
        
        @wraps(converter)
        def _func(row):
            row[self] = converter(row[self], *args, **kw)
            
        data.add_task(Task(_func, 'Converting variable %s to %s' % (self.name, self.format.key)))
    
    def rename(self, name):
        if self._set:
            self._set.rename(self, name)
        else:
            self._name = name
    
    def __repr__(self):
        return 'Variable(%r, %r)' % (self._name, self._settings.format.key)
    
    def copy(self):
        c = Variable(self._name, self._settings.format)
        c._settings = self._settings.copy()
        c._settings._variable = c
        return c
      
class VariableSettings(object):
    def __init__(self, format, default = None, label = None, **kw):
        self.format = lookup_format(format)
        
        self._variable = None
        self.label = label
        self.default = default
        
        rules_kw, flags_kw = {}, {}
        
        for k, v in kw.iteritems():
            if k in _rules:
                rules_kw[k] = v
            if k in _flags:
                flags_kw[k] = v
        
        self.rules = Rules(**rules_kw)
        self.rules._variable_settings = self
        self.flags = Flags(**flags_kw)
        self.flags._variable_settings = self
        
    def copy(self):
        settings = VariableSettings(self.format)

        settings.label = self.label
        settings.default = self.default
        settings.rules = self.rules.copy()
        settings.rules._variable_settings = settings
        settings.flags = self.flags.copy()
        settings.flags._variable_settings = settings
        
        return settings
    
class VariableSet(object):
    def __init__(self, variables = ()):
        """
        Creates a collection of variables.
        
        >>> VariableSet([u'a', u'b', u'c'])
        VariableSet([Variable(u'a', u'string'), Variable(u'b', u'string'), Variable(u'c', u'string')])
        >>> VariableSet([(u'a', u'integer'), u'b', u'c'])
        VariableSet([Variable(u'a', u'integer'), Variable(u'b', u'string'), Variable(u'c', u'string')])
        >>> VariableSet([Variable(u'a', format = u'boolean'), u'b', u'c'])
        VariableSet([Variable(u'a', u'boolean'), Variable(u'b', u'string'), Variable(u'c', u'string')])
        >>> VariableSet([(u'a', u'x', u'y'), u'b', u'c'])
        Traceback (most recent call last):
            ...
        CardsharpError: Cannot use (u'a', u'x', u'y') in Variable listing
        >>> VariableSet([u'a', u'a', u'a'])
        Traceback (most recent call last):
            ...
        CardsharpError: Duplicate variable declaration: a
        """
        self._variables = []
        self._mapping = dict()
        for i, v in enumerate(variables):
            v = self._make_variable(v)
            
            if v.name in self._mapping:
                raise CardsharpError('Duplicate variable declaration: %s' % v.name)
            
            v._set = self
            self._variables.append(v)
            
            self._mapping[v] = v
            self._mapping[v.name] = v

        self._data = None
    
    def _make_variable(self, v):
        if isinstance(v, basestring):
            return Variable(v)
        
        if isinstance(v, Variable):
            return v.copy()
        
        try:
            if len(v) == 2:
                return Variable(v[0], v[1])
        except:
            pass
        
        raise CardsharpError('Cannot use %r in Variable listing' % (v, ))
    
    def copy(self):
        return VariableSet(self)
        
    def __len__(self):
        return len(self._variables)
    
    def _handle_slice(self, s):
        start, stop, step = s.start, s.stop, s.step
        if start != None:
            start = self.index(start)
            
        if stop != None:
            stop = self.index(stop)
        
        return self._variables[start:stop:step]
                    
    def __contains__(self, x):
        if isinstance(x, int):
            return 0 <= x < len(self)
        
        return _c(x) in self._mapping
        
    def __getitem__(self, x):
        if isinstance(x, int):
            return self._variables[x]
        elif isinstance(x, slice):
            return self._handle_slice(x)
        
        return self._mapping.get(x) or self._mapping[_c(x)]
    
    def __delitem__(self, x):
        vars = self[x]
        if isinstance(vars, Variable):
            vars = [vars]
            
        indices = [self.index(v) for v in vars]
        for v in vars:
            v._set = None
        
            del self._mapping[v]
            del self._mapping[v.name]
            self._variables.remove(v)
            
        if self._data:
            indices.sort()
            indices.reverse()
            def _func(row):
                for i in indices:
                    del row._values[i]
                
            if len(vars) == 1:
                description = 'Drop variable %s' % vars[0].name
            else:
                description = 'Drop variables: %s' % ', '.join(v.name for v in vars)
            
            self._data.add_task(Task(_func, description))
    
    def _add_vars(self, i, x):
        if i is None:
            i = len(self)
            
        vars = [self._make_variable(v) for v in x]
        new_vars = set()
        for v in vars:
            if v.name in self._mapping or v.name in new_vars:
                raise CardsharpError('Duplicate variable declaration: %s - %s' % v.name, v.format)
            
            new_vars.add(v.name)
            
        for v in reversed(vars):
            self._mapping[v] = v
            self._mapping[v.name] = v
            self._variables.insert(i, v)
            
        if self._data:
            values = [v.default for v in vars]
            def _func(row):
                row._values = row._values[:i] + values + row._values[i:]
            
            if len(vars) == 1:
                description = 'Add variable %s' % vars[0].name
            else:
                description = 'Add variables: %s' % ', '.join(v.name for v in vars)
                
            self._data.add_task(_func, description)
                                
    def append(self, x):
        self._add_vars(None, [x])
    
    def extend(self, x):
        self._add_vars(None, x)
    
    def insert(self, i, x):
        self._add_vars(i, [x])
    
    def index(self, x):
        return self._variables.index(self[x])
    
    def __iter__(self):
        return iter(self._variables)
    
    def __repr__(self):
        return 'VariableSet([' + ', '.join(repr(v) for v in self._variables) + '])'
    
    def rename(self, old_var, new_var):
        old_var = self[old_var]
        old_name = old_var.name
        new_name = _c(new_var)
        if new_name in self._mapping:
            raise CardsharpError('Cannot rename %s to %s: %s already exists on the dataset.' % (old_name, new_name, new_name))
        
        del self._mapping[old_name]
        old_var._name = new_name
        self._mapping[new_name] = old_var
        
    def drop(self, x):
        if isinstance(x, list):
            for var in x:
                self.__delitem__(var)
        else:
            self.__delitem__(x)

class VariableMap(object):
    def __init__(self, variables, values = ()):
        self._variables = VariableSet(variables)
        self._values = fill_variable_defaults(self._variables, values)
        
    def __len__(self):
        return len(self._variables)
    
    def __getitem__(self, x):
        return self._values[self._variables.index(x)]

    def __setitem__(self, x, value):
        var = self._variables[x]
        self._values[self._variables.index(var)] = var.validate(value)

    def __delitem__(self, x):
        index = self._variables.index(x)
        del self._values[index]
        del self._variables[index]
    
    def pop(self, x, default = None):
        if x in self:
            value = self[x]
            del self[x]
            return value
        else:
            return default
        
    def __contains__(self, x):
        return x in self._variables
    
    def __iter__(self):
        return iter(self._variables)
    
    def items(self):
        return list(self.iteritems())
    
    def iteritems(self):
        for var, value in izip(self._variables, self._values):
            yield var, value
            
    def keys(self):
        return list(self.iterkeys())
    
    def iterkeys(self):
        return iter(self._variables)
    
    def values(self):
        return list(self.itervalues())
    
    def itervalues(self):
        return iter(self._values)
    
    def get(self, x, default = None):
        if x in self:
            return self[x]
        else:
            return default
        
    def has_key(self, x):        
        return x in self
    
class VariableSpec(VariableSet):
    def __init__(self, variables):
        VariableSet.__init__(self, variables)
        self._keep = [True] * len(self)
        self._original = [v.name for v in self]

    def __delitem__(self, x):
        vars = self[x]
        if isinstance(vars, Variable):
            vars = [vars]
            
        indices = [self.index(v) for v in vars]
        indices.sort()
        indices.reverse() 
        VariableSet.__delitem__(self, x)
        for i in indices:
            del self._original[i]
            del self._keep[i]
        
    def _add_vars(self, i, x):
        total = len(x)
        VariableSet._add_vars(self, i, x)
        self._original = self._original[:i] + [v.name for v in self[i:(i + total)]] + self._original[i:]
        self._keep = self._keep[:i] + ([True] * total) + self._keep[i:]
    
    def original(self, x):
        return self._original[self.index(x)]
    
    def keep(self, x):
        return self._keep[self.index(x)]
    
    def filter(self, row = None):
        if row is None:
            row = self

        for keep, value in izip(self._keep, row):
            if keep:
                yield value
        
    def pair_filter(self, row):
        for keep, var, value in izip(self._keep, self, row):
            if keep:
                yield (var, value)
        
    def copy(self):
        return VariableSet(var for var, keep in izip(self, self._keep) if keep)
        
    def __repr__(self):
        return 'VariableSpec([' + ', '.join(repr(v) for v in self._variables) + '])'