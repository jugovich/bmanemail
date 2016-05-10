Full Project Report
===================

Introduction
============

For the past 24 years a community of like-minded individuals has gathered together during the summer months to celebrate 
music, art and life. This celebration has grown into what we now call Burning Man and the community members who 
partake in it have been given the name of Burners. Since 1986 the yearly participants of Burning Man has grown from 
20 to over 50,000. Since yearly population does not correlate with total community size no one really knows how many 
Burners are out there (and who is a Burner is a topic worthy of discussion in of itself), but the number is substantial. 
As the Burning Man organization has grown it has developed a series of resources for the community. 
One of these resources is a series of regional announcement and discussion listhosts that provide a place for 
Burners to post local events and discus topics related to Burning Man. 
These resources are a fantastic tool and this project plans to use them to establish the foundation for an 
web application that will centralize event information to allow Burners quick and easy access to all events 
happening not only in their locale but across the world.

This project has completed the initial work for the Burning Man Event Mail Filtering agent. The agent allows command line
calls to load listhost emails into a raw dataset, then clean and process that dataset, save the files into arff format,
generate a classification model, apply this model to the extracted emails, and finally runs validation 
on the prediction results. Future work includes improving the classifier model, and building a web interface to view the
emails classified as events.

Methodology
===========

Gathering Burner Emails
-----------------------
Using http://regionals.burningman.com/regional-directory.html I subscribed to announcement and discussion email 
list servers using the email address of bmanemail137@gmail.com on Jan 12th 2011. In gmail I created a filter for all
these list servers using the from address to categorize them as name-list (discussion lists) and name-announce (announcement lists).
Only public lists having @burningman.com server were used, this eliminated all the private list servers to ensure 
privacy rules of those listhosts. In total 87 lists were used.

Once filters were created I setup an imap connection to the Mozilla Thunderbird client. This client was used because it has
extraction capabilities using a plugin called mbx2eml http://luethje.eu/prog/mbx2e-en.htm. This allowed me to create an
export of all the emails into html format. The emails were exported into a subdirectory with the filter name + extract time.
For this project on 5/26 I created on extract and all the raw html files can be seen in the *install-path*/data/raw/ dir.
This extract produced 87 subdirectories with 3872 emails in total. 

Creating the Raw Dataset
------------------------

After the files were extracted I then began the process of reviewing the data and determining the best approach to conduct
data preprocessing. The following rules were determined for extracting the raw emails.

 1) Loop over each subdirectory in raw (all the list servers)
 
 2) Loop over all the emails in the message folder
 
 3) Add the file path to the extract dataset for row id
 
 4) extract the subject, from, to, time, sender, date, cc, using the following regex
    
    >>> '</td>[ ]*</tr>[ ]*</table>[ ]*<br>(?P<b>.*?)</body>[ ]*</html>'
 
 5) add the list name information by looking at the directory where the emails were coming from
 
 6) add the list-tag information to check if the message came from another list (this information was to be used 
    to determine if the message was forwarded but fwd: keyword in subject proved more reliable). 
    To extract this information I looked at the subject variable and extracted the first occurrence of 
    
    >>> [.+?]
    
 7) The next step was to clean the message body. I removed extra whitespace, html information, css style information, and if the 
    message was a response then I removed the orignial message. 
 
 8) After it was cleaned I added the body information. I created a helper function to split the body into 1000 character
    chunks to make manual coding of the test and validation dataset possible in excel.
 
 9) All this data was then saved to a extract.txt (.xls if review = True) file in the /data/stage directory.
    
The final extract was able to sucessfully code all but 9 emails. Thus the extract dataset had 3861 emails.

Coding the Validation and Training data
---------------------------------------

To create a C4.5 classifier I needed a training dataset. To produce this I generated a random sample of 509 emails
to code. The coding was done subjectively following a very loose set of coding rules.

  1) If the email had a specific time period announcing a gathering, party, fundraiser, festival, meet-n-great, etc.
     then it was coded as being an event.
  
  2) If the email provided updates about an event but no specific announcement information then it was coded as not an event.
  
  3) If the email was a re: then only information about a new event announcement made the email an event email. 
     The original message did not count as an announcement.
  
  4) If the message was a forward then the originial message/(s) were reviewed for event announcement information and 
     coded by rules 1 and 2.
     
