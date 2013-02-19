#!/usr/bin/env python

import sys
import struct
import ctypes as c

PALM_EPOCHE_CONV = 2082844800

def get_c_string(fileobj):
    chars = []
    while True: # break when \0 encountered
        char = fileobj.read(1)
        if char == '\0':
            break
        chars.append(char)
    return "".join(chars)

class PalmDB(object):
    "An entire Palm Database; a file"
    def __init__(self, filename):
        self.filename = filename
        with open(filename) as f:
            self.header = PDBHeader(f.read(0x4e))
            self.record_list = [PDBRecordHeader(f.read(8))
                for x in xrange(self.header.num_records)]
            f.read(2) #no idea what this is
            self.records = self._get_records(f)

    def _get_records(self, file_object):
        return [PDBRecord(file_object, record.offset)
            for record in self.record_list]

class PDBHeader(c.Structure):
    "The header for a palm database, the 78 bytes"
    _fields_ = [
        ("name", c.c_char_p),
        ("file_attys", c.c_ushort),
        ("version", c.c_ushort),
        ("creation_time", c.c_uint),
        ("mod_time", c.c_uint),
        ("backup_time", c.c_uint),
        ("mod_num", c.c_uint),
        ("app_info", c.c_uint),
        ("sort_info", c.c_uint),
        ("type", c.c_uint),
        ("creator", c.c_uint),
        ("unique_id", c.c_uint),
        ("next_record_list", c.c_uint),
        ("num_records", c.c_ushort)
    ]
    _format = struct.Struct(">32sHHIIIIIIIIIIH")

    def __init__(self, packed_string):
        super(type(self), self).__init__(*self._format.unpack(packed_string))

        #let us use regular time
        self.creation_time -= PALM_EPOCHE_CONV
        self.mod_num -= PALM_EPOCHE_CONV
        self.backup_time -= PALM_EPOCHE_CONV

class PDBRecordHeader(c.Structure):
    "The offset seems to be the only thing of importance here"
    _fields_ = [
        ("offset", c.c_uint),
        ("attys", c.c_char), #always seems to be @
        ("unique_id", c.c_char_p) #documentation says this should always be 0
    ]
    _format = struct.Struct(">Ic3s")
    def __init__(self, packed_string):
        super(type(self), self).__init__(*self._format.unpack(packed_string))
    
    def __repr__(self):
        return "PDBRecordHeader(offset=0x{:X}, attys={})".format(
            self.offset, self.attys)

# this may vary wildly!
class PDBRecord(object):
    "TBI"
    format = struct.Struct(">I")
    def __init__(self, f, offset):
        f.seek(offset)
        f.read(10)
        print "0x{:X}".format(offset)
        if f.read(1) == "@": # received
            #print "received? 1"
            f.read(23)
            phone_number = get_c_string(f)
            name = get_c_string(f)
            f.read(3)
            t1 = f.read(4)
            f.read(2)
            t2 = f.read(4)
            f.read(2)
            t3 = f.read(4)
        else: # sent
            if f.read(1) == "\x02": # sent
                #print "sent? 01"
                f.read(23)
                sent_time = f.read(4)
                f.read(18)
                received_time = f.read(4)
                f.read(8)
                #f.read(57) # there might be something useful here
                some_number = ord(f.read(1))
                phone_number = get_c_string(f)
                name = get_c_string(f)
            else: # sent
                #print "sent? 11"
                f.read(29)
                sent_time = f.read(4)
                f.read(18)
                received_time = f.read(4)
                f.read(8)
                #f.read(63) # might be something useful
                some_number = ord(f.read(1))
                phone_number = get_c_string(f)
                name = get_c_string(f)
            f.read(17) # might be useful here

        vars(self).update(locals())

if __name__ == "__main__":
    palm_db = PalmDB(sys.argv[1])
