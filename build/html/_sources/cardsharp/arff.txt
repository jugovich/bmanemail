:mod:`arff` --- arff loader
============================

The arff handler was created for the ECT-584 final project to handle loading and saving files in the arff file format
used by weka. The arff handler was built into the cardsharp open source project. Cardsharp is a data manipulation library
for python that allows creation/loading of datasets, exposing these datasets to any python method/library of manipulating 
them, and then being able to save them in any format that cardsharp supports. This project used a strip down version of
cardsharp to decrease the number of steps required to setup on and run the final project.

For complete documentation of Cardsharp see http://cardsharp.norc.org/cardsharp/wiki/Home

Example of working with arff file:

To create a new dataset with 1 string variable and add 2 rows

>>> import cardsharp as cs
>>> dataset = cs.Dataset(['a'])
>>> dataset.add_row(['1'])
>>> dataset.add_row(['2'])
>>> for row in dataset:
>>>	  print row
[u'2']
[u'1']

To add an integer varaible to the end of the dataset and a nominal variable at index = 0

>>> dataset.variables.append(('b', 'integer'))
>>> dataset.variables.insert(0, ('c', 'nominal'))
>>> print dataset.variables
VariableSet([Variable('c', u'nominal'), Variable('a', u'string'), Variable('b', u'integer')])

Add some more data and save in arff format

>>> nom_map = {'c' : ['Yes', 'No']}
>>> for x in xrange(10):
>>> 	if x % 2 == 0:
>>>			dataset.add_row(['Yes', str(x), x])
>>>     else:
>>>			dataset.add_row(['No', str(x), x])
>>> dataset.save(filename = os.path.normpath(os.path.join( __file__, '..', 'samples', 'arff_demo')), 
>>>              format = 'arff', nominal_map = nom_map, dataset = 'demo') 

See the saved file here :download:`demo.arff </data/demo/demo.arff>`.

.. automodule:: cardsharp.loaders.arff
   :members:
   :undoc-members:
   
