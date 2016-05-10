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

from .errors import *

__all__ = []

_flags = dict()

def flag(cls):
    f = cls()
    f.name = cls.__name__
    _flags[f.name] = f
    return cls

class Flag(object):
    """Set a Flag on a variable to handle special circumstances on loaders (loading/saving). 
    Same as rule but no validation on variable data."""
    def check_setting(self, value):
        raise FlagError('%r is an invalid setting for %s' % (value, self.name))
    
@flag
class string_width_override(Flag):
    """Use string_width_override to be able to set variable.rules.length > dataset.options.max_string_width."""
    def check_setting(self, value):
        if value is None:
            return None
        
        if value not in (True, False):
            Flag.check_setting(self, value)
            
        return value

@flag
class auto_inc(Flag):
    """Sets AUTO_INCREMENT flag on variable for MySQL loader. 
        *Note* If this flag is set the data contained in this variable can not contain values. 
    """
    def check_setting(self, value):
        if value is None:
            return None
        
        if value not in (True, False):
            Flag.check_setting(self, value)
            
        return value

@flag
class not_null(Flag):
    """Sets NOT NULL flag on variable for MySQL loader."""
    def check_setting(self, value):
        if value is None:
            return None
        
        if value not in (True, False):
            Flag.check_setting(self, value)
            
        return value

@flag
class primary_key(Flag):
    """Sets PRIMARY KEY flag on variable for MySQL loader
        WHERE value = constraint name"""
    def check_setting(self, value):
        if value is None:
            return None
        
        if not isinstance(value, (unicode, str)):
            Flag.check_setting(self, value)
            
        return value

@flag
class unique(Flag):
    """Sets UNIQUE flag on variable for MySQL loader
        WHERE value = constraint name"""
    def check_setting(self, value):
        if value is None:
            return None
        
        if not isinstance(value, (unicode, str)):
            Flag.check_setting(self, value)
            
        return value
    
@flag
class foreign_key(Flag):
    """Sets FOREIGN KEY flag on variable for MySQL loader 
    with value = list or tuple 
    where first value is a string = foreign key constraint name
    and second value is a string = references column ie. 'TABLENAME(TABLECOLUMN)"""
    def check_setting(self, value):
        if value is None:
            return None
        
        if not isinstance(value, (tuple, list)) and not isinstance(value[0], (unicode, str)) and not isinstance(value[1], (unicode, str)):
            Flag.check_setting(self, value)
            
        return value 
        
class Flags(object):
    def __init__(self, **kw):
        self._settings = dict()
        self._variable_settings = None
        for name, value in kw.iteritems():
            self._assign(name, value)    
    
    
    def _assign(self, name, value):
        flag = _flags.get(name)
        if not flag:
            raise CardsharpError('Unknown flag: %s' % name)
    
        value = flag.check_setting(value)
        self._settings[name] = value
            
    def iteritems(self):
        return self._settings.iteritems()
        
    def __getattr__(self, name):
        if name in _flags:
            return self._settings.get(name)
        
        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._assign(name, value)
        
    def copy(self):
        f = Flags()
        f._settings = dict(self._settings)
        return f