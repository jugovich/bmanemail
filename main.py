import os, sys, bmine
import re
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))
import cardsharp as cs
import subprocess
from itertools import izip

#the variables in the email dataset
variables = ['path', 'list_tag', 'subject', 'from', 'to', 'time', 'sender', 'date', 'cc', 'body']

def _check_file(file_path, as_dir = False):
    """Helper function to ensure directory/file exists"""
    if not os.path.exists(file_path):
        print '%s does not exist.' % file_path
        return False
                    
    if as_dir:
        if not os.path.isdir(file_path):
            print 'Warning: %s is not a directory.' % file_path
            return False
        else:
            return True
    else:
        if not os.path.isfile(file_path):
            print '%s is not a file.' % file_path
            return False
        else:
            return True

def run_extract(data_dir, save_dir, filename, format, verbose):
    """This module takes a data directory pointing where the raw email files are stored in seperate directories
    (one directory for each list), takes a save_dir, filename, and format for saving the extracted raw dataset.
    The module loops over all the email list directories and loops over all the email files in these directories
    calling bmine.extract() on each email. These emails are added to a raw_extract dataset. Specify verbose to see
    all extraction details (this will slow down processing time)."""
    print '...extracting raw emails (this is gonna take a bit)...'
    dirs = {}
    extractor = bmine.bmine(data_dir, save_dir)
    for dir in os.listdir(data_dir):
        list_index = 0
        full_count = 0
        dir_path = os.path.join(data_dir, dir, 'messages')
        
        if verbose:
            print 'Extracting emails from %s' + dir_path
            extractor.verbose = True
        
        list_name = re.search('[a-z]+(-announce|-list)', dir).group()
        if _check_file(dir_path, as_dir = True):
            for email in os.listdir(os.path.join(dir_path)):
                full_path = os.path.join(dir_path, email)
                if _check_file(full_path):
                    if verbose:
                        print '...extracting email %s' % full_path
                    extractor.extract(full_path, list_name, index = list_index, review = False)
                    list_index += 1
                full_count += 1
            #if int((full_count / 3500.0) * 10.0) in [x + 1 for x in range(10)]:
            #print '...still extracting: %s complete...' % (str(int((full_count / 3500.0) * 100.0)) + '%')
                
        dirs[list_name] = (full_count, list_index)
    cs.wait()    
    print 'Extraction Compelete with %i emails failed to parse...' % extractor.extract_err_c
    if verbose:
        print 'list name : email count'
        print dirs
        
    print 'Saving dataset...'
    extractor.save(filename, format)
    cs.wait()
    print 'save complete...'
    
def run_singleExtract(data_dir, save_dir):
    """This module can extract a single raw directory, (used for testing purposes)."""
    list_index = 0
    full_count = 0
    extractor = bmine.bmine(data_dir, save_dir)
    
    dir_path =  os.path.join(data_dir, 'portland-list_20110526-2345', 'messages')
    list_name = re.search('[a-z]+(-announce|-list)(?=_)', 'portland-list_20110526-2345').group()
    for email in os.listdir(dir_path):
        full_path = os.path.join(dir_path, email)
        print full_path
        if _check_file(full_path):
            extractor.extract(full_path, list_name, index = list_index)
            list_index += 1
        full_count += 1
        if full_count == 75:
            break
    print full_count
    print list_index
    extractor.save('portland-list_20110526-23451.xls', 'excel')
    
def gen_sample(data_path, save_path, sample):
    """This module takes a dataset (data_path) and saves a sample of it to a new dataset (save_path).
    This module was used to gernate the training and validation samples for the ect584 project."""
    print 'generate sample data...'
    training = cs.load(filename = data_path, format = 'excel', sample = sample)
    cs.wait()
    training.save(filename = save_path, format = 'excel', overwrite = True)
    print 'complete.'

def stage_train(data_dir, data_filename, data_format, train_dir, train_filename, train_format, save_dir):
    """This module takes a test dataset (data_dir, data_filename, data_format) and adds the predicted event
    values in the coded training dataset (train_dir, train_filename, train_format) and saves the test dataset
    with predicted values added to save_dir."""
    print 'Staging training dataset (adding in predicted values)...'
    trn = bmine.bmine(data_dir, save_dir) 
    trn.load(data_filename, data_format)
    trn.stage_training(train_dir, train_filename, train_format)
    print '...complete.'
    
def run_process(data_dir, save_dir, filename, format):
    """This module loads a dataset and processes it to produces a processed trainining dataset and test dataset
    in arff format to be used to create a classification model and then apply this module to the test dataset."""
    print '...processing data...'
    proc = bmine.bmine(data_dir, save_dir)
    proc.load(filename, format)
    proc.process(data_dir, save_dir)
    print 'complete.'
    
def run_review_terms():
    """This module was used to review the terms present in the raw/cleaned datafiles."""
    print 'Generating term file for review...'
    train = bmine.bmine(r'D:\school\ect584\final\Data\stage\\', r'D:\school\ect584\final\Data\stage\\')
    train.load(r'D:\school\ect584\final\Data\stage\cleaned.txt', 'text')
    train.review_terms()
    print 'Complete.'

def run_clean(data_dir, save_dir, filename, format):
    """This module cleans a file (filename, format) at data_dir. This cleaning is necessary to remove unwanted
    information before running process(). The file is saved to save_dir.""" 
    print '...cleaning data...'
    cln = bmine.bmine(data_dir, save_dir)
    cln.load(filename, format)
    cln.clean()
    print 'complete.'
    
def build_model(training_file, model_dir):
    """Creates a C4.5 classification model (weka J48 classifier) using a supplied arff training file 
    and outputs the completed model to supplied model_dir. The weka.classifiers.trees.J48 is called
    using pythons built-in subprocess module by calling the java process + a list of command line arguements.
    See http://docs.python.org/library/subprocess.html"""
    print 'Building C4.5 classification model using supplied training set...'
    subprocess.call(['java', 'weka.classifiers.trees.J48', 
                     '-C', '0.25', 
                     '-M', '2', 
                     '-t', training_file, 
                     '-d', model_dir])
    print '...complete.'

def classify(test_file, model_file, save_file, predict_var_name):
    """Apply a C4.5 classification model to the test_file using supplied model_file, to predict variable at 
    index of predict_var_name. The predictions are captured using subprocess.check_output See http://docs.python.org/library/subprocess.html,
    These predicitons are parsed and then stored to an output file (save_file). The output file contains the processed
    dataset information with predicted values and path_id appended."""
    test = cs.load(filename = test_file + '.arff', format = 'arff')
    cs.wait()
    test.variables.append('predicted')
    test.variables.append(('prediciton_error', 'float'))
    #classify test file and capture predictions
    predictions = subprocess.check_output(['java', 'weka.classifiers.trees.J48', 
                           '-p', str(test.variables.index(predict_var_name) + 1), 
                           '-T', test_file + '.arff', 
                           '-l', model_file])
    
    #extract prediction information and store this information in test dataset
    predictions = re.findall('[ ]+\d+[ ]+.+?:.+?[ ]+(.+?:.+?)[ ]+(\d+\.\d+)', predictions, flags = re.I)
    for line, row in izip(predictions, test):
        row['predicted'], row['prediciton_error'] = line[0], float(line[1])
    
    #load the pre_processed information to get the path_id
    ds = cs.load(filename = os.path.normpath(os.path.join(test_file, '..', '..', 'stage', 'pre_processed.txt')), format = 'text')
    cs.wait()
    path_ids = []
    from re import sub
    
    #gather the path information
    for row in ds:
        path_ids.append(sub('.+?data\\\\raw\\\\', '', row['path'])) 
    
    #add in the path information to the dataset
    test.variables.append('path')
    for row in test:
        row['path'] = path_ids.pop(0)
    
    #save the test dataset with predictions and path_id apppended
    test.save(filename = save_file, format = 'excel')
    cs.wait()

def validate(data_dir, filename):
    """This module compares a dataset that has predicted values to the validation dataset and then outputs statistics
    on the accuracy of the model."""
    print 'Validating data...'
    val_ds = cs.load(filename = os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'validate', 'v_data.xls')), format = 'excel')
    cs.wait()
    val = bmine.bmine(data_dir, '')
    val.load(filename, 'excel')
    val.validate(val_ds)
    print 'All Complete.'