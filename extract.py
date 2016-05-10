import os
import re
import calendar
from datetime import  date

def get_announce_by_date():
    emails = {}
    for dir in os.listdir(r'D:\workspace\bmemail\data'):
        if re.search('announce', dir):
            emails[dir] = {}
            for file in os.listdir(r'D:\workspace\bmemail\data\%s\messages' % dir):
                #removed replies
                f = file.lower()
                if not re.match('re:|\d+-re_', f):
                    #get date and add to dict
                    dt = re.match('(\d+)', f).groups(0)
                    
                    dt = date(int(dt[0][:4]), int(dt[0][4:6]), int(dt[0][6:8]))
                    print dt
                    if dt in emails[dir]:
                        emails[dir][dt] += 1
                    else:
                        emails[dir][dt] = 1
                
#    for region, days in emails.iteritems():
#        print region
#        for day in days:
#            print [day, emails[region][day]]
#    for k,v in emails.iteritems():
#        print k
#        print v
                
                    
get_announce_by_date()