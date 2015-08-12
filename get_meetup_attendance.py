#! /usr/bin/env python
from datetime import datetime
import logging
import os
import requests
from argparse import ArgumentParser
from urlparse import urlparse

class MeetupClient(object):
    """Very basic client class for fetching event/attendee data.
    """

    def __init__(self, api_key=None):
        """
        :param api_key: Key used to authenticate the request to Meetup's API.
            See https://secure.meetup.com/meetup_api/key/. Required if `url` is
            not provided.
        """
        self.api_key = api_key


    def fetch_groups(self, meetup_name=None):
        ''' Get a list of groups we have permission to get attendance from '''

        # Found right url to use at https://github.com/meetup/api/issues/81#issuecomment-94778457
        url = 'https://api.meetup.com/2/groups'
        params = {
            'member_id' : 'self',
            'fields' : 'self',
            'only' : 'id,urlname,self',
            'key': self.api_key
        }

        all_groups = requests.get(url, params=params).json()
        # Get the list of groups we have permission for
        organizer_groups = []
        for group in all_groups["results"]:
            # If a meetup_name is given, just return that group
            if meetup_name:
                if meetup_name == group["urlname"]:
                    return [group]
            if "member_approval" in group["self"]["actions"]:
                organizer_groups.append(group)

        return organizer_groups


    def fetch_events(self, group_id, time_frame="-1d", url=None):
        """ Fetch recent Brigade events from Meetup

        :param time_frame: Period of time to fetch events from. Matchs Meetup's
            time format: `<beginning>,<end>`, with either being absolute time
            in milliseconds since the Unix epoch, or relative dates e.g. `1m`
            or `-1w`. 

        :return: List of events
        :rtype: List of dictionaries

        Usage::
            # Fetch events from the last week
            meetup_client = MeetupCient('OpenTwinCities', 'OurKey')
            events = meetup_client.fetch_events('-1w,')
            for event in events:
                print "Event ID:" + event['id']
                print "Event Name:" + event['name']
                print "Event DateTime" + datetime.fromtimestamp(
                    event['time']/1000.0).strftime('%Y-%m-%d %H:%M:%S')

        """

        if url is None:
            if group_id is None or type(group_id) != int:
                raise ValueError('group_id must be provided if not providing '
                                 'url') 

            # Using Meetup V2 Events API
            # http://www.meetup.com/meetup_api/docs/2/events/
            url = 'https://api.meetup.com/2/events'
            params = {
                'group_id': group_id,
                'time': time_frame,
                'status': 'past',
                'only' : 'id,name,time',
                'page': 20,
                'key': self.api_key
            }
        else:
            params = None

        # Note the differnce in how V2 and V3 handle next links.
        # In V2, 'next' is part of the body.
        r = requests.get(url, params=params).json()
        events = r['results']
        if r['meta']['next']:
            events += self.fetch_events(url=r['meta']['next'])
        return events


    def fetch_attendees(self, group_urlname=None, event_id=None, url=None):
        """Fetch the attendees of a specific event

        :param event_id: Meetup ID string for the event to fetch attendees of.
            Required if `url` is not provided.
        :param url: If provided, the url that will be called to fetch
            attendees. If not provided, then the url will be constructed based
            on `event_id`, `group_urlname`, and `api_key`.
        :return: List of attendees
        :rtype: List of dictionaries

        Usage::
            # Fetch attendees for event with ID '12345abcd'
            meetup_client = MeetupCient('OpenTwinCities', 'OurKey')
            attendees = meetup_client.fetch_events('12345abcd')
            for attendee in attendees:
                print "Attendee Name:" + attendee['member']['name']

        """

        if url is None:
            if event_id is None:
                raise ValueError('event_id must be provided if not providing '
                                 'url')
            # Using Meetup V3 Attendance API
            # http://www.meetup.com/meetup_api/docs/:urlname/events/:id/attendance/
            url = (
                'https://api.meetup.com/%(group_urlname)s'
                '/events/%(event_id)s/attendance' % {
                    'group_urlname': group_urlname,
                    'event_id': event_id
                }
            )
            params = {
                'sign': 'true',
                'filter': 'attended',
                'page': 50,
                'key': self.api_key
            }
        else:
            params = None

        # Note the differnce in how V2 and V3 handle next links.
        # In V3, 'next' is a link header.
        r = requests.get(url, params=params)
        attendees = r.json()
        if 'next' in r.links:
            attendees += self.fetch_attendees(url=r.links['next']['url'])
        return attendees


