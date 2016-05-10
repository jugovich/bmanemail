from re import search, sub, S
import os, sys
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))
import cardsharp as cs
from itertools import izip

#format map for cardsharp file filenames and extensions to be used to save() and load()
_format_info = {
         'sas' : '.sas7bdat',
        'text' : '.txt',
       'excel' : '.xls',
        'spss' : '.sav',
      'csharp' : '.csharp',
         'csv' : '.csv',
       'mysql' : '.mysql',
    'sas7bdat' : '.sas7bdat',
         'txt' : '.txt',
         'xls' : '.xls',
         'sav' : '.sav',
      'csharp' : '.csharp',
         'csv' : '.csv',
       'mysql' : '.mysql',
       'del'   : '.del',
       'arff'  : '.arff',
}

def remove_stop_words(text):
    '''Helper function to remove stop words present in the data. Stop word list was created by manual review
    of all terms present in the data. This term list with frequencies of term in data was created by running  
    pp.review_terms().  
    '''
    #make stop word list
    stop = '|'.join(['the', 'to', 'and', 'of', 'a', 'you', 'is', 'or', 'i', 'on', 'be', 'your', 'that', 'are',
                     'with', '-', 'will', 'have', 'as', '&amp;', 'all', 'list', 'from', 'by', 'our', 
                     'mailing', 'not', 'an', 'so', 'but', 'in', 'it', 'because', 'had', 'you', 'hey', 'we',
                     'hi', 'hello', 'greetings', 'dear', 'can', 'thanks', 'if', '--+', '\*+',
                     'me', 'has', 'was', 'would', 'who', 'unsubscribe', 'up', '@burningman.com', 'burningman',
                     'for', 'this', 'does', 'can', 'com', 'man', 'burning'])
    
    #add space so first word is reviewed for potential removal
    text = ' ' + text
    
    #return variable text with all stop words removed
    return sub('(?<= )(' + stop + ')(?= )', ' ', text)


