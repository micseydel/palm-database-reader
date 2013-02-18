import sys
import re

from hack_sms import MessagesDatabase

def main():
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