class CfAPIClient(object):
    """Very basic client class for pushing attendee data.
    """

    def __init__(self):
        self.cfapi_meetup_matches = self.match_org_to_meetup()

    # @property
    # def org_url(self):
    #     return (
    #         'https://www.codeforamerica.org/api/organizations/' + self.org_id
    #     )

    def match_org_to_meetup(self):
        ''' Get a list of org_ids and meetup_urlnames '''
        orgs = requests.get('https://www.codeforamerica.org/api/organizations.geojson').json()
        cfapi_meetup_matches = []
        for org in orgs["features"]:
            _, host, path, _, _, _ = urlparse(org["properties"]["events_url"])
            if 'meetup.com' in host:
                cfapi_meetup = {
                    "cfapi_org" : {
                        "url" : org["properties"]["api_url"].replace("http://","https://"),
                        "id" : org["properties"]["id"]
                    },
                    "meetup_urlname" : path.replace("/","")
                }
                cfapi_meetup_matches.append(cfapi_meetup)

        return cfapi_meetup_matches


    def get_cfapi_org_from_meetup_urlname(self, group_urlname):
        ''' Get the cfapi_org_url from a groups meetup urlname '''
        for org in self.cfapi_meetup_matches:
            if org["meetup_urlname"] == group_urlname:
                return org["cfapi_org"]


    def format_attendee(self, cfapi_org, event, attendee):
        ''' Format attendee '''
        expected_format = {
            "name" : attendee["member"]["name"],
            "event" : event["name"],
            "date" : str(datetime.utcfromtimestamp(event['time']/1000.0)),
            "cfapi_url" : cfapi_org["url"]
        }
        return expected_format


    def push_attendee(self, cfapi_org, attendee):
        url = (
            'https://www.codeforamerica.org/brigade/%(cfapi_org_id)s/checkin/' %
            {
                'cfapi_org_id': cfapi_org["id"]
            }
        )

        response = requests.post(url, data=attendee)
        return response


parser = ArgumentParser(description=''' Pulling attendance data from Meetup ''')
parser.add_argument('--meetup-name', dest='meetup_name', help='A single Meetup group to update')
parser.add_argument('--time', dest='time_frame', help='How far back to update. Default is "-1w"')


if __name__ == '__main__':

    logger = logging.getLogger('CfAPI_Attendance_Sync')
    logger.setLevel(logging.INFO)

    args = parser.parse_args()
    time_frame = args.time_frame or '-1w'
    api_key = os.environ['MEETUP_KEY']

    # Get all the meetup groups that we have permission to gather attendance for
    # for each group
        # get event ids for the last week
        # for each event
            # get attendance
                # for each attendee
                    # push to the checkin tool



    # cfapi_client = CfAPIClient(cfapi_org_id)
    # meetup_client = MeetupClient(group_urlname, api_key)
    # events = meetup_client.fetch_events(time_frame)
    # logging.info('Fetched %d events from Meetup' % len(events))
    # for event in events:
    #     print event
    #     event_name = event['name']
    #     event_date = str(datetime.utcfromtimestamp(event['time']/1000.0))
    #     logger.info("Event ID: " + event['id'])
    #     logger.info("Event Name: " + event_name)
    #     logger.info("Event DateTime: " + event_date)
    #     attendees = meetup_client.fetch_attendees(event['id'])
    #     print attendees
    #     logger.info("\tFetc hed %d attendees" % len(attendees))
    #     for attendee in attendees:
    #         attendee_name = attendee['member']['name']
    #         logger.info("\tAttendee Name: " + attendee_name)
    #         cfapi_client.push_attendee({
    #             'name': attendee_name,
    #             'email' : 'test@test.com',
    #             'event': event_name,
    #             'date': event_date
    #         })
