#!/usr/bin/env python
#hack_sms.py

import os
import sys
import string
import re
import struct
from time import ctime
from pprint import pprint

'''
Copyright (c) 2010 Michael Seydel <micseydel@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

* The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
* Any use of the Software for commercial purposes requires that the copyright
holder be notified of the purpose of the derived work, and how the copyright
holder may obtain a copy of the derived work, before the derived work is
released.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.



Last updated: 29 August 2010

DESCRIPTION:
The purpose of this code is to extract information from the Palm SMS file
Message_Database.pdb. This code is in-progress. I, the author, only have a
Palm Treo 755p (previously 700p) from Verizon so have had limited data to
test. The datasets I've been able to look at include texting both
Verizon-to-Verizon and Verizon-to-Other.

This specific file is for the SMS database, however I intend to have a more
full set of tools which would also be able to deal with the phonebook,
calendar, memos, and maybe even call history. ("maybe" because *I* don't care)

TODO:
  * refine sent message finding
  * find drafts pattern
  * re patterns for phone numbers need to be improved
    * phone numbers of different lengths, w/ and w/o dashes or dots
  * for the special numbers, this program should identify known
      numbers such as Twitter, Facebook, AIM, etc. rather than
      labelling them as their phone number. this is low priority.
      _give_number_name() is a function for this which is called in
      get_phone_numbers() but it was written for something else so may
      need slight modification
  * default messages database for mac needs some clean up
  

NOTES:
  * currently, received texts can be pulled with sender & their
      phone number, as well as most sent messages
  * date/time somewhat retrievable
  * my phone will only show up to 200 messages for an individual - this does
  not mean that it is not in the record, and this should be checked out
  * when using get_sent() I found that the most recent sent weren't caught
  * Trsm = "Treo Sent Message"?

'''

PALM_EPOCHE_CONV = 2082844800

