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

import traceback as _traceback

class CardsharpError(Exception):
    pass

class MergeError(CardsharpError):
    pass

class RuleError(CardsharpError):
    pass

class FlagError(CardsharpError):
    pass

class VoidDatasetError(CardsharpError):
    def __init__(self, exc_info):
        tb = ''.join(_traceback.format_exception(*exc_info))
        CardsharpError.__init__(self, 'Nested exception: ' + tb)
        self._exc_info = exc_info
        
    def exc_info(self):
        return self._exc_info

class FormatError(CardsharpError):
    pass

class LoaderError(CardsharpError):
    pass

class OptionError(LoaderError):
    pass

class DropError(LoaderError):
    pass

class LoadError(LoaderError):
    pass

class SaveError(LoaderError):
    pass

class TaskFinished(CardsharpError):
    pass

class TaskWaiting(CardsharpError):
    pass

class NoMoreRowsError(TaskFinished):
    pass

class MarkInactiveError(CardsharpError):
    pass

class DataError(CardsharpError):
    pass

class StateError(DataError):
    pass

class BookError(DataError):
    pass