To create the validation dataset for determining the accuracy of the classifier model 240 new emails were coded using the 
above rules (the sample did not contain any emails in the training dataset). The coding was done by another individual 
from the original coder. This may have introduce additional selection bias of non-event versus event emails into the project.
In future releases a more concrete criteria for selecting announcement emails will be followed. While this may result in 
more event emails not being correctly coded it will increase the accuracy of the model at predicting pre-defined "events".

Creating the Pre-processed Dataset
----------------------------------

Once the raw dataset was created the next step was to clean the dataset. All occurences of random characters that had
whitespace around them were removed as well as link urls and html tag data.

>>> regex = '|'.join([
>>>               'http(s|)://.+? ', '\(+', '\)+', '\.+', '@+', ',+',  '&nbsp;',  '~+', '"+', '\*+', '\++', ';+',
>>>               '\|+', '!+', '=+',  'com/mailman/listinfo/', '&#.+?;', '"+', '&amp',
>>>               'com/', 'com&gt;', 'php?eid', '\?+', '&lt;', '&gt',
>>>               '&quot;', 'www', '-+', 'message--+', '--+', '((n|)\'(t|s|m))', ',+', '#+'])

The cleaned file was saved as extract-cleaned in stage and then loaded by the stage-training() module 
to add the predicted values which were  coding in the training dataset to the test dataset. 
This file was saved as pre-processed.txt in stage. 

Creating the Processed Test and Training Datasets
-------------------------------------------------

The pre-processed.txt file was then loaded. The following variables were added to the test and training dataset:

>>> ['b-day', 'b-date', 'b-time-full', 'b-time-str', 'b-month', 'b-season',
>>>  's-day', 's-date', 's-time-full', 's-time-str', 's-month', 's-season',
>>>  're', 'fwd', 'list-name', 'event', ]

These variables represented if keyword information was contained in the body b- or the subject s-, or if the email
was a response email (re: was checked in subject), a forwarded email (fwd was checked in subject), the list-name was added
(extracted from the directory where the email resided) and event was the predicted value.

In addition to the above data keywords were added to a text file which was loaded and then the k-*key* for each key in 
keywords file was added to the test and training datasets.

After the variables were all added then the body and subjected were seached for the keywords. For the keywords in the file
stop-words were included in the search. The following keywords were used.

>>> key	regex-value
>>> 1	save the date
>>> 2	come join us
>>> 3	on sale
>>> 4	buy tickets
>>> 5	general admission
>>> 6	date
>>> 7	tickets
>>> 8	admission
>>> 9	\\$\\d+
>>> 10	announcement
>>> 11	fundraiser
>>> 12	party
>>> 13	festival
>>> 14	event

For the other keywords stop-words were removed to provide better matching results. A list of stop words was created by
manually reviewing (iterative proceess) the full set of terms present in the data along with frequencies. The list of
stop words was as follows:

>>> ['the', 'to', 'and', 'of', 'a', 'you', 'is', 'or', 'i', 'on', 'be', 'your', 'that', 'are',
>>>  'with', '-', 'will', 'have', 'as', '&amp;', 'all', 'list', 'from', 'by', 'our', 
>>>  'mailing', 'not', 'an', 'so', 'but', 'in', 'it', 'because', 'had', 'you', 'hey', 'we',
>>>  'hi', 'hello', 'greetings', 'dear', 'can', 'thanks', 'if', '--+', '\*+',
>>>  'me', 'has', 'was', 'would', 'who', 'unsubscribe', 'up', '@burningman.com', 'burningman',
>>>  'for', 'this', 'does', 'can', 'com', 'man', 'burning']

Once the stop words were removed the below regular expressions were applied to match the remaining keywords:

