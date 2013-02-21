#!/usr/bin/env python
#hack_sms.py

import os
import sys
import string
import re
from struct import unpack
from datetime import datetime

from contact import Contact

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

Best source of documentation I've found is
http://www.mactech.com/articles/mactech/Vol.21/21.08/PDBFile/index.html
'''

PALM_EPOCHE_CONV = 2082844800

class Message(object):
    def __init__(self, sender, receiver, msg, time_sent, time_received):
        self.sender = sender
        self.receiver = receiver
        self.msg = msg
        self.time_sent = time_sent
        self.time_received = time_received

    def __eq__(self, other):
        'Messages considered equal when all fields are equal'
        try:
            return all(getattr(self, field) == getattr(other, field) for field
                in ('sender', 'receiver', 'msg', 'time_sent', 'time_received'))
        except AttributeError:
            return False
        # return (self.sender == other.sender and self.receiver == other.receiver
        #     and self.msg == other.msg and self.time_sent == other.time_sent
        #     and self.time_received == other.time_received)

    def __hash__(self):
        return hash('{}{}{}'.format(self.sender, self.receiver, self.msg)) + \
            hash(self.time_sent) + hash(self.time_received)

    def __str__(self):
        '<sender> (<time>): <msg>'
        return '{} ({}): {}'.format(self.sender.name, self.time_sent, self.msg)

    def __lt__(self, other):
        return self.time_sent < other.time_sent

    def __gt__(self, other):
        return self.time_sent > other.time_sent

    def __contains__(self, string):
        return string in self.msg

class MessagesDatabase(object):
    'creates a MessageDatabase object'
    def __init__(self, location=None):
        self.location = location if location is not None else get_location()

        with open(self.location, 'rb') as f:
            self.raw_data = f.read()

        self._compile_re_patterns()

        try:
            owner_num = re.findall(self._owner_number_pat, self.raw_data)[0]
            self.owner = Contact(owner_num, 'Owner')
        except IndexError:
            self.owner = Contact('0'*10, 'Owner')

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
        '''get_received([name, [number, [partial_name]]]) -> list of Messages
        number is a string, and partial_name is expected to be lowercase'''
        received = []
        for message_data in re.findall(self._received_pat, self.raw_data):
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
            _from = Contact(phone_number, address_name)
            msg = Message(_from, self.owner, msg, sent_time, received_time)
            msg.other_time = palm_epoch_to_datetime(other_time)
            received.append(msg)

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
            to = Contact(phone_number, address_name)
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

if __name__ == '__main__':
    db = MessagesDatabase(sys.argv[1])
