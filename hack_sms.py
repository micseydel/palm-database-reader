#!/usr/bin/env python
#hack_sms.py

import os
import sys
import string
import re
from struct import unpack
from datetime import datetime

'''
Copyright (c) 2013 Michael Seydel <micseydel@gmail.com>

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


Last updated: 17 February 2013

DESCRIPTION:
The purpose of this code is to extract information from the Palm SMS file
Message_Database.pdb. This code is in-progress. I, the author, only have a
Palm Treo 755p (previously 700p) from Verizon so have had limited data to
test. The datasets I've been able to look at include texting both
Verizon-to-Verizon and Verizon-to-Other, which there seems to be a difference
between.
Best source of documentation I've found is
http://www.mactech.com/articles/mactech/Vol.21/21.08/PDBFile/index.html

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
  * get_location on non-windows is specific to my machine (needs fix)

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

class Message(object):
    def __init__(self, _from, to, msg, time_sent, time_received):
        self._from = _from
        self.to = to
        self.msg = msg
        self.time_sent = time_sent
        self.time_received = time_received

    def __str__(self):
        return '{} ({}): {}'.format(self._from.name, self.time_sent, self.msg)

class Contact(object):
    def __init__(self, number, name=None):
        self.number = number
        self.name = name if name is not None else special_name(number)

    def __repr__(self):
        return 'Contact("{}", "{}")'.format(self.name, self.number)

    def __eq__(self, other):
        return (self.name == other or self.number == other
            or self.name == other.name or self.number == other.number)

class MessagesDatabase(object):
    'creates a Message_Database object'
    def __init__(self, location=None):
        self.location = location if location is not None else get_location()

        with open(self.location, 'rb') as f:
            self.raw_data = f.read()

        self.__compile_re_patterns()

        try:
            owner_num = re.findall(self._owner_number_pat, self.raw_data)[0]
            self.owner = Contact('Owner', owner_number)
        except IndexError:
            self.owner = Contact('Owner', '0'*10)

        # {phone_number: Contact}
        self.contacts = {}

    def __compile_re_patterns(self):
        self._owner_number_pat = '\x000\x03\x00\x0b([0-9]+)\x00'
        self._received_pat = re.compile(
            '\0(\d{3}[\.|\-]?\d{3}[\.|\-]?\d{4})\0' # phone number
            '([\x0A\x0D\x1B-\x7E]+?)\0.{10}' # name in address book
            '(.{2})([\x0A\x0D\x1B-\x7E]+?)' # message length, and message
            '\0.\0'
            '(.{4}).{2}(.{4}).{2}(.{4})\0', #times
            )

        self._received_mms_pat = re.compile(
            '([0-9]{3}[\.|\-]?[0-9]{3}[\.|\-]?[0-9]{4})\x00'
            '([\x0A\x0D\x1B-\x7E]+).{34}(.)([\x0A\x0D\x1B-\x7E]+)\x00 \x08')

        self.__sent_pat = re.compile(
            '(.{4})...{4}.{12}' # sent time
            '(.{4}).{8}' # received time
            '(\d{3}[\.|\-]?\d{3}[\.|\-]?\d{4})\0' # phone number
            '([\x0A\x0D\x1B-\x7E]+?).{11}' # name in address book
            'Trsm.{2}(.{2})([\x0A\x0D\x1B-\x7E]+?)\0' # message length, & message
            )

    def get_contact(self, number, name=None):
        'Get a Contact; if they do not exist, creates'
        if number in self.contacts:
            return self.contacts[number]

        contact = Contact(number, name)
        self.contacts[number] = contact
        return contact

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
                                 specific_name(special_num[0])))
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
            if number == self.owner.number: continue
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

    def get_received(self, name=None, number=None, partial_name=None):
        'get_received([name, [number, [partial_name]]]) -> list of Messages'
        received = []
        for message_data in re.findall(self._received_msgs_pat, self.raw_data):
            # not at all sure about the times here; what is the third for?
            (phone_number, address_name, _, msg, sent_time, received_time,
                other_time) = message_data

            if name is not None:
                if address_name != name: continue
            elif number is not None:
                if phone_number != number: continue
            elif partial_name is not None:
                if partial_name not in address_name.lower(): continue

            sent_time = palm_epoch_to_datetime(sent_time)
            received_time = palm_epoch_to_datetime(received_time)
            _from = self.get_contact(phone_number, address_name)
            received.append(
                Message(_from, self.owner, msg, sent_time, received_time))

        #mms
        # for msgSet in re.findall(received_mms_pat, self.raw_data):
        #     number, name, msg = msgSet
        #     if who:
        #         if who not in name: continue
        #     received_msgs_sets.append((number, name, msg))
        return received

    def get_sent(self, name=None, number=None, partial_name=None):
        'get_sent([name, [number, [partial_name]]]) -> list of Messages'
        sent = []

        for message_data in re.findall(self.__sent_pat, self.raw_data):
            sent_time, received_time, phone_number, address_name, _, msg = \
                message_data

            if name is not None:
                if address_name != name: continue
            elif number is not None:
                if phone_number != number: continue
            elif partial_name is not None:
                if partial_name not in address_name.lower(): continue

            sent_time = palm_epoch_to_datetime(sent_time)
            received_time = palm_epoch_to_datetime(received_time)
            to = self.get_contact(phone_number, address_name)
            sent.append(Message(self.owner, to, msg, sent_time, received_time))

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

def get_location():
    'Try to find the Message_Database.pdb file path'
    #try cur dir first
    if os.path.isfile('Messages_Database.pdb'):
        return os.path.abspath('Messages_Database.pdb')
    if os.path.isfile('Messages Database.pdb'):
        return os.path.abspath('Messages Database.pdb')

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

def palm_epoch_to_datetime(time):
    return datetime.fromtimestamp(unpack(">I", time)[0] - PALM_EPOCHE_CONV)

def special_name(number):
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

if __name__ == '__main__':
    db = MessagesDatabase(sys.argv[1])
