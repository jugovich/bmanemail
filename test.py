import sys, os
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))
import cardsharp as cs
import subprocess
import re
from cardsharp.util import memoize

xwalk = cs.load(r'D:\workspace\CCHRRD\bjs_rules\rules\arrest\ancic\hi\crosswalk.txt', format = 'text', 
                var_names = ['key', 'vals'])
hi = cs.load(filename = r'P:\6684\Common\bjs\data\output\Review\Arrest\HI\round2\arrest_hi.sav', format = 'spss', limit = 50)
model = cs.Dataset(['chg', 'stat', 'achg'])
cs.wait()
statnum, chglit = {},{}

for index, row in enumerate(xwalk):
    key = row['key'].split('|')
    stat_key = re.sub('[, \']', '_', key[0])
    lit_key  = re.sub('[,\']', '_', key[1])
    lit_key = re.sub('\(attempted\)|\(conspiracy\)|\(accomplice\)', '', lit_key)
    if stat_key not in statnum:
        statnum[stat_key] = index
    for term in lit_key.split():
        if term not in chglit:
            chglit[term] = index

nom_map = {}
nom_map['p'] = []

for row in hi:
    lit = row['achglitx'].strip().lower() if row['achglitx'] else ''
    num = row['astatnumx'].strip().lower() if row['astatnumx'] else ''
    if str(row['achg']).replace('.0', '') not in nom_map['p']:
        nom_map['p'].append(str(row['achg']).replace('.0', ''))  
    model.add_row([lit, num, str(row['achg'])])
    
print len(chglit)
for v in statnum.iterkeys():
    model.variables.append(('s_%s' % v, 'integer'))

for v in chglit.iterkeys():
    model.variables.append(('c_%s' % v, 'integer'))
print len(statnum)

model.variables.append(('p', 'nominal'))

#@memoize
#def get_

for row in model:
    for var in model.variables:
        if var.name not in ['chg', 'stat', 'achg', 'p']:
            row[var.name] = 0
    if row['stat']:
        row['s_%s' % re.sub('[, \']', '_', row['stat'])] = 1
    
    lit_key  = re.sub('[,\']', '_', row['chg'])
    lit_key = re.sub('\(attempted\)|\(conspiracy\)|\(accomplice\)', '', lit_key)  

    for term in lit_key.split():
        row['c_%s' % re.sub('[,\']', '_', term)] = 1
        
    row['p'] = int(row['achg'].replace('.0', ''))

print 'before drop'
model.variables.drop('chg')
model.variables.drop('stat')
model.variables.drop('achg')

print 'before save'
cs.wait()
model.save(filename = r'd:\workspace\cchrrd\hi_model.arff', format = 'arff', dataset = 'hi', nominal_map = nom_map,
           overwrite = True)
cs.wait()

subprocess.call(['java', 'weka.classifiers.trees.J48', 
                     '-C', '0.25', 
                     '-M', '2',
                     '-t', r'd:\workspace\cchrrd\hi_model.arff', 
                     '-d', r'd:\workspace\cchrrd\model_t.model'])

#subprocess.call(['java', 'weka.classifiers.trees.J48', 
#                           '-p', len(model.variables), 
#                           '-T', test_file + '.arff', 
#                           '-l', model_file])