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

from ... import __version__ as API_VERSION

from .. import Loader, Saver, register, FileLoader, FileSaver, DatasetInfo, LOADING, SAVING
from .sevenzip import SevenZip

from .codec import search as _

from ...errors import *
from ...variables import Variable, _c, VariableSpec #, Range
from ...rules import Rules
from ...util import memoize
from ...format import lookup_format
from ..options import option, saves, loads

from decimal import Decimal
from distutils.version import StrictVersion
from itertools import izip
from contextlib import closing

import yaml, re, codecs, datetime, os

FILE_VERSION = '1.0'

_esc_map = {
    '\n' : 'n',
    '\t' : 't',
    '\r' : 'r',
    '\\' : '\\',
}

_unesc_map = dict([(v, k) for k, v in _esc_map.iteritems()])

_esc_in_str = re.compile(r'[\n\t\r\\]')

@memoize
def escape(s):
    """Escapes a string for saving.  This escapes whitespace characters (that is, \n, \t, and \r) and
    necessarily escapes \\ as well.
    
    >>> escape(None) is None
    True
    >>> escape('')
    u''
    >>> escape('This escapes:\\n\\ttabs (\\t),\\n\\tnewlines (\\n),\\n\\tand slashes (\\\\)')
    u'This escapes:\\\\n\\\\ttabs (\\\\t),\\\\n\\\\tnewlines (\\\\n),\\\\n\\\\tand slashes (\\\\\\\\)'
    """
    if not s:
        return s

    if _esc_in_str.search(s):
        def gen():
            for c in s:
                e = _esc_map.get(c)
                if e is None:
                    yield c
                else:
                    yield '\\'
                    yield e

        return ''.join(gen())

    return s

_unesc_in_str = re.compile(r'\\')

@memoize
def unescape(s):
    """Unescapes a string for loading.  This unescapes whitespace characters (that is, \n, \t, and \r) and
    necessarily unescapes \\ as well. Ignores \\  if at end of *s*. 
    
    >>> unescape('This unescapes: \\\\n, \\\\t, and \\\\r, \\\\, \\\\')
    u'This unescapes: \\n, \\t, and \\r, , \\\\'
    
    If *s* is None, False, or an empty string then return *s*.
    
    >>> unescape('')
    u''
    >>> if unescape(None) is None:
    ...     True
    True
    
    """
    if not s:
        return s

    if _unesc_in_str.search(s):
        def gen():
            in_escape = False
            for c in s:
                if in_escape:
                    yield _unesc_map.get(c, c)
                    in_escape = False
                elif c == '\\':
                    in_escape = True
                else:
                    yield c
                    
            if in_escape:
                yield '\\'

        return ''.join(gen())

    return s

_quote_re = re.compile(r'(^\s+|\s+$|[\'"])')

@memoize
def quote(s):
    """Quotes *s* for saving to csharp dataset. If *s* is None returns an empty string and 
    if *s* is an empty string returns a quoted string.
    
    >>> quote(None)
    u''
    >>> quote("")
    u"''"
    
    In order to preserve the integrity of the data quotes are added if *s* begins 
    with whitespace or ends with whitespace,

    >>> quote("   test")
    u"'   test'"
    >>> quote("test   ")
    u"'test   '"
    
    or contains at least one quote. It will also escape the quote character it uses.
    
    >>> quote('"test')
    u'\\'"test\\''
    >>> quote('"test"')
    u'\\'"test"\\''
    >>> quote("'test'")
    u'"\\'test\\'"'
    >>> quote("\\"A 'test'\\"")
    u'\\'"A \\\\\\'test\\\\\\'"\\''
    
    """
    if s is None:
        return ''

    if not s:
        return "''"

    if _quote_re.search(s):
        quote_char = '\''
        if "'" in s and not '"' in s:
            quote_char = '"'

        s = quote_char + s.replace(quote_char, '\\' + quote_char) + quote_char

    return s

