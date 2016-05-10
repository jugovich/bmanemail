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

from __future__ import unicode_literals, absolute_import

import cardsharp as cs
from cardsharp.test import construct_random_dataset, get_temp_file, construct_dataset, assert_raises, assert_cs_raises

def equality_filter(row):
    if row[0] == '1':
        return False
    else:
        return True

def test_equality_filter():
    ds = cs.Dataset('abc')
    d1 = cs.Dataset('abc')
    d2 = cs.Dataset('abc')
    ds.add_row('111')
    ds.add_row('222')
    ds.add_row('121')
    ds.add_row('333')
    ds.add_row('131')

    with get_temp_file('txt') as temp:
        ds.save(filename = temp.name, format = 'excel')
        cs.wait()
        d1 = cs.load(filename = temp.name, format = 'excel', filter = equality_filter)
        d2 = cs.load(filename = temp.name, format = 'excel')
        cs.wait()
        assert len(d1.rows) == 2
        assert len(d2.rows) == 5
    