>>> #regular expression for extracting certain keywords present in the data
>>> day       = ('day', '(mon|tues|wed(nes|)|thur(s|)|fri|sat|sun)( |day)')
>>> time-full = ('time-full', '%s (\d+:\d+|\d+)[ ]*(am|pm)' % day[1])
>>> time-str  = ('time-str', 'noon|midnight|dusk|dawn|night|day')
>>> month     = ('month', ' jan(uary|) | feb(uary|) |march|april| may |june|july|august|september|october| (nov|ember) | dec(ember|) ')
>>> season    = ('season', 'sping|summer|winter|fall')
>>> date      = ('date', '\d+[/-]\d+[/-]d+|\d+[ ]*(?=%s)|%s \d+' % (month[1], day[1])) 

If a match was found to a keyword its corresponding variable was coded as a **YES** otherwise it was a **NO**. 

The training set was isolated by checking to see if the dataset initially loaded had a predicted value (was appended 
during stage training). If it did then the keyword term matrix was added to the the training.arff file where each row
represented a case (email) and each column represented a term. For the test dataset all processed rows were added. 

Finally the test.arff and training.arff datasets were saved to /datat/process/

Creating the Classifier Model 
-----------------------------

To classify event emails weka's J48 implementation of the C4.5 classifier algorithm was used with the default settings 
(changing the settings never improved the accuracy). Many iterations of trying different sets of keywords were attempted.
After much trial and error the keyword list and regular expressions for parsing was finialized (see above) and I created
a wrapper for calling weka through python. To create the classifier I used python's subprocessor.call() method: 
see http://docs.python.org/library/subprocess.html

>>> subprocess.call(['java', 'weka.classifiers.trees.J48', 
>>>                  '-C', '0.25', 
>>>                  '-M', '2', 
>>>                  '-t', training-file, 
>>>                  '-d', model-dir])

This resulted in the following output (in addition to a model.model file which was saved in /data/process).

Building C4.5 classification model using supplied training set...

Options: -C 0.25 -M 2 

J48 pruned tree
~~~~~~~~~~~~~~~

k-8 = YES: YES (17.0/1.0)

k-8 = NO

|   re = YES: NO (269.0/6.0)

|   re = NO

|   |   b-month = YES

|   |   |   k-11 = YES: YES (12.0)

|   |   |   k-11 = NO

|   |   |   |   b-time-str = YES: YES (76.0/20.0)

|   |   |   |   b-time-str = NO: NO (20.0/7.0)

|   |   b-month = NO

|   |   |   k-9 = YES

|   |   |   |   b-time-str = YES

|   |   |   |   |   k-14 = YES: NO (3.0/1.0)

|   |   |   |   |   k-14 = NO: YES (6.0/1.0)

|   |   |   |   b-time-str = NO: NO (5.0)

|   |   |   k-9 = NO

|   |   |   |   k-14 = YES

|   |   |   |   |   k-7 = YES: YES (3.0)

|   |   |   |   |   k-7 = NO: NO (8.0/2.0)

|   |   |   |   k-14 = NO: NO (90.0/3.0)


Number of Leaves  : 	11

Size of the tree : 	21


Time taken to build model: 0.03 seconds

Time taken to test model on training data: 0.02 seconds

=== Error on training data ===

Correctly Classified Instances         468               91.945  %

Incorrectly Classified Instances        41                8.055  %

Kappa statistic                          0.7661

Mean absolute error                      0.1257

Root mean squared error                  0.2507

Relative absolute error                 36.7952 %

Root relative squared error             60.7141 %

Total Number of Instances              509     


=== Confusion Matrix ===

   a   b   <-- classified as

  92  19 |   a = YES

  22 376 |   b = NO


Running Predictions
-------------------

Using the model which was produced I used subprocess.check-output to capture the prediction infomation and add this 
to the test dataset. This is necessary for both validation purposes and to be able to identify predicted email for 
loading into the web interface for dispalying to users the different events.

>>> predictions = subprocess.check-output(['java', 'weka.classifiers.trees.J48', 
>>>                '-p', str(test.variables.index(predict-var-name) + 1), 
>>>                '-T', test-file + '.arff', 
>>>                '-l', model-file])
    
The test dataset with appended predictions was saved to /data/results.xls

Validation
----------

After the test dataset was outputted I then loaded the validation dataset and compared the predicted values in it to the 
predicited values in the test dataset. These results were saved and outputted to a stats.txt file:

Validation

Total validation sample: 240

Total predicted: 230

Model was 62.17% accurate.


Confusion Matrix

 a   b   <-- classified as

15.0  45.0 |   a = YES

42.0  128.0 |   b = NO


Notes on Saving / Loading
-------------------------

Most saving and loading and some variable manipulation used the cardsharp open source project, 
http://cardsharp.norc.org/cardsharp/wiki/Home . To allow for loading and saving of arff files I created
an arff handler to add to the cardsharp project. 

Automated
---------

This project has created the ability to load a set of raw html files, clean and parse these files, and then load
them into weka for classification and finally output a classified dataset all within the python framework. Incorporating
django the whole process including display to the web can be automated. This creating an online web filtering agent.

File Output Flow
----------------

The below files are produced after running the bmemail event.py run command.

First raw emails are parsed using bmine.extract() to produce the extract file:
:download:`extract.txt </data/stage/extract.txt>`

Then the extract file is cleaned with bmine.clean() to procude the cleaned extract file:
:download:`extract-cleaned.txt </data/stage/extract-cleaned.txt>`

Then the cleaned-extract has more pre-processing work done to it to get it ready for processing. First bmine.stage-train()
is called to add the training data (:download:`t-data.txt </data/train/t-data.xls>`) to the cleaned-extract and this produces- 
:download:`pre-processed.txt </data/stage/pre-processed.txt>`, and then bmine.process() is run to produce arff files 
for conducting datamining work in weka- :download:`train.txt </data/process/train.arff>`, and :download:`test.txt </data/process/test.txt>`. 
 
After the training and test file have been produced a model is created using main.build-model() creating a .model file:
:download:`model.model </data/process/model.model>`.
 
This model is used to do C4.5 classification on the test.arff file using weka's J48 algorithm by running main.classify(), 
and the output from this is captured by Python using the subprocess.check-output() command. This output is appended to the
test dataset and then saved to :download:`output.xls </data/results/output.xls>`.

Finally, the output file is read and compared against the validation file,
:download:`validate.xls </data/validate/v-data.xls>` to access the accuracy of the model. Some 
statistics about the accuracy of the model, including a confusion matrix, are outputed to 
:download:`stats.txt </data/results/stats.txt>`,


The below files are used to run the BM-email program.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The keywords file is a tab delimited file with the first column being the key and the second column is a regular expression
to match a certain keyword or phrase.

:download:`keywords.txt </data/metadata/keywords.txt>`

The training file was created using the gen-sample() method in bmine with sample parameter = .13. This produced 
a training sample file of 510 emails which were than manually coded (event) as either an event announcement or not
an event announcement.

:download:`train.xls </data/train/t-data.xls>`

The validation file was created using the gen-sample() method in bmine with sample parameter = .05. This produced 
a training sample file of 240 emails which were than manually coded (event) as either an event announcement or not
an event announcement.

:download:`validate.xls </data/validate/v-data.xls>`


Full Command Line Output From run() command
-------------------------------------------

...extracting raw emails (this is gonna take a bit)...

Problem extracting D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110314-[denver-announce] TONIGHT! Meet & Greet Potluck-6.html

ROW: D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110314-[denver-announce] TONIGHT! Meet & Greet Potluck-6.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110321-[denver-announce] Burner Meet & Greet Potluck - Sushi Edition -8pm -1 am-9.html

ROW: D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110321-[denver-announce] Burner Meet & Greet Potluck - Sushi Edition -8pm -1 am-9.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110411-[denver-announce] Potluck Monday! Burner Meet & Greet Potluck 8pm -1 am-19.html

ROW: D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110411-[denver-announce] Potluck Monday! Burner Meet & Greet Potluck 8pm -1 am-19.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110502-[denver-announce] Potluck Monday! Burner Meet & Greet Potluck 8pm -1 am-25.html

ROW: D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110502-[denver-announce] Potluck Monday! Burner Meet & Greet Potluck 8pm -1 am-25.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110509-[denver-announce] Tonight!! Potluck Monday! Meet and Greet!-27.html