@memoize
def unquote(s):
    """We unquote if the first character is a quote character and has a matching end quote. 
    If *s* is none then returns None. A :exc:`CardSharpError` is raised if no matching end is found.
    
    >>> unquote("'test\'")
    u'test'
    >>> unquote('\"test\"')
    u'test'
    >>> unquote('test')
    u'test'
    >>> unquote('\"test')
    Traceback (most recent call last):
            ...
    CardsharpError: Unmatched quotes - no end quote
    >>> unquote("'test")
    Traceback (most recent call last):
            ...
    CardsharpError: Unmatched quotes - no end quote
    >>> if unquote('') is None:
    ...     True
    True
    """
    if not s:
        return None
    
    if s[0] == "'":
        if s[-1] != "'":
            raise CardsharpError('Unmatched quotes - no end quote')
        else:
            return s[1:-1].replace(r"\'", "'")
    elif s[0] == '"':
        if s[-1] != '"':
            raise CardsharpError('Unmatched quotes - no end quote')
        else:
            return s[1:-1].replace(r'\"', '"')
    else:
        return s

def variable_representer(dumper, data):
    """Returns a mapping node based on *data* ???? with a tag of **tag:yaml.org,2002:map** 
    and the following subnodes: name and format (always), default (if not None), label and rules
    (if they exist in *data*). 
    
    """
    lines = [
        ('name', data.name),
        ('format', data.format.key),
    ]

    if data.default is not None:
        lines.append(('default', data.default))

    if data.label:
        lines.append(('label', data.label))

    if data.rules:
        lines.append(('rules', data.rules))

    return dumper.represent_mapping('tag:yaml.org,2002:map', lines)

