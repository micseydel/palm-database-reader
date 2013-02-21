# get someone else's Contact class?
class Contact(object):
    contacts = {}
    def __new__(cls, number, name=None):
        if number in cls.contacts:
            contact = cls.contacts[number]
            # not sure what to do with this right now
            if contact.name != name:
                print contact.name, '!=', name
                raise Exception(
                    'Contradicting contact name, {} and {} for {}'.format(
                        name, contact.name, number)
                    )
        else:
            contact = object.__new__(cls, number, name)
            cls.contacts[number] = contact
        return contact

    def __init__(self, number, name):
        self.number = number
        self.name = name if name is not None else special_name(number)

    def __str__(self):
        return '{} ({})'.format(self.name, self.number)

    def __repr__(self):
        return 'Contact("{}", "{}")'.format(self.number, self.name)

    def __eq__(self, other):
        'Returns True if they are the same contact, or for comparison to ' \
        'string when a name or number'
        return other is self or self.number == other or self.name == other

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

