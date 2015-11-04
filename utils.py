from datetime import datetime

def is_safe_name(name):
    ''' Return True if the string is a safe name.
    '''
    return raw_name(safe_name(name)) == name

def safe_name(name):
    ''' Return URL-safe organization name with spaces replaced by dashes.

        Slashes will be removed, which is incompatible with raw_name().
    '''
    return name.replace(' ', '-').replace('/', '-').replace('?', '-').replace('#', '-')

def raw_name(name):
    ''' Return raw organization name with dashes replaced by spaces.

        Also replace old-style underscores with spaces.
    '''
    return name.replace('_', ' ').replace('-', ' ')

def convert_datetime_to_iso_8601(dt):
    ''' Convert the passed datetime object to ISO 8601 format
    '''
    if not dt or type(dt) is not datetime:
        return None

    iso_string = unicode(dt.isoformat())

    # add a 'Z' (representing the UTC time zone) to the end if there's no explicit time zone set
    if not dt.tzinfo:
        iso_string = u'{}Z'.format(iso_string.rstrip(u'Z'))

    return iso_string