class bmine(object):
    """Class to house dataset processing modules for activities related to Burning Man )( data mining."""
    def __init__(self, data_dir, save_dir, **kw):
        """Takes a data directory and save directory (for loading/saving) and a list of keywords."""
        self.data_dir       = data_dir
        self.save_dir       = save_dir
        self.email_vars     = ['path', 'list-name', 'list_tag', 'subject', 'from', 'to', 'time', 'sender', 'date', 'cc', 'body']
        self.extract_err_c  = 0
        self.subject_reg    = {}
        self.list_name      = None
        self.dataset        = None                
        
    def _add_body(self, vars, body, body_count):
        """Helper function to break up body into 1000 character chunks to make review in excel possible."""
        vars.append(body[0:1000])
        body = body[1000:]
        
        if len(self.dataset.variables) < len(vars):
            self.dataset.variables.append('body_%s' % body_count)
        if len(body) > 0:
            self._addBody(vars, body, body_count+1)

    def _addListInfo(self, list_name, vars):
        """Helper function to identify list tags on the subject body."""
        s = search('\[.*?\]|%s' % list_name, vars[3])
        if s:
            vars[2] = s.group() if s.group() else None
        vars[1] = list_name
    
    def load(self, fn, fmt):
        """This module takes a filename and format and then using these arguements loads a dataset at self.data_dir."""
        self.dataset = cs.load(filename = os.path.join(self.data_dir, fn + _format_info[fmt]), format = fmt)
        cs.wait()
        
    def extract(self, path, l_n, **kw):
        """This module extracts email information. The module requires a *path* to the email file and a list_name *l_n*
        for the name of the list server that the email was extracted from. """
        
        #If a dataset has not already been created, create one using the email_vars variable list
        if not self.dataset:
            self.dataset = cs.Dataset(self.email_vars)
        
        #declare variables
        self.list_name = l_n
        b_c = 1
        
        #create regex strings for non-essential data removal
        style       = '<style.+?</style>' 
        unsubscribe = 'to unsubscribe from this list,.*'
        list_tag    = '%s|%s@burningman.com' % (self.list_name, self.list_name)
        email_meta  = ','.join(['https://lists.burningman.com/mailman/listinfo/',
                                '@burningman.com', 'list::', 'http://bostonburners.org',
                                'http://chaoshacker.org/mailman/listinfo/burners', 
                                'unsubscribe', '\++']) 
        
        #load the email and extract information
        with open(path, 'rb') as f:
            #load email
            data = f.read()
            data = data.lower() if data.lower() else ''
            vars = []
            body = ''
            #add path id
            vars.append(str(path))
            
            #loop over and extract the to, from, date, time, sender, subjecct information
            for var in self.email_vars[1:len(self.email_vars) - 1]:
                m = search('<tr><td><b>%s:[ ]*</b>(.*?)</td>' % var, data, flags = S)
                if m:
                    #replace html with characters
                    m = m.groups()[0].replace('&gt;', '>')
                    m = m.replace('&lt;', '<')
                    m = m.replace('&quot;', '"')
                    m = m.replace('&#39;', '\'')
                else:
                    m = None
                    
                vars.append(m)

            #remove new lines
            data = sub('\r|\n', ' ', data)
            #extract body
            match = search('</td>[ ]*</tr>[ ]*</table>[ ]*<br>(?P<b>.*?)</body>[ ]*</html>', data, flags = S)
            if match:
                self.orig_body = match.groupdict()['b'].strip()
                #remove css style info, all the unsubscribe info, html tags, list tags
                #and some special characters causing unicode decode errors
                body = sub('<.+?>|%s|%s|%s|%s' % (style, unsubscribe, list_tag, email_meta), 
                                                        ' ', self.orig_body)
                body = sub('\xe2\x80\x9c|\xe2\x80\x9d|\xe2\x80\x99', '\'', body)
                #if re: in subject remove orginial message
                if 're:' in vars[3]:          
                    body = sub('|'.join(['from: .+? to:.+', 
                                        '[a-z]+ on \d+/\d+/\d+ \d+:\d+ (am|pm)[ ]*,.+?wrote:.+',
                                        'on [a-z]+, \d+/\d+/\d+,.+?wrote:.+', 
                                        'on [a-z]+, \d+, \d+, at (\d+|\d+:\d+)[ ]*(am|pm)[ ]*(,|).+?wrote:',
                                        'on [a-z]+ \d+, \d+ \d+:\d+ (am|pm),.+?wrote:.+',
                                        '[-]+ original message [-]+',
                                        'on \d+[/-]\d+[/-]\d+ \d+:\d+[ ]*(am|pm|)[ ]*,.+?wrote:.+',
                                        'on [a-z]+(,|)[ ]*[a-z]+ \d+(th|st|), \d+(,|)[ ]*(at|)[ ]*\d+:\d+[ ]*(am|pm|),.+?wrote:',]),
                                        ' ', body)
                #clean whitespace    
                body = sub('[ ]+', ' ', body)
                
            else:
                #no body was found
                body = None
            
            #For the ability to review file in excel call _add_body to split up body into 1000 character chunks
            if kw['review'] == True:
                self._add_body(vars, body, b_c)
            else:
                vars.append(body)
            
            #add the list-name and list-tag information
            self._addListInfo(self.list_name, vars)
            
            #attempt to add the row, if it does not add output the parsing error information
            try:
                self.dataset.add_row(vars)      
            except:
                #if self.verbose:
                print 'Problem extracting %s' % path
                print 'ROW: %s' % vars[0]
                print '---------------'
                self.extract_err_c += 1
                
        cs.wait()
    
    def stage_training(self, dir, fn, fmt):
        """This module take a directory, filename and format of a coded training dataset and appends the coded event
        values to the test dataset stored in self."""
        
        #declare variables
        training = {}
        
        #load the training dataset
        trn = cs.load(filename = os.path.join(dir, fn + _format_info[fmt]), format = fmt)
        cs.wait()
        
        #loop over the training dataset and add path_id as key and the predicted event value as the value to 
        #training dictionary
        for row in trn:
            training[sub('.+?data\\\\raw\\\\', '', row['path'])] = row['event']
        
        
        #add the event variable to extracted and cleaned test dataset
        self.dataset.variables.append(('event', 'string'))
        
        #loop over the test dataset to add the predicted value if it is present in the training dictionary
        for row in self.dataset:
            if sub('.+?data\\\\raw\\\\', '', row['path']) in training:
                row['event'] = training[sub('.+?data\\\\raw\\\\', '', row['path'])]
        
        #save the test dataset
        self.dataset.save(filename = self.save_dir + r'\pre_processed.txt', format = 'text', overwrite = True)
        cs.wait()
        
    def process(self, data_dir, save_dir):
        """This module processes a extracted and cleaned dataset and creates processed .arff files and a .text files. 
        It produces test.arff (the test dataset) and training.arff (the training dataset). The training dataset is used
        by gen_model() to create a C4.5 classificaition model using weka's J48 algorithm and test.arff is used in
        classify() to use the model created by the training dataset and then apply this model to the test dataset to
        predict the event variable."""
        #load keyword list
        keywords = cs.load(filename = os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'metadata', 'keywords.txt')), 
                           format = 'text', var_names = ['id', 'regex'])
        
        cs.wait()
        #add keyword to var_names and to kw dictionary
        kw = {}
        var_names = []
        for row in keywords:
            var_names.append(('k_' + row['id'], 'nominal'))
            kw[row['id']] = row['regex']
        
        #list of variables to add to the processed dataset to use for the C4.5 classification algorithm
        for var in ['b_day', 'b_date', 'b_time_full', 'b_time_str', 'b_month', 'b_season',
                    's_day', 's_date', 's_time_full', 's_time_str', 's_month', 's_season',
                    're', 'fwd', 'list_name', 'event', ]:
            var_names.append((var, 'nominal'))
        
        #add new variables to dataset and create the nominal mapping for arff saving
        nom_map = {}
        list_map = {}
        for row in self.dataset:
            list_map[sub('-.+', '', row['list-name'])] = 1
        
        for var in var_names:
            #create nominal variable class
            if var[0] == 'list_name':
                nom_map[var[0]] = [ln for ln in list_map.iterkeys()]  
            else:
                nom_map[var[0]] = ['YES', 'NO']
            if var[0] not in self.dataset.variables:
                self.dataset.variables.append(var)
        
        #create test and training dataset with the above variable names
        ds_test  = cs.Dataset(var_names)
        ds_train = cs.Dataset(var_names)
        #regular expression for extracting certain keywords present in the data
        day       = ('day', '(mon|tues|wed(nes|)|thur(s|)|fri|sat|sun)( |day)')
        time_full = ('time_full', '%s (\d+:\d+|\d+)[ ]*(am|pm)' % day[1])
        time_str  = ('time_str', 'noon|midnight|dusk|dawn|night|day')
        month     = ('month', ' jan(uary|) | feb(uary|) |march|april| may |june|july|august|september|october| (nov|ember) | dec(ember|) ')
        season    = ('season', 'sping|summer|winter|fall')
        date      = ('date', '\d+[/-]\d+[/-]d+|\d+[ ]*(?=%s)|%s \d+' % (month[1], day[1]))
        
        #loop over the test dataset looking in the variables to produce new variables for the processed test dataset
        for row in self.dataset:
            #loop over all the variables in each row
            for var, var_info in izip(row, self.dataset.variables):
                #if variable is body or subject then first look for presence of list of keywords, then remove stop_words
                #then look for above keywords declared in the regex section above
                if 'body' in var_info.name or 'subject' in var_info.name and var:
                    for k, v in kw.iteritems():
                        row['k_' + k] = 'YES' if search(v, var) or row['k_' + k] == 'YES' else 'NO'
                    var_no_stop = remove_stop_words(var)
                    #seperating by body and subject increases accuracy by 8 - 10%
                    #for regex in [day, time_full, time_str, date, month, season]:
                    #    row['b_' + regex[0]] = 'YES' if search(regex[1], var_no_stop) or row['b_' + regex[0]] == 'YES' else 'NO'
                    
                if 'body' in var_info.name and var:
                    var_no_stop = remove_stop_words(var)
                    for regex in [day, time_full, time_str, date, month, season]:
                        row['b_' + regex[0]] = 'YES' if search(regex[1], var_no_stop) or row['b_' + regex[0]] == 'YES' else 'NO'
                if 'subject' in var_info.name and var:
                    var_no_stop = remove_stop_words(var)
                    for regex in [day, time_full, time_str, date, month, season]:
                        row['s_' + regex[0]] = 'YES' if search(regex[1], var_no_stop) or row['b_' + regex[0]] == 'YES' else 'NO'
                    
                    #check subject for reply (re:) or forward (fwd:) tag
                    row['re'] = 'YES' if 're:' in var or row['re'] == 'yes' else 'NO'
                    row['fwd'] = 'YES' if 'fwd:' in var or row['fwd'] == 'yes' else 'NO'
                
                #add list type and list name        
                if 'list-name' in var_info.name and var:
                    row['list_name'] = sub('-.+', '', row['list-name'])
                
            #add event prediction and add row to training dataset if prediction is present in self.dataset
            if row['event'] == None:
                row['event'] = '?'  
            else:
                row['event'] = 'YES' if row['event'] == '1.0' else 'NO'
                ds_train.add_row(([row[v[0]] for v in var_names]))
            
            #add parsed row to test dataset
            ds_test.add_row(([row[v[0]] for v in var_names]))
            
        #save the test and training dataset into arff format
        ds_test.save(filename = save_dir + r'\test.arff', format = 'arff', 
                     nominal_map = nom_map, dataset = 'test', overwrite = True)
        cs.wait()
        #save as text file for validate()
        ds_test.save(filename = save_dir + r'\test.txt', format = 'text', overwrite = True)
        ds_train.save(filename = save_dir + r'\train.arff', format = 'arff', 
                      nominal_map = nom_map, dataset = 'train', overwrite = True)
        cs.wait()
        
    def clean(self):
        """This module cleans the dataset, removing non-essential information from the body that was missed by cleaning
        regular expressions during raw dataset extraction."""
        
        #loop over the dataset
        for row in self.dataset:
            #iterate over the variables
            for var, var_info in izip(row, self.dataset.variables):
                #clean body
                if 'body' in var_info.name and var:
                    #remove stop words and punctuation/html
                    regex = '|'.join([
                            'http(s|)://.+? ', '\(+', '\)+', '\.+', '@+', ',+',  '&nbsp;',  '~+', '"+', '\*+', '\++', ';+',
                            '\|+', '!+', '=+',  'com/mailman/listinfo/', '&#.+?;', '"+', '&amp',
                            'com/', 'com&gt;', 'php?eid', '\?+', '&lt;', '&gt',
                            '&quot;', 'www', '_+', 'message--+', '--+', '((n|)\'(t|s|m))', ',+', '#+'])
                    text = sub(regex, ' ', var)
                    text = remove_stop_words(text)
                    text = sub('[ ]+', ' ', text)
                    row[var_info.name] = text
        
        #save the cleaned file
        self.save('extract_cleaned', 'text')
        cs.wait()
        
    def validate(self, val_ds):
        """This module takes a classified dataset and compares it against a validation dataset to access the 
        accuracy of the model used to classify the given datast. A stats.txt file is outputed with statistics on the 
        accuracy of the model."""
        
        #declare variables
        val = {}
        yes_correct   = 0.0
        yes_incorrect = 0.0
        no_correct    = 0.0
        no_incorrect  = 0.0
        sub_total     = 0.0
        total         = 0.0
        
        #convert the predict value to an integer
        val_ds.variables['event'].convert('integer')
        cs.wait()
        
        #loop over the validation dataset to create a dictionary with keys = the path id, and values = predicted value.
        for row in val_ds:
            total += 1.0
            val[sub('.+?data\\\\raw\\\\', '', row['path'])] = row['event']
        
        #loop over the classified dataset to gather counts of correct and incorrect predictions
        for row in self.dataset:
            if row['path'] in val:
                if row['predicted']:
                    sub_total += 1.0
                    if 'YES' in row['predicted']:
                        if val[row['path']] == 1:
                            yes_correct += 1.0
                        else:
                            yes_incorrect += 1.0
                    else:
                        if val[row['path']] == 0:
                            no_correct += 1.0
                        else:
                            no_incorrect += 1.0
        
        #output the statistics on the accuracy of the model
        with open(self.data_dir + '\stats.txt', 'wb') as f:
            f.write('Validation\n==========\n\nTotal validation sample: %i\nTotal predicted: %i\nModel was %s accurate.\n\n' %
                     (total, sub_total, (str(round((((no_correct + yes_correct) / sub_total) * 100.0), 2)) + '%')))
            f.write('Confusion Matrix\n----------------\n a   b   <-- classified as\n')
            f.write('%s  %s |   a = YES\n%s  %s |   b = NO\n' % (yes_correct, yes_incorrect, no_incorrect, no_correct))
        
        #print the model accuracy statistics to the command line
        print 'Validation'
        print '=========='
        print 'Total validation sample: %i' % total
        print 'Total predicted: %i' % sub_total
        print 'Model was %s accurate.\n' % (str(round((((no_correct + yes_correct) / sub_total) * 100.0), 2)) + '%')
        print 'Confusion Matrix'
        print '----------------'
        print ' a   b   <-- classified as'
        print '%s  %s |   a = YES' % (yes_correct, yes_incorrect)
        print '%s  %s |   b = NO'  % (no_incorrect, no_correct)

    def save(self, fn, fmt, sample = None):
        """This module takes a filename, format, and optional sample arguement and saves the dataset with the given
        arguements. If a sample arguement is provided than a random sample of x% is saved where x is a float. 
        x = .05 will save approxiametly 5% of the file."""
        
        self.dataset.save(filename = os.path.join(self.save_dir, fn + _format_info[fmt]), format = fmt, overwrite = True)
        if sample:
            self.dataset.save(filename = os.path.join(self.save_dir, fn + _format_info[fmt]), format = fmt, sample = .13, overwrite = True)
    

    #Below code used during project but ultimately not used in the final deliverable
    def review_terms(self):
        """This module is a helper function to review the list of terms present in the extracted file. It was used
        to review the results of cleaning and removing stop words."""
        
        #declare variables
        word_list = dict()
        
        #loop over the dataset to gather the terms present in the body variable
        for row in self.dataset:
            for var, var_info in izip(row, self.dataset.variables):
                if 'body' in var_info.name and var:
                    for word in var.split():
                        if word in word_list:
                            word_list[word] += 1
                        else:
                            word_list[word] = 1
        
#        #if the term appears less than 3 time remove it
#        for row in self.dataset:
#            for var, var_info in izip(row, self.dataset.variables):
#                if 'body' in var_info.name and var:
#                    for word in var.split():
#                        if word in word_list and word_list[word] < 10:
#                            
#                            row[var_info.name] = row[var_info.name].replace(word, '')
#                            del word_list[word]
#        
#        self.save('cleaned_new', 'text')
#                      
#        print len(word_list) 
#       
#        with open(r'D:\school\ect584\final\Data\process\word_list_new.txt', 'wb') as f:
#            for k,v in word_list.iteritems():
#                f.write(k + '\t' + str(v) + '\r\n')
#            
#        ds.save(filename = r'D:\school\ect584\final\Data\process\word_list.xls', format = 'excel')
#        cs.wait()