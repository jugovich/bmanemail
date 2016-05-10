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

from cardsharp.test import random_caps, assert_raises, assert_almost_equal
import datetime
from decimal import Decimal
from cardsharp import format
from cardsharp.errors import FormatError

defaults = {
    str : 'x',
    unicode : u'x',
    int : 1,
    bool : True,
    float : 1.1,
    Decimal : Decimal('1.1'),
    long : 1L,
    datetime.date : datetime.date(2000, 1, 1),
    datetime.time : datetime.time(12, 0, 0),
    datetime.datetime : datetime.datetime(2009, 12, 12),
}

mapping = dict()
for f in (format.STRING, format.INTEGER, format.DECIMAL, format.FLOAT, format.DATETIME, format.DATE, format.TIME, format.BOOLEAN, format.BINARY):
    m = mapping[f] = dict(key = f.key)
    d = m['tests'] = dict()
    for t, s in defaults.iteritems():
        d[t] = dict(
            sample = s,
            maps_to = False,
            validate = False,
            change_type = True,
        )

mapping[format.STRING]['tests'][str].update({ 'maps_to' : True, 'validate' : True })
mapping[format.STRING]['tests'][unicode].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.BINARY]['tests'][str].update({ 'validate' : True, 'change_type' : False })
mapping[format.INTEGER]['tests'][int].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.INTEGER]['tests'][long].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.DECIMAL]['tests'][int].update({ 'validate' : True })
mapping[format.DECIMAL]['tests'][long].update({ 'validate' : True })
mapping[format.DECIMAL]['tests'][Decimal].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.FLOAT]['tests'][int].update({ 'validate' : True })
mapping[format.FLOAT]['tests'][long].update({ 'validate' : True })
mapping[format.FLOAT]['tests'][Decimal].update({ 'validate' : True })
mapping[format.FLOAT]['tests'][float].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.BOOLEAN]['tests'][bool].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.DATETIME]['tests'][datetime.datetime].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.DATE]['tests'][datetime.date].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })
mapping[format.TIME]['tests'][datetime.time].update({ 'maps_to' : True, 'validate' : True, 'change_type' : False })

def iter_mapping(formats_only = False):
    for f, m in mapping.iteritems():
        if formats_only:
            yield dict(format = f, key = m['key'])
            continue

        for t, info in m['tests'].iteritems():
            d = dict(format = f, key = m['key'], type = t)
            d.update(info)
            yield d

def test_string_mapping():
    for t in iter_mapping(formats_only = True):
        k = random_caps(t['key'])
        assert t['format'] == format.lookup_format(k)

def test_type_mapping():
    for t in iter_mapping():
        if t['maps_to']:
            assert t['format'] == format.lookup_format(t['type']), 'Format lookup for %r got %r (expected %r)' % (t['type'], format.lookup_format(t['type']), t['format'])
        else:
            assert t['format'] != format.lookup_format(t['type']), 'Format lookup for %r got %r (didn\'t expect %r)' % (t['type'], format.lookup_format(t['type']), t['format'])

def test_check_missing_format():
    assert_raises(KeyError, format.lookup_format, 'x')
    assert_raises(KeyError, format.lookup_format, None)

def test_create_format():
    assert_raises(KeyError, format.Format, 'x')
    assert_raises(ValueError, format.Format, 'integer', (int, ))

def test_validate_equality():
    for t in iter_mapping():
        if t['validate']:
            v1 = t['sample']
            v2 = t['format'].validate(t['sample'])
            if isinstance(v1, float) or isinstance(v2, float):
                assert_almost_equal(float(v1), float(v2), 10, '%r validation for %r returned %r' % (t['format'], t['sample'], t['format'].validate(t['sample'])))
            else:
                assert v1 == v2, '%r validation for %r returned %r' % (t['format'], t['sample'], t['format'].validate(t['sample']))

def test_validate_fail():
    for t in iter_mapping():
        if not t['validate']:
            assert_raises(FormatError, t['format'].validate, t['sample'])

def test_validate_type_equality():
    for t in iter_mapping():
        if t['validate']:
            if t['change_type']:
                assert repr(t['sample']) != repr(t['format'].validate(t['sample'])), '%r validation for %r returned %r' % (t['format'], t['sample'], t['format'].validate(t['sample']))
            else:
                assert repr(t['sample']) == repr(t['format'].validate(t['sample'])), '%r validation for %r returned %r' % (t['format'], t['sample'], t['format'].validate(t['sample']))
