import cardsharp as cs
from random import randint
from cardsharp.test import assert_cs_raises
from cardsharp.errors import MergeError

def test_basic_merge():
    d1 = cs.Dataset('abc')
    d2 = cs.Dataset('afg')
    rows = cs.config.test_rows
    keys = [unichr(x) for x in xrange(rows)]
    orig_vals = [unichr(randint(0, 65535)) + unichr(randint(0, 65535)) for x in xrange(rows)]
    merge_vals = [unichr(randint(0, 65535)) + unichr(randint(0, 65535)) for x in xrange(rows)]
    d1_rows = [k + v for k, v in zip(keys, orig_vals)]
    d2_rows = [k + v for k, v in zip(keys, merge_vals)]
    expected_rows = [d1_row + m for d1_row, m in zip(d1_rows, merge_vals)]
    expected_rows.reverse()

    for row in d1_rows:
        d1.add_row(row)
    for row in d2_rows:
        d2.add_row(row)
    
    d1.merge(d2, 'a')
    
    for row, e_row in zip(d1, expected_rows):
        for r, e in zip(row, e_row):
            assert r == e

def test_merge_missing_keys():
    d1 = cs.Dataset('abc')
    d2 = cs.Dataset('abc')
    d3 = cs.Dataset('afg')
    d1.add_row('def')
    d1.add_row('hij')
    d2.add_row('def')
    d2.add_row('hij')
    d3.add_row('d12')
    d3.add_row('e34')
    
    d1.merge(d3, 'a', missing_keys = 'error')
    assert_cs_raises(MergeError, d1)
    
    d2.merge(d3, 'a', missing_keys = 'ignore')

def test_merge_extra_keys():
    d1 = cs.Dataset('abc')
    d2 = cs.Dataset('abc')
    d3 = cs.Dataset('abc')
    d4 = cs.Dataset('afg')
    d1.add_row('def')
    d1.add_row('hij')
    d2.add_row('def')
    d2.add_row('hij')
    d3.add_row('def')
    d3.add_row('hij')
    d4.add_row('d12')
    d4.add_row('h34')
    d4.add_row('e56')
    
    d1.merge(d4, 'a', extra_keys = 'error')
    assert_cs_raises(MergeError, d1)
    
    d2.merge(d4, 'a', extra_keys = 'ignore')
    
    d3.merge(d4, 'a', extra_keys = 'add')
    d3.wait()
    assert len(d3.rows) == 3
    
    