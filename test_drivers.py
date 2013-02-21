from hack_sms import MessagesDatabase

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
    database = MessagesDatabase('Messages_Database_noPics.pdb')
    msgs = []
    msgs.extend(database.get_received())
    msgs.extend(
        map(lambda x: x[:2] + ("Michael Seydel",) + x[-1:],
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
    database = MessagesDatabase('Messages_Database_noPics.pdb')
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
    chars = list(f.read(bytes_to_check) if bytes_to_check else f.read())
    f.close()

    curr = [chars.pop(0) for x in xrange(2)]
    while chars:
        thisNum = struct.unpack(">H", ''.join(curr))[0]
        if thisNum >= number - tolerance and thisNum <= number + tolerance:
            print '%02X %02X' % tuple(ord(char) for char in curr),
        curr.pop(0)
        curr.append(chars.pop(0))
        offset += 1

