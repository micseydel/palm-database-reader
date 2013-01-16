from string import printable
from itertools import izip

from palm import PalmDB

space_dict = {'\n': '\\n', '\t': '\\t', ' ': ' ', '\x0c': '\\x0c', '\x0b': '\\x0b', '\r': '\\r'}

def look_nice(char):
    if char in printable:
        if char.isspace():
            return space_dict[char]
        return char
    return '\\x{:02x}'.format(ord(char))

def hexify(string):
    return ''.join(look_nice(char) for char in string)

def build_separated_records(palm_db):
    fin = open('/home/micseydel/Treo/Messages Database.pdb')
    fout = open('test', 'w')
    fbig = open('big', 'w')
    records = [record.offset for record in palm_db.record_list]
    for this, next in izip(records[:-1], records[1:]):
        fin.seek(this)
        size = next - this
        if size > 1000:
            fbig.write('{:#x} ({})\n'.format(this, size))
            fbig.write(hexify(fin.read(size)))
            fbig.write('\n\n')
        else:
            fout.write('{:#x} ({})\n'.format(this, size))
            fout.write(hexify(fin.read(size)))
            fout.write('\n\n')
    fin.close()
    fout.close()
    fbig.close()

    print "separated", palm_db.header.num_records, "records"

def build_records_of_sizes():
    lengths = { 34: [], 70: [], 76: [] }
    with open('subdata') as f:
        for record in f.read().split('\n\n'):
            offset_length, inquestion, therest = record.strip().split('\n')
            offset, length = offset_length.split()
            really = eval('"""%s"""' % inquestion)
            lengths[len(really)].append((offset, hexify(really)))

def print_records(palm_db):
    for record in palm_db.records:
        if len(record.message) > 160: continue
        print 'Name:', record.name
        print 'Phone number:', record.phone_number
        print 'Time', record.received_time
        print 'Offset: 0x{:X}'.format(record.offset)
        print record.message
        print
        #print '{offset:#06x} name({name}) #({phone_number})'.format(
        #    **vars(record))

def make_subset_files():
    with open('subset') as fin:
        messages = fin.read().strip().split('\n\n')
    
    for message in messages:
        rcvd_sent, offset, record = message.split('\n')
        with open('messages/{}/{}'.format(rcvd_sent.strip('#'), offset), 'w') as fout:
            fout.write(record)

if __name__ == '__main__':
    palm_db = Palm_DB('lots.pdb')
    #build_separated_records(palm_db)
    #build_records_of_sizes()
    #print_records(palm_db)
    make_subset_files()
