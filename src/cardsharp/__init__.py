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

__version__ = '0.8a1'

from threading import Thread as _Thread, Event as _Event
import sys as _sys
import atexit as _atexit
import time as _time

from .configuration import config

def _handle_exception(ex_type, ex_value, ex_tb):
    if config.show_threaded_exceptions:
        _sys.excepthook(ex_type, ex_value, ex_tb)
    
    for data in _all_datasets:
        try:
            rows = data.rows
            for mark in rows._marks:
                with mark.flag:
                    mark.flag.notify_all()
        except VoidDatasetError:
            continue
        
    
def _spawn_thread(name, target):
    def _target():
        try:
            target()
        except:
            _handle_exception(*_sys.exc_info())
            
    t = _Thread(target = _target, name = name)
    t.daemon = False
    t.start()

    return t

from .data import *
from .errors import *
from .variables import *
from .loaders import *
from .tasks import *
from .rules import *

from .data import _all_datasets

def wait():
    for data in _all_datasets:
        try:
            data.wait()
        except VoidDatasetError:
            pass

    _time.sleep(0.25)

_atexit.register(wait)