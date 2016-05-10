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

__all__ = [str(s) for s in ('register', 'unregister', 'FileHandler', 'FileLoader', 'FileSaver', 
                            'list_datasets', 'get_info', 'load', 'Loader', 'Saver', 'drop', )]

LOADING = 'loading'
SAVING = 'saving'

from .. import _spawn_thread, config
from .options import get_options, INITIAL_STAGE, VARIABLES_STAGE
from ..errors import *
from ..util import as_tuple, NOT_DEFINED
from ..format import lookup_format
from ..variables import VariableSpec
from ..data import Dataset
from .filter import RowFilter

from collections import defaultdict
from threading import Lock
from itertools import imap
from abc import ABCMeta, abstractmethod, abstractproperty

import sys

_load_handlers, _save_handlers = dict(), dict()
def register(handler):
    for id in handler.id:
        if isinstance(handler, FileLoader):
            _load_handlers[id] = handler

        if isinstance(handler, FileSaver):
            _save_handlers[id] = handler

def unregister(handler):
    if isinstance(handler, basestring):
        _load_handlers.pop(handler, None)
        _save_handlers.pop(handler, None)
    else:
        for id in handler.id:
            if isinstance(handler, FileLoader):
                h = _load_handlers.get(id, None)
                if h is handler:
                    del _load_handlers[id]

            if isinstance(handler, FileSaver):
                h = _save_handlers.get(id, None)
                if h is handler:
                    del _save_handlers[id]