def rules_representer(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', [(k, v) for k, v in data.iteritems()])

def decimal_representer(dumper, data):
    return dumper.represent_scalar('!d', data)

def decimal_constructor(loader, node):
    value = loader.construct_scalar(node)
    return Decimal(value)

def _yd(value):
    return yaml.dump(value, encoding = None, default_style = '"').strip()

def range_representer(dumper, data):
    comp_min = ' < ' if data.exclusive_min else ' <= '
    comp_max = ' < ' if data.exclusive_max else ' <= '

    if data.min is None:
        if data.max is None:
            return dumper.represent_scalar('!r', '(unbounded range)')
        else:
            return dumper.represent_scalar('!r', 'x' + comp_max + _yd(data.max))
    else:
        if data.max is None:
            return dumper.represent_scalar('!r', _yd(data.min) + comp_min + 'x')
        else:
            return dumper.represent_scalar('!r', _yd(data.min) + comp_min + 'x' + comp_max + _yd(data.max))

def _yl(value):
    return yaml.load(value)

#===============================================================================
# def range_constructor(loader, node):
#    value = loader.construct_scalar(node).strip()
#    m = re.match(r'^(?P<min>.+)\s+(?P<eq_min><=?)\s+x\s+(?P<eq_max><=?)\s+(?P<max>.+)$', value)
#    if m:
#        return Range(min = _yl(m.group('min')), max = _yl(m.group('max')), exclusive_min = m.group('eq_min') == '<', exclusive_max = m.group('eq_max') == '<')
#    m = re.match(r'^(?P<min>.+)\s+(?P<eq_min><=?)\s+x$', value)
#    if m:
#        return Range(min = _yl(m.group('min')), exclusive_min = m.group('eq_min') == '<')
#    m = re.match(r'^x\s+(?P<eq_max><=?)\s+(?P<max>.+)$', value)
#    if m:
#        return Range(max = _yl(m.group('max')), exclusive_max = m.group('eq_max') == '<')
#    assert value == '(unbounded range)'
#    return Range()
#===============================================================================

def set_representer(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data)

def unicode_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(Variable, variable_representer)
yaml.add_representer(Rules, rules_representer)
#yaml.add_representer(Range, range_representer)
yaml.add_representer(Decimal, decimal_representer)
yaml.add_representer(set, set_representer)
yaml.add_representer(unicode, unicode_representer)

yaml.add_constructor(u'!d', decimal_constructor)
#yaml.add_constructor(u'!r', range_constructor)

def _read_utf8(szip, dataset, filename):
    """Creates a utf8 read stream for loading *dataset* at *filename* using the csharp-data codec 
    defined in :class:`codec`.
    """
    stream = szip.extract(dataset + '\\' + filename)
    r = codecs.getreader('csharp-data')(stream)
    return r

def _write_utf8(szip, dataset, filename):
    """Creates a utf8 write stream for saving *dataset* at *filename* using the csharp-data codec 
    defined in :class:`codec`.
    """
    stream = szip.add(dataset + '\\' + filename)
    w = codecs.getwriter('csharp-data')(stream)
    return w

def read_variable_from_yaml(d):
    v = Variable(d['name'], lookup_format(d['format']))
    v.default = d.get('default')
    v.label = d.get('label')
    if 'rules' in d:
        for r, value in d['rules'].iteritems():
            setattr(v.rules, r, value)

    return v

def _conv_dt(pat, func):
    """ Creates the date conversion function...
    """
    pat = re.compile(pat)
    def _exec(value):
        m = pat.match(value)
        if m:
            return func(*(int(i) for i in m.groups()))
        else:
            raise LoadError('Unrecognized format: %r' % value)
        
    return _exec

_load_var_map = {
    'float' : lambda v: float(v),
    'date' : _conv_dt(r'^\s*(\d{4})/(\d{2})/(\d{2})\s*$', datetime.date),
    'datetime' : _conv_dt(r'^\s*(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})\s*$', datetime.datetime),
    'time' : _conv_dt(r'^\s*(\d{2}):(\d{2}):(\d{2})\s*$', datetime.time),
    'integer' : lambda v: int(v),
    'decimal' : lambda v: Decimal(v),
    'boolean' : lambda v: True if v in ('1', 'true', 'True') else False,
    'binary' : lambda v: bytes(v.decode('base64'))
}

for f in _load_var_map.keys():
    _load_var_map[f] = memoize(_load_var_map[f])

_load_var_map['string'] = lambda v: v

def load_var(v, value):
    """Loads *value* by first calling :func:unescape and :func:unquote on *value* and then performs a function
    from _load_var_map based on *v.format.key*. If *value* is an empty string then returns None.   
    
    >>> from cardsharp import Variable
    >>> v = Variable('x', 'float')
    >>> load_var(v, '1.23')
    1.23
    
    """
    f = v.format.key

    if value == '':
        return None

    return _load_var_map[f](unescape(unquote(value)))

_save_var_map = {
    'float' : lambda v: unicode(repr(v)),
    'date' : lambda v: '%04d/%02d/%02d' % (v.year, v.month, v.day),
    'datetime' : lambda v: '%04d/%02d/%02d %02d:%02d:%02d' % (v.year, v.month, v.day, v.hour, v.minute, v.second),
    'time' : lambda v: '%02d:%02d:%02d' % (v.hour, v.minute, v.second),
    'integer' : lambda v: unicode(v),
    'decimal' : lambda v: unicode(v),
    'boolean' : lambda v: '1' if v else '0',
    'binary' : lambda v: v.encode('base64'),
}

for f in _save_var_map.keys():
    _save_var_map[f] = memoize(_save_var_map[f])

_save_var_map['string'] = lambda v: v

def save_var(v, value):
    f = v.format.key

    if value is None:
        return ''

    return quote(escape(_save_var_map[f](value)))

def _split(s):
    return re.split('\t', s)

def _streamiter(f):
    buffer = None
    while True:
        next = f.read(1024 * 4)
        if next == '':
            if buffer:
                yield ''.join(buffer)
            return

        while next:
            m = re.match(r'(?s)^(.*?)\n(.*)$', next)
            if m:
                yield ''.join(buffer) + m.group(1) if buffer else m.group(1)
                buffer = None
                next = m.group(2)
            else:
                if not buffer:
                    buffer = []
                buffer.append(next)
                next = None

def _open_archive(options, mode = 'r'):
    return SevenZip(options['filename'], mode = mode)

@option(default = 'data')
def dataset(options):
    pass

@option(default = FILE_VERSION)
def version(options):
    if options['version'] != FILE_VERSION:
        raise OptionError('Unknown cardsharp version: %s' % FILE_VERSION)

class CardsharpHandler(FileLoader, FileSaver):
    id = ('cardsharp.loaders.cardsharp', 'cardsharp.loaders.csharp')
    formats = ('csharp', 'cardsharp')
    
    def list_datasets(self, options):
        with _open_archive(options) as _archive:
            files = _archive.list()
            return [f.path for f in files if f.filename == 'data.txt']

    def get_dataset_info(self, options):
        with _open_archive(options) as _archive:
            with _read_utf8(_archive, options['dataset'], 'info.txt') as in_stream:
                d = yaml.load(in_stream)
                if d is None:
                    raise LoadError('No dataset "%s" found in "%s" file.' % (options['dataset'], options['filename']))
    
            options['_cases'] = d['cases']
            options['_cardsharp_version'] = StrictVersion(d['api_version'])
            options['_cardsharp_data_hash'] = d['data_hash']
            options['_cardsharp_dict_hash'] = d['dict_hash']
            options['version'] = d['file_version']
            
            valid_hash = options['_cardsharp_dict_hash']
            with _read_utf8(_archive, options['dataset'], 'datadict.txt') as in_stream:
                variables = VariableSpec(read_variable_from_yaml(v_s) for v_s in yaml.load_all(in_stream))
    
            if valid_hash != in_stream.digest.hexdigest():
                raise LoadError('The hash of the dictionary does not match the calculated hash')
    
            options['_variables'] = variables
            options['format'] = 'csharp'

    def can_load(self, options):
        if options.get('format') == 'csharp':
            return 10000

        f = options.get('filename')
        if f and os.path.splitext(f)[1] == '.csharp':
            return 10000

        return 0

    class loader(Loader):
        def rows(self):
            opt = self.options
            with _open_archive(opt) as _archive:
                valid_hash = opt['_cardsharp_data_hash']
                with _read_utf8(_archive, opt['dataset'], 'data.txt') as in_stream:
                    f = _streamiter(in_stream)
                    mapping = tuple(_c(s) for s in _split(f.next()))
                    if mapping != tuple(opt['_variables'].original(v) for v in opt['_variables']):
                        raise LoadError('Invalid mapping in dataset: expected %r, got %r' % (mapping, (opt['_variables'].original(v) for v in opt['_variables'])))

                    f = opt['_filter'].filter(f)
                    for line in f:
                        row = _split(line)
                        yield (load_var(v, value) for v, value in opt['_variables'].pair_filter(row))

                if opt['_cases'] == self.loaded_rows and valid_hash != in_stream.digest.hexdigest():
                    raise LoadError('The hash of the data does not match the calculated hash')

    def can_save(self, options):
        if options.get('format') == 'csharp':
            return 10000

        return 0

    class saver(Saver):
        def rows(self):
            opt = self.options
            with _open_archive(opt, mode = 'w') as _archive:
                _archive.delete(opt['dataset'] + '\\datadict.txt')
                _archive.delete(opt['dataset'] + '\\data.txt')
                _archive.delete(opt['dataset'] + '\\info.txt')

                with _write_utf8(_archive, opt['dataset'], 'datadict.txt') as out:
                    yaml.dump_all(opt['_variables'].filter(), out, default_flow_style = False, encoding = None)

                datadict_hash = out.digest.hexdigest()
                try:
                    with _write_utf8(_archive, opt['dataset'], 'data.txt') as out:
                        out.write('\t'.join(v.name for v in opt['_variables'].filter()) + '\n')
                        
                        while True:
                            row = (yield)
                            out.write('\t'.join(save_var(v, value) for v, value in opt['_variables'].pair_filter(row)) + '\n')                   
                except (GeneratorExit, StopIteration):
                    pass

                data_hash = out.digest.hexdigest()
                with _write_utf8(_archive, opt['dataset'], 'info.txt') as out:
                    yaml.dump({
                        'cases' : self.saved_rows,
                        'api_version' : API_VERSION,
                        'file_version' : opt['version'],
                        'data_hash' : data_hash,
                        'dict_hash' : datadict_hash,
                    }, out, encoding = None, default_flow_style = False)

register(CardsharpHandler())