ROW: D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110509-[denver-announce] Tonight!! Potluck Monday! Meet and Greet!-27.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110519-[denver-announce] Pink Mammoth Fundraiser This Saturday!-34.html

ROW: D:\workspace\bmemail\data\raw\denver-announce-20110526-2347\messages\20110519-[denver-announce] Pink Mammoth Fundraiser This Saturday!-34.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\la-announce-20110526-2348\messages\20110331-[la-announce] LA Burning Man Announce 3-31-19.html

ROW: D:\workspace\bmemail\data\raw\la-announce-20110526-2348\messages\20110331-[la-announce] LA Burning Man Announce 3-31-19.html

---------------

Problem extracting D:\workspace\bmemail\data\raw\newyork-list-20110526-2348\messages\20110406-[BManNYC] OT World-s First Bacon Perfume-158.html

ROW: D:\workspace\bmemail\data\raw\newyork-list-20110526-2348\messages\20110406-[BManNYC] OT World-s First Bacon Perfume-158.html

---------------

D:\workspace\bmemail\data\raw\newyork-list-20110526-2348\messages\20110418-Re-[BManNYC] Travelers Insurance (was  OT Please help friend-KKe?r in need and go have your fun too!)-397.html does not exist.

Problem extracting D:\workspace\bmemail\data\raw\portland-list-20110526-2345\messages\20110513-Re[portland-list] Bacon Filibuster-465.html

ROW: D:\workspace\bmemail\data\raw\portland-list20110526-2345\messages\20110513-Re[portland-list] Bacon Filibuster-465.html

---------------

Extraction Compelete with 9 emails failed to parse...

Saving dataset...

save complete...

...cleaning data...

complete.


Staging training dataset (adding in predicted values)...

...complete.

...processing data...

complete.


Building C4.5 classification model using supplied training set...

Options: -C 0.25 -M 2 

J48 pruned tree

k-8 = YES: YES (17.0/1.0)

k-8 = NO

|   re = YES: NO (269.0/6.0)

|   re = NO

|   |   b-month = YES

|   |   |   k-11 = YES: YES (12.0)

|   |   |   k-11 = NO

|   |   |   |   b-time-str = YES: YES (76.0/20.0)

|   |   |   |   b-time-str = NO: NO (20.0/7.0)

|   |   b-month = NO

|   |   |   k-9 = YES

|   |   |   |   b-time-str = YES

|   |   |   |   |   k-14 = YES: NO (3.0/1.0)

|   |   |   |   |   k-14 = NO: YES (6.0/1.0)

|   |   |   |   b-time-str = NO: NO (5.0)

|   |   |   k-9 = NO

|   |   |   |   k-14 = YES

|   |   |   |   |   k-7 = YES: YES (3.0)

|   |   |   |   |   k-7 = NO: NO (8.0/2.0)

|   |   |   |   k-14 = NO: NO (90.0/3.0)


Number of Leaves  : 	11

Size of the tree : 	21


Time taken to build model: 0.03 seconds

Time taken to test model on training data: 0 seconds


=== Error on training data ===

Correctly Classified Instances         468               91.945  %

Incorrectly Classified Instances        41                8.055  %

Kappa statistic                          0.7661

Mean absolute error                      0.1257

Root mean squared error                  0.2507

Relative absolute error                 36.7952 %

Root relative squared error             60.7141 %

Total Number of Instances              509     

=== Confusion Matrix ===

   a   b   <-- classified as

  92  19 |   a = YES

  22 376 |   b = NO


=== Stratified cross-validation ===


Correctly Classified Instances         448               88.0157 %

Incorrectly Classified Instances        61               11.9843 %

Kappa statistic                          0.6497

Mean absolute error                      0.1596

Root mean squared error                  0.3172

Relative absolute error                 46.6985 %

Root relative squared error             76.8067 %

Total Number of Instances              509     



=== Confusion Matrix ===


   a   b   <-- classified as

  81  30 |   a = YES

  31 367 |   b = NO


...complete.

Validating data...

Validation


Total validation sample: 240

Total predicted: 230

Model was 62.17% accurate.


Confusion Matrix

 a   b   <-- classified as

15.0  45.0 |   a = YES

42.0  128.0 |   b = NO

All Complete.