class FileHandler(object):
    __metaclass__ = ABCMeta

    id = None
    name = None

    def __init__(self):
        """Creates any missing :attr:`id` or :attr:`name` fields.

        >>> class DefaultHandler(FileHandler):
        ...     def list_datasets(self, options):
        ...         pass
        ...
        >>> class HandlerA(DefaultHandler):
        ...     name = 'A'
        ...     id = 'A'
        ...
        >>> class HandlerB(DefaultHandler):
        ...     id = ('b', 'c')
        ...
        >>> class HandlerNone(DefaultHandler):
        ...     id = None
        ...     name = None
        ...
        >>> HandlerA().id, HandlerA().name
        ((u'a',), u'A')
        >>> HandlerB().id, HandlerB().name
        ((u'b', u'c'), u'HandlerB')
        >>> HandlerNone().id, HandlerNone().name
        ((u'cardsharp.loaders.handlernone',), u'HandlerNone')
        >>> DefaultHandler().id, DefaultHandler().name
        ((u'cardsharp.loaders.defaulthandler',), u'DefaultHandler')
        """
        super(FileHandler, self).__init__()

        self.id = as_tuple(self.id, if_none = None)

        if not self.id:
            class_name = ('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
            self.id = (class_name, )

        self.id = tuple(unicode(s).lower() for s in self.id)

        if not self.name:
            self.name = self.__class__.__name__

        self.name = unicode(self.name)
        
    def process_options(self, mode, stage, kw):
        if stage is None:
            kw = self.process_options(mode, INITIAL_STAGE, kw)
            if '_variables' not in kw:
                self.get_dataset_info(kw)
                
            kw = self.process_options(mode, VARIABLES_STAGE, kw)
            return kw
        
        if '_filter' not in kw:
            kw['_filter'] = RowFilter()
                
        options = get_options(self.__module__, mode)
        option_names = set(k for k in kw.iterkeys() if not k.startswith('_'))
        for option in options:
            option_names.discard(option.name)
            if option.stage == stage:
                option(kw)

        if option_names:
            raise OptionError('Unknown option: %s' % next(iter(option_names)))
                
        return kw
        
class FileLoader(FileHandler):
    """Defines the interface required to save different file formats for *Cardsharp*.

    :meth:`list_datasets`, :meth:`get_dataset_info`, :meth:`can_load`, and :meth:`loader`
     are required to load files.
    """

    err = LoadError

    def __init__(self):
        super(FileLoader, self).__init__()

    @abstractmethod
    def list_datasets(self, options):
        pass
    
    @abstractmethod
    def get_dataset_info(self, options):
        pass

    @abstractmethod
    def can_load(self, options):
        pass

    @abstractmethod
    def loader(self, info, options):
        pass

class FileSaver(FileHandler):
    """Defines the interface required to save different file formats for *Cardsharp*.

    :meth:`can_save`, and :meth:`saver` are required to save files.
    """

    err = SaveError

    def __init__(self):
        super(FileSaver, self).__init__()

    @abstractmethod
    def can_save(self, options):
        pass

    @abstractmethod
    def saver(data, options):
        pass
    
def _find_suitability(certainty, priority = None):
    """Return an integer rating the suitability of the handler.
    The *certainty* is either an integer (in which case it is returned unchanged) or a mapping.
    If it is a mapping, *priority* is used as a key to locate the suitability.  If the *priority* is
    not in the mapping ``None`` is used as a fall-back, and if ``None`` is not a key then ``0`` is
    returned.

    >>> cert = { 'speed' : 100 }
    >>> _find_suitability(cert, 'speed')
    100
    >>> _find_suitability(cert, 'accuracy')
    0
    >>> cert[None] = 50
    >>> _find_suitability(cert, 'accuracy')
    50
    """

    try:
        return certainty.get(priority, certainty.get(None, 0))
    except AttributeError:
        return certainty

def _handler_key((suit, handler)):
    """Provides a sort key for a tuple (*suitability*, :class:`FileHandler`).
    Keys are ranked by *suitability* (in reverse order), with ties broken by the first id.

    >>> class Handler(object):
    ...     def __init__(self, id):
    ...         self.id = id
    ...
    ...     def __repr__(self):
    ...         return 'Handler(%r)' % self.id
    ...
    >>> handlers = [(10, Handler(u'c')), (40, Handler(u'b')), (10, Handler(u'a'))]
    >>> map(_handler_key, handlers)
    [(-10, u'c'), (-40, u'b'), (-10, u'a')]
    >>> sorted(handlers, key = _handler_key)
    [(40, Handler(u'b')), (10, Handler(u'a')), (10, Handler(u'c'))]
    """
    return (-suit, handler.id[0])

def find_load_handler(priority = None, **kw):
    return _find_handler(LOADING, priority = priority, **kw)

def find_save_handler(priority = None, **kw):
    return _find_handler(SAVING, priority = priority, **kw)

def _find_handler(mode, handler = None, format = None, priority = None, all = False, **kw):
    if mode == LOADING:
        _handlers = _load_handlers
    elif mode == SAVING:
        _handlers = _save_handlers
        if handler is None and format is None:
            raise OptionError('You must specify a format (or a handler) to save the the dataset')
    else:
        raise TypeError('Unknown mode: %r' % mode)

    if handler:
        try:
            return _handlers[handler]
        except KeyError:
            raise LoaderError('Unknown handler: %s' % handler)

    if format:
        kw['format'] = format        
        _handlers = set(h for h in _handlers.itervalues() if format in h.formats)
        if not _handlers:
            raise LoaderError('Unknown format: %s' % format)
    else:
        _handlers = set(_handlers.itervalues())
        
    handlers, errors = set(), set()
    for handler in _handlers:
        _can = handler.can_load if mode == LOADING else handler.can_save
        try:
            options = handler.process_options(mode, INITIAL_STAGE, kw = dict(kw))
            handlers.add((_find_suitability(_can(options), priority), handler))
        except LoaderError as e:
            errors.add(str(e))

    handlers = [(c, h) for c, h in handlers if c]
    if not handlers:
        if mode == LOADING:
            _err, _str = LoadError, 'Cannot determine the format of the data'
        else:
            _err, _str = SaveError, 'Cannot find a handler for format %s' % kw['format']

        if errors:
            if len(errors) == 1:
                _str += ': %s' % next(iter(errors))
            else:
                _str += ' (possible reasons: %s)' % ', '.join(repr(e) for e in errors)

        raise _err(_str)

    handlers.sort(key = _handler_key)
    if all:
        return handlers
    else:
        return handlers[0][1]

def list_datasets(filename = NOT_DEFINED, **kw):
    if filename != NOT_DEFINED:
        kw[b'filename'] = filename
    
    handler = find_load_handler(**kw)
    options = handler.process_options(LOADING, INITIAL_STAGE, kw = kw)
    return handler.list_datasets(options)

def get_info(filename = NOT_DEFINED, dataset = NOT_DEFINED, **kw):
    if filename != NOT_DEFINED:
        kw[b'filename'] = filename
    
    if dataset != NOT_DEFINED:
        kw[b'dataset'] = dataset
    
    handler = find_load_handler(**kw)
    options = handler.process_options(LOADING, INITIAL_STAGE, kw = kw)
    handler.get_dataset_info(options)
    
    return DatasetInfo(options['_variables'], options.get('version'), options.get('_cases'), options['format'])

def drop(filename = NOT_DEFINED, dataset = NOT_DEFINED, **kw):
    if filename != NOT_DEFINED:
        kw[b'filename'] = filename
    
    if dataset != NOT_DEFINED:
        kw[b'dataset'] = dataset
    
    """Not sure how to handle drop on formats other than MySQL. Should we
    give the user the ability to delete an existing dataset. Normally overwrite could be set
    on save, but for MySQL when you need to drop tables in a specific order to ensure now
    ref errors it does not make sense to load all the datasets and then save."""
    if kw['format'].lower() != 'mysql':
        raise DropError('Can not drop dataset on format other than MySQL')
    
    handler = find_load_handler(**kw)
    options = handler.process_options(LOADING, INITIAL_STAGE, kw = kw)
    handler.drop(options)

def load(filename = NOT_DEFINED, dataset = NOT_DEFINED, **kw):
    if filename != NOT_DEFINED:
        kw[b'filename'] = filename
    
    if dataset != NOT_DEFINED:
        kw[b'dataset'] = dataset
    
    handler = find_load_handler(**kw)
    options = handler.process_options(LOADING, stage = None, kw = kw)
    loader = handler.loader(options)
    
    data = Dataset(options['_variables'].filter())
    data._loaded = False
    loader._mark = data.rows.create_mark('Loading')
    def _exec():
        with loader._mark as m:
            try:
                filter = options['filter']
                for row in loader.rows():
                    row = m._create_row(row)
                    if filter(row):
                        m._add_row(row)
                        loader.loaded_rows += 1
            except:
                m.void()
                raise
            
    _spawn_thread('Loading Thread', _exec)
    return data

def _save(data, filename = NOT_DEFINED, dataset = NOT_DEFINED, format = NOT_DEFINED, **kw):
    if format == NOT_DEFINED and dataset != NOT_DEFINED:
        format, dataset = dataset, NOT_DEFINED
    
    if format != NOT_DEFINED:
        kw[b'format'] = format
        
    if filename != NOT_DEFINED:
        kw[b'filename'] = filename
    
    if dataset != NOT_DEFINED:
        kw[b'dataset'] = dataset
    
    handler = find_save_handler(**kw)
    kw['_variables'] = VariableSpec(data.variables)
    opt = handler.process_options(SAVING, stage = None, kw = kw)
    saver = handler.saver(opt)
    saver._mark = data.rows.create_mark('Saving')

    def _exec():
        if opt.get('create_dir') and opt.get('filename'):
            dir_name = os.path.dirname(opt['filename'])
            if os.path.exists(dir_name):
                if os.path.isfile(dir_name):
                    raise SaveError('Parent directory %s can not be created' % dir_name)
            else:
                os.makedirs(dir_name)

        with saver._mark as m:
            try:
                save_iter = saver.rows()
                save_iter.next()
    
                for keep in opt['_filter']:
                    m.advance()
                    
                    while not opt['filter'](m.current_row):
                        m.advance()
                        
                    if keep:
                        save_iter.send(m.current_row)
                        saver.saved_rows += 1
        
            except NoMoreRowsError:
                pass
            except:
                m.void()
                raise

        save_iter.close()
        
    _spawn_thread('Saving Thread', _exec)
        
class DatasetInfo(object):
    def __init__(self, variables, version = None, cases = None, format = None):
        self.format = format
        self.variables = VariableSpec(variables)
        self.version = version
        self.cases = cases

    def __unicode__(self):
        format = self.format or 'Unknown'
        version = self.version or 'Unknown'
        cases = 'Unknown' if self.cases is None else self.cases
        return 'DatasetInfo (format %s (version %s), cases %s)' % (format, version, cases)

    def __str__(self):
        return self.__unicode__().encode('utf-8')

class Loader(object):
    __metaclass__ = ABCMeta

    def __init__(self, options):
        self.options = options
        self.loaded_rows = 0

    @abstractmethod
    def rows(self):
        pass

class Saver(object):
    __metaclass__ = ABCMeta

    def __init__(self, options):
        self.options = options
        self.saved_rows = 0

    @abstractmethod
    def rows(self):
        pass

for m in ('csharp', 'excel', 'text', 'csv',  'spss', 'sas', 'arff'):
    name = __name__ + '.' + m
    try:
        __import__(name, globals(), locals(), [], 0)
    except (ImportError, ), e:
        if config.debug:
            raise e
    except:
        if config.debug:
            raise