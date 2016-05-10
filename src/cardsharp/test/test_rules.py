import cardsharp as cs
from cardsharp.test import construct_random_dataset, get_temp_file, construct_dataset, assert_raises, assert_cs_raises
from cardsharp.errors import RuleError

def test_length():
    ds = construct_random_dataset(rows = 1)
    
    ds1 = cs.Dataset(['s',])
    t = ''
    
    for x in xrange(1000):
        t += u"\u0411".encode('utf-16')
    
    print len('\xff')
    print len('\xff'.encode('utf-8'))
    print len(t)
    ds1.add_row([t,])
    ds1['s'].rules.length = 1000
    
#    ds['a'].rules.length = 1000
#    ds['b'].rules.length = 1000
#    ds['c'].rules.length = 1000
#    ds['d'].rules.length = 1000
#    ds['e'].rules.length = 1000
#    assert_cs_raises(RuleError, ds)
    