class MessagesDatabase(object):
    'creates a Message_Database object'
    def __init__(self, location=None):
        if location is None: self.location = self.__getLocation()
        else: self.location = location
        self.__make_raw_data()
        self.__compile_re_patterns()
        self.__make_owner_number()

    def __getLocation(self):
        #try cur dir first
        if os.path.isfile('Messages_Database.pdb'):
            return 'Messages_Database.pdb'
        elif os.path.isfile('Messages Database.pdb'):
            return 'Messages Database.pdb'

        try:
            platform = os.uname()[0]
        except AttributeError:
            platform = 'Windows'

        if platform == 'Windows':
            old_file = \
                r'C:\Program Files\palm\TreoM\Backup\Messages_Database.pdb'
            new_file = \
                r'C:\Documents and Settings\%s' + os.environ['USERNAME'] + \
                r'\My Documents\Palm OS Desktop\TreoM\Backup' \
                '\Messages_Database.pdb'
            if os.path.isfile(old_file):
                return old_file
            elif os.path.isfile(new_file):
                return new_file

        elif platform == 'Darwin':
            mac_file = "/Users/micseydel/Documents/Palm/Users/" \
                "Micseydel's Treo/Backups/Messages Database.pdb"
            return mac_file if os.path.isfile(mac_file) else None

        elif platform == 'Linux':
            linux_file = '/home/micseydel/Treo/Messages Database.pdb'
            return linux_file if os.path.isfile(linux_file) else None

    def __make_raw_data(self):
        f = open(self.location, 'rb')
        self.raw_data = f.read()
        f.close()

    def __compile_re_patterns(self):
        self.__owner_number_pat = '\x000\x03\x00\x0b([0-9]+)\x00'
        self.__received_msgs_pat = re.compile(
            '([0-9]{3}[\.|\-]?[0-9]{3}[\.|\-]?[0-9]{4})' # phone number
            '\x00([\x0A\x0D\x1B-\x7E]+)?' # person
            '\x00{9} \x02\x00.([\x0A\x0D\x1B-\x7E]+)' # message
            '\x00\x80\x00(.{4})\x00') # time

        self.__received_mms_pat = re.compile(
            '([0-9]{3}[\.|\-]?[0-9]{3}[\.|\-]?[0-9]{4})\x00'
            '([\x0A\x0D\x1B-\x7E]+).{34}(.)([\x0A\x0D\x1B-\x7E]+)\x00 \x08')

        self.__sent_msgs_pat = re.compile(
            # specific to my number \x00\x07  \x00\x06 receiver's number
            '9250\x00\x80\x00(.{4})\x00..{4}\x00..{4}.{4}\x00{18}.{2}'
            '([0-9]{3}[\.|\-]?[0-9]{3}[\.|\-]?[0-9]{4})\x00'
            '([\x0A\x0D\x1B-\x7E]+)\x00{10}\x1bTrsm .{3}'
            '([\x0A\x0D\x1B-\x7E]+)\x00'
            )

    def __make_owner_number(self):
        try:
            self.owner_number = \
                re.findall(self.__owner_number_pat, self.raw_data)[0]
        except:
            self.owner_number = '0'*10

    def _give_number_name(self, number):
        'Gives more descriptive names for special numbers like for Twitter'
        if '40404' == number: return 'Twitter'
        elif '466453' == number: return 'Google'
        elif '32665' == number: return 'Facebook'
        elif '699268' == number: return 'Wamu'
        elif '93557' == number: return 'Wells Fargo'
        elif '246246' == number: return 'AIM Login'
        elif number.startswith('265'): return 'AIM-%s' % number[-3:]
        elif number.startswith('32665'): return 'Fbook-%s' % number[-3:]
        elif number.startswith('46') and len(number) == 6:
            return 'AIM-%s' % number[-4:]
        elif number.startswith('0092466'): return 'YIM-%s' % number[-3:]
        else: return number

    def get_phone_numbers(self):
        'returns list of (number, name) tuples, possibly with duplicates'
        #regular 10-digit (with area code) numbers
        regular_number_and_name_pattern = '([0-9]{3}[\.|\-]?[0-9]{3}[\.|\-]?'\
                                      '[0-9]{4})\0([\x0A\x0D\x1B-\x7E]+)?\0'
        # 5- and 6-digit numbers, like with Google, Twitter, Facebook and AIM 
        special_num_pattern = '\0([0-9]{5,6})\x00([\x0A\x0D\x1B-\x7E]+)?\x00'
        findings = re.findall(regular_number_and_name_pattern, self.raw_data)
        for special_num in re.findall(special_num_pattern, self.raw_data):
            #if name field doesn't exist...
            if not special_num[-1]:
                findings.extend((special_num[0],
                                 self._give_number_name(special_num[0])))
            #otherwise just pass it along, the user already has a name
            else: findings.extend(special_num)
        return findings

    def get_name_and_number_sets(self):
        'return list of (name, number) tuples without duplicates, ' \
        'dots and dashes considered'
        nameAndNumberSets = []
        findings = self.get_phone_numbers()
        for finding in findings:
            number, name = finding
            if number == self.owner_number: continue
            #gets rid of dots and dashes in a phone number
            nameAndNumberSet = (name, re.sub('\.|\-', '', number))
            if nameAndNumberSet not in nameAndNumberSets:
                nameAndNumberSets.append(nameAndNumberSet)
        return nameAndNumberSets

    def get_msgs(self):
        "this function doesn't really do what it's name might suggest"
        #finds all printable characters inside of ' \x02\x00.' and '\x00\x80'
        msgs = re.findall(' \x02\x00.([\x0A\x0D\x1B-\x7E]+)\x00\x80',
                          self.raw_data)

    def get_received(self, who=''):
        'returns a list of tuples in format (number, name, msg), ' \
        'with option to filter to one person'
        received_msgs_sets = []
        for msgSet in re.findall(receivedMsgsPat, self.raw_data):
            number, name, msg, time = msgSet
            # gets an unsigned int (reversed) which is a Palm epoche
            time = struct.unpack(">I", time)[0]
            if who:
                if who not in name: continue
            received_msgs_sets.append(
                (time - PALM_EPOCHE_CONV, number, name, msg))

        #mms
        for msgSet in re.findall(received_mms_pat, self.raw_data):
            number, name, msg = msgSet
            if who:
                if who not in name: continue
            received_msgs_sets.append((number, name, msg))
        return received_msgs_sets

    def print_received_msgs(self, who=''):
        'neatly prints received messages, with option to filter to one person'
        received_msgs_sets = get_received(who)
        if not received_msgs_sets:
            print '%s is not in Messages Database' % who
            return
        for received_msg_set in received_msgs_sets:
            number, name, msg = received_msg_set
            print '%s   %s' % (number, name)
            print '-' * (len(number+name)+3)
            print msg
            print

    def print_received_msgs_individual(self, who):
        'prints the name of the person, then all the messages'
        received_msgs_sets = get_received(who)
        if not received_msgs_sets:
            print '%s is not in Messages Database' % who
            return
        number, name, first_msg = received_msgs_sets[0]
        print '%s   %s' % (number, name)
        print '-' * (len(number+name)+3)
        for received_msg_set in received_msgs_sets:
            print received_msg_set[-1]
            print

    def get_sent(self, who=None):
        'get_sent([who]) -> (time, number, name, msg)'
        sent = []
        for message_set in re.findall(sent_msgs_pat, self.raw_data):
            if who:
                if message_set[2] != who:
                    continue
            time, number, name, msg = message_set
            time = struct.unpack(">I", time)[0]
            sent.append((time-PALM_EPOCHE_CONV, number, name, msg))
        return sent

    def get_outbox(self):
        'not yet functional'
        pat = re.compile(
            '([0-9]{3}[\.|\-]?[0-9]{3}[\.|\-]?[0-9]{4})\x00'
            '([\x0A\x0D\x1B-\x7E]+)\x00{9}.+([\x0A\x0D\x1B-\x7E]+).+'
            'Message Failed'
            )
        return re.findall(pat, self.raw_data)

    def get_drafts(self):
        'not yet functional'
        possible_draft_pat = re.compile(
            '(.{4})..(.{4})..(.{4})..{30}' # time
            '(\d{3}[\.|\-]?\d{3}[\.|\-]?\d{4})\0' # phone number
            '([\x0A\x0D\x1B-\x7E]+?).{13}' # name in address book
            '3107209250.{5}Michael Seydel \(M\).{10}'
            '(.)([\x0A\x0D\x1B-\x7E]+?)\0') # message length, and message
        return re.findall(possible_draft_pat, self.raw_data)

    def get_saved(self):
        'not yet functional, lags too'
        possible_saved_pat = re.compile(
            '\x20\x02.{2}([\x0A\x0D\x1B-\x7E]+)\x00\x40.+([0-9]{3}[\.|\-]?'
            '[0-9]{3}[\.|\-]?[0-9]{4})\x00([\x0A\x0D\x1B-\x7E]+)\x00'
            )
        saved = []
        for msg in re.findall(possible_saved_pat, self.raw_data):
            saved.append((msg[1], msg[2], msg[0],))
        return saved

