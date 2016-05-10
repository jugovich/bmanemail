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
from decimal import Decimal

__all__ = []

_rules = dict()

def rule(cls):
    r = cls()
    r.name = cls.__name__
    _rules[r.name] = r
    return cls

class Rule(object):
    def check_setting(self, value):
        raise RuleError('%r is an invalid setting for %s' % (value, self.name))
    
    def validate(self, setting, value):
        raise RuleError('%r is an invalid value for %s' % (value, self.name))
    
@rule
class length(Rule):
    """
        ..note: For utf-8 encoding remember to double your length and for utf-16 increase by 4x
    """
    def check_setting(self, value):
        if value is None:
            return None
        
        try:
            if value < 1:
                raise RuleError('%r is an invalid value for %s. Length must be a number greater than 0' % (value, self.name))
            return int(value)
        except:
            Rule.check_setting(self, value)
            
    def validate(self, setting, value):
        if setting is None or value is None:
            return
        
        try:
            if len(value) > setting:
                raise RuleError('%r is too long for %s (maximum length %s)' % (value, self.name, setting))
        except TypeError:
            from decimal import Decimal
            import datetime 
            from datetime import date, datetime, time
            if isinstance(value, (int, long)):
                if len(str(value)) > setting:
                    raise RuleError('%r is too long for %s (maximum length %s)' % (value, self.name, setting))
            elif isinstance(value, (Decimal, float)):
                from re import sub
                if len(str(sub('\.(?<=\.)\d*','',str(value)))) > setting:
                    raise RuleError('%r is too long for %s (maximum length %s)' % (value, self.name, setting))
            elif isinstance(value, (date, datetime, time, bool)):
                raise RuleError('Invalid format %s does not support Datetime, Date, Time, or Boolean formats' % self.name)
            else:
                raise
@rule
class scale(Rule):
    """Rule to enforce that the number of decimal place <= scale."""
    def check_setting(self, value):
        if value is None:
            return None
        
        try:
            assert(int(value) >= 0)
            return int(value)
        except:
            Rule.check_setting(self, value)
            
    def validate(self, setting, value):
        if setting is None or value is None:
            return
        
        
        if not isinstance(value, (Decimal, float)):
             raise RuleError('%s must be a float or Decimal not %s)' % (self.name, type(value)))
         
        from re import sub
        if len(sub('.*(?=\.)\.', '', str(value))) > setting:
            raise RuleError('%r is too long for %s (maximum number of decimals %s)' % (value, self.name, setting))

@rule
class precision(Rule):
    def check_setting(self, value):
        if value is None:
            return None
        
        try:
            assert(int(value) > 0)
            return int(value)
        except:
            Rule.check_setting(self, value)
            
    def validate(self, setting, value):
        """If value contains a decimal subtract 1 from value for . in value
        
        EX) If value = 1.2 THEN len(str(value)) = 3 but precision does not count period so we subtract 1
         
        """
        if setting is None or value is None:
            return
        
        from re import search
        l = len(str(value)) - 1 if search('\.', str(value)) else len(str(value))
            
        if l > setting:
            raise RuleError('%r is too long for %s (maximum number of digits %s)' % (value, self.name, setting))
    
@rule
class not_null(Rule):
    """Ensures that all values on variable are not equal to None"""
    def check_setting(self, value):
        if value is None:
            return None
        
        if value not in (True, False):
            Rule.check_setting(self, value)
            
        return value
            
    def validate(self, setting, value):
        if setting and not value:
            raise RuleError('NOT NULL rule violated. Value for %s is null' % self.name)
        else:
            return
       
class Rules(object):
    def __init__(self, **kw):
        self._settings = dict()
        self._variable_settings = None
        for name, value in kw.iteritems():
            self._assign(name, value)    

    def _get_data(self):
        var_settings = self._variable_settings
        if not var_settings:
            return None, None
        
        var = var_settings._variable
        if not var:
            return None, None
        
        set = var._set
        if not set:
             return var, None

        return var, set._data
        
    def _assign(self, name, value):
        rule = _rules.get(name)
        if not rule:
            raise CardsharpError('Unknown rule: %s' % name)
    
        value = rule.check_setting(value)
        self._settings[name] = value
        
        var, data = self._get_data()
        if data:
            def _func(row):
                rule.validate(value, row[var])
                
            data.add_task(_func, 'Validating %r (%r)' % (name, value))
            
    def iteritems(self):
        return self._settings.iteritems()
        
    def __getattr__(self, name):
        if name in _rules:
            return self._settings.get(name)
        
        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._assign(name, value)
            
    def validate(self, value):
        for rule, setting in self._settings.iteritems():
            _rules[rule].validate(setting, value)
            
    def copy(self):
        r = Rules()
        r._settings = dict(self._settings)
        return r