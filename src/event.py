from main import _check_file, run_extract, run_process, build_model, classify, run_clean, stage_train, validate
import argparse, subprocess
import os, sys
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

def _check_file(file_path, as_dir = False):
    '''Helper function to validate directory and file paths.'''
    if not os.path.exists(file_path):
        print "%s does not exist." % file_path
        sys.exit(1)
                    
    if as_dir:
        if not os.path.isdir(file_path):
            print "%s is not a directory." % file_path
            sys.exit(1)
    else:
        if not os.path.isfile(file_path):
            print "%s is not a file." % file_path
            sys.exit(1)
            
def _check_format(format):
    """Helper function to validate format can be handled by version of cardsharp in this project."""
    if format not in ['csharp', 'excel', 'text', 'csv', 'spss', 'del', 'arff']:
        print "%s not a valid file type." % format
        sys.exit(1)
    
def _stage(args): 
    """Wrapper function to run cmd event.stage command. Validates argument parameters and then calls run_extract"""
    _check_file(args.data_dir, as_dir = True)
    _check_file(args.save_dir, as_dir = True)
    
    print "Staging data..."
    
    try:
        run_extract(args.data_dir, args.save_dir, args.verbose)
    except:
        if args.verbose:
            raise
        print "Fatal error. Aborting stage and terminating program. Run with -v 1 for verbose output with more details."
        sys.exit(1)
    
    print "done."

def _classify(args):
    """Placeholder for classify command"""
    pass

def _apply_model(args):
    """Placeholder for appy_model command"""
    pass

def _process(args):
    """Placeholder for process command"""
    pass

def _example_run(args):
    """Command to run example for ECT-584. First runs the extract on the raw emails to produce a raw dataset.
    This dataset is then cleaned and the training data is staged to produce a pre_processed dataset test dataset
    with predicted event values appended. This is then processed to create a test and training arff dataset.
    The training dataset is used to create a classification model using weka's J48 implementation of the C4.5 
    classification algorithm. Once the model has been created the test dataset has events predicated and these 
    predicated values are appended to the test dataset and saved to an excel file. Then this file is loaded and
    compared against the validation dataset to access the accuracy of the model.
    """
    #calls main.py run)extract with relative file paths
    #run_extract(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'raw')),
    #            os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')), 
    #            'extract', 'text', False)
    #calls main.py run_clean with relative file paths
    run_clean(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
              os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
              'extract', 'text')
    #calls main.py stage_train with relative file paths
    stage_train(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
                'extract_cleaned',
                'text',
                os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'train')),
                't_data',
                'excel',
                os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')))
    #calls main.py run_process with relative file paths
    run_process(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
                os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'process')), 
                'pre_processed', 
                'text')
    #calls main.py build_model with relative file paths
    build_model(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'process', 'train.arff')), 
                os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'process', 'model.model')))        
    #calls main.py classify with relative file paths
    classify(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'process', 'test')), 
             os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'process', 'model.model')), 
             os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'results', 'output.xls')), 
             'event')
    #calls main.py validate with relative file paths
    validate(os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'results')), 
             'output')

#Create cmd argument parsers
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Run the Burning Man Email programs.')

    subparsers = parser.add_subparsers(help = 'sub-command help')
    
    stage = subparsers.add_parser('stage', help = 'stage help')
    stage.add_argument('-d', '--data_dir', 
                       help    = "The path to the directory which contains the raw html emails. Default = %s" % 
                                                        os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'raw')),
                       default = os.path.normpath(os.path.join(__file__, '..', '..','data', 'raw')),
                       )
    stage.add_argument('-s', '--save_file', 
                       help    = "The path to the raw dataset save file. Default = %s" % 
                                                        os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
                       default = os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
                       )
    stage.add_argument('-v', '--verbose', 
                       help    = "Verbose output: a value of 1 is on, and 0 is off. Default = 0 (off).",
                       default = 0,
                       )
    stage.set_defaults(func = _stage)
    
    process = subparsers.add_parser('process', help = 'run help')
    process.add_argument('-d', '--data_file', 
                       help    = "The path to the raw dataset file. Default = %s" % 
                                                        os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'raw')),
                       default = os.path.normpath(os.path.join(__file__, '..', '..','data', 'raw')),
                       )
    process.add_argument('-s', '--save_dir', 
                       help    = "The path to the raw dataset should be saved. Default = %s" % 
                                                        os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
                       default = os.path.normpath(os.path.join(__file__, '..', '..', 'data', 'stage')),
                       )
    process.add_argument('-v', '--verbose', 
                       help    = "Verbose output: a value of 1 is on, and 0 is off. Default = 0 (off).",
                       default = 0,
                       )
    process.set_defaults(func = _process)
    
    run = subparsers.add_parser('run', help = 'run help')
    run.set_defaults(func = _example_run)
    
    args = parser.parse_args()
    args.func(args)
    