######################END CLASS###################

def test():
    print 'Loading database...\n'
    file = 'Messages_Database_mmsAndTemplates.pdb'
#    file = selectFileFromFolder('oliverFunny', 'pdb')
    print 'Using %s' % os.path.split(file)[-1]
    msgs_db = MessagesDatabase(file)

    print 'Printing content\n'
    
    sent = msgs_db.get_sent()
    print 'Sent messages (%i):' % len(sent)
    if sent:
        for msg in sent:
            print '  %s\n    %s\n' % msg[1:]
    else: print '  None\n'

    recvd = msgs_db.get_received()
    print 'Received messages (%i):' % len(recvd)
    if recvd:
        for msg in recvd:
            print '  %s\n    %s\n' % msg[1:]
    else: print '  None\n'

    drafts = msgs_db.get_drafts()
    print 'Drafts (%i):' % len(drafts)
    if drafts:
        for msg in drafts:
            print '  %s\n    %s\n' % msg[1:]
    else: print '  None\n'

    outbox = msgs_db.get_outbox()
    print 'Outbox (%i):' % len(outbox)
    if outbox:
        for msg in outbox:
            print '  %s\n    %s\n' % msg[1:]
    else: print '  None\n'

    saved = msgs_db.get_saved()
    print 'Saved (%i):' % len(saved)
    if saved:
        for msg in saved:
            print '  %s\n    %s\n' % msg[1:]
    else: print '  None\n'

def get_long_at_position(filename, pos):
    f = open(filename)
    f.seek(pos)
    needed_bytes = list(f.read(4))
    f.close()
    needed_bytes.reverse()
    return struct.unpack("L", ''.join(needed_bytes))[0]

def get_mod_date(filename):
    'assumes that the following link is accurate' \
    'http://www.mactech.com/articles/mactech/Vol.21/21.08/PDBFile/index.html'
    seconds = get_long_at_position(filename, 0x28)
    return ctime(seconds)

def brief_test():
    database = Messages_Database('Messages_Database_noPics.pdb')
    msgs = []
    msgs.extend(database.get_received())
    msgs.extend(
        map(lambda x: x[:2] + ("Michael Seydel",) + (x[-1],),
            database.get_sent())
        )
    msgs.sort()
    for msg in msgs:
        try:
            time, number, name, content = msg
            print '%s (%s):\n\t%s\n\n' % (name, ctime(time), content)
        except ValueError: # this happened with an MMS
            print '-'*40
            print msg
            print '-'*40
            continue

def get_consecutive_empties(lst):
    numbers = []
    so_far = 0
    for element in lst:
        if element:
            numbers.append(so_far)
            so_far = 0
        else:
            so_far += 1
    numbers.append(so_far)
    return numbers

def check_nulls():
    import matplotlib.pyplot as plot
    database = Messages_Database('Messages_Database_noPics.pdb')
    #experimenting with the number of consecutive empty strings gained by this
    parts = database.raw_data[43000:].split('\0')
    list_of_numbers = get_consecutive_empties(parts)
    plot.plot(list_of_numbers)
#    plot.savefig("test.png")
    plot.show()

def find_int(filename, num, offset=0, bytes_to_check=0, tolerance=0):
    f = open(filename, 'rb')
    f.seek(offset)
    chars = list(f.read(bytes_to_check)) if bytes_to_check else list(f.read())
    f.close()

    curr = [chars.pop(0) for x in xrange(4)]
    while chars:
        thisNum = struct.unpack(">I", ''.join(curr))[0]
        if thisNum >= num - tolerance and thisNum <= num + tolerance:
            print '%02X %02X %02X %02X' % tuple(ord(char) for char in curr),
            print '(%s)) @' % thisNum, offset, ctime(thisNum-PALM_EPOCHE_CONV)
        curr.pop(0)
        curr.append(chars.pop(0))
        offset += 1

def find_short(filename, number, offset=0, bytes_to_check=0, tolerance=0):
    f = open(filename, 'rb')
    f.seek(offset)
    chars = list(f.read(bytes_to_check)) if bytes_to_check else list(f.read())
    f.close()

    curr = [chars.pop(0) for x in xrange(2)]
    while chars:
        thisNum = struct.unpack(">H", ''.join(curr))[0]
        if thisNum >= number - tolerance and thisNum <= number + tolerance:
            print '%02X %02X' % tuple(ord(char) for char in curr),
        curr.pop(0)
        curr.append(chars.pop(0))
        offset += 1

if __name__ == '__main__':
    db = MessagesDatabase(sys.argv[1])
    vzn_sent_pat = re.compile(
        #'Trsm.{12}'
        '(.{4}).{8}' # time
        '(\d{3}[\.|\-]?\d{3}[\.|\-]?\d{4})\0' # phone number
        '([\x0A\x0D\x1B-\x7E]+?).{13}' # name in address book
        '3107209250.{5}Michael Seydel \(M\).{4}'
        '(.)([\x0A\x0D\x1B-\x7E]+?)\0') # message length, and message
#    for found in vzn_sent_pat.findall(db.raw_data):
#        print found
#        print

    other_sent_pat = re.compile(
        '(.{4})...{4}.{12}' # sent time
        '(.{4}).{8}' # received time
        '(\d{3}[\.|\-]?\d{3}[\.|\-]?\d{4})\0' # phone number
        '([\x0A\x0D\x1B-\x7E]+?).{11}' # name in address book
        'Trsm.{2}(.{2})([\x0A\x0D\x1B-\x7E]+?)\0' # message length, & message
        )

    other_recvd_pat = re.compile(
        '\0(\d{3}[\.|\-]?\d{3}[\.|\-]?\d{4})\0' # phone number
        '([\x0A\x0D\x1B-\x7E]+?)\0.{10}' # name in address book
        '(.{2})([\x0A\x0D\x1B-\x7E]+?)' # message length, and message
        '\0.\0'
        '(.{4}).{2}(.{4}).{2}(.{4})\0', #times
        )

    msgs = []
    for msg in re.findall(other_sent_pat, db.raw_data):
        sent, received, phone_number, name, msg_len, msg_content = msg
        msgs.append(
            (struct.unpack('>I', sent)[0] - PALM_EPOCHE_CONV,
             '>'+name, msg_content)
        )
    for msg in re.findall(other_recvd_pat, db.raw_data):
        num, name, msg_len, content, t1, t2, t3 = msg
        msgs.append(
            (struct.unpack('>I', t1)[0]-PALM_EPOCHE_CONV, '<'+name, content)
            )
    msgs.sort()
    for msg in msgs:
        time, name, content = msg
        print name, '(%s):' % ctime(time)
        print '\t', content
        print

# this looks like it works well except for my originally sent message
#http://www.mactech.com/articles/mactech/Vol.21/21.08/PDBFile/index.html
