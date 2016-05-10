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

import ConfigParser, os

all = ['config', ]

class ConfigOption(object):
    def __init__(self, name, section = 'default', converter = None, default = None):
        self.name = name
        self.section = section
        self.converter = converter or (lambda x: x)
        self.default = default
        
        if section == 'default':
            self.attr_name = name
        else:
            self.attr_name = '%s_%s' % (section, name)
        
class Config(object):
    def __init__(self):
        object.__setattr__(self, '_config_options', dict())
        
        self._config_parser = ConfigParser.SafeConfigParser()
        self._config_parser.read(os.path.join(os.path.dirname(__file__),  'csharp.config'))
        
    def add_option(self, name, section = 'default', converter = None, default = None):
        option = ConfigOption(name = name, section = section, converter = converter, default = default)
        if option.attr_name in self._config_options:
            return
        
        self._config_options[option.attr_name] = option
        if hasattr(self, option.attr_name):
            value = getattr(self, option.attr_name)
        elif self._config_parser.has_option(option.section, option.name):
            value = self._config_parser.get(option.section, option.name)
        else:
            value = option.default
            
        if converter:
            value = converter(value)
        
        setattr(self, option.attr_name, value)
        
    def __setattr__(self, name, value):
        option = self._config_options.get(name)
        if option:
            value = option.converter(value)
            
        object.__setattr__(self, name, value)
        
def _bool(v):
    if isinstance(v, basestring):
        v = v.lower()
        
    return v not in ['false', 'no', 'f', '0', False]

config = Config()

config.add_option('overwrite', converter = _bool, default = False)
config.add_option('debug', converter = _bool, default = False) 
config.add_option('show_threaded_exceptions', converter = _bool, default = False)
            


    
