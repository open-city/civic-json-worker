#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import unittest
import datetime

from httmock import response, HTTMock

class MeetUpAttendanceTests(unittest.TestCase):


    def setUp(self):
        from get_meetup_attendance import MeetupClient, CfAPIClient
        self.meetupclient = MeetupClient(os.environ["MEETUP_KEY"])
        with HTTMock(self.response_content):
            self.cfapiclient = CfAPIClient()


    def tearDown(self):
        pass


    def response_content(self, url, request):

        # Meetup api /groups
        if 'https://api.meetup.com/2/groups' in url.geturl():        
            return response(200, '''
                {
                    "results" : [
                        {
                            "urlname" : "hacksandhackers",
                            "self": {
                                "actions": [ ]
                            },
                            "id": 1552364
                        },
                        {
                            "urlname": "CodeForDenver",
                            "self": {
                                "role": "Organizer",
                                "actions": [ "member_approval" ]
                            },
                            "id": 6104442

                        }
                    ]
                } ''')

        # Meetup api /events
        if 'https://api.meetup.com/2/events' in url.geturl():        
            return response(200, '''  
                { "results" : 
                    [ { "name" : "Project Night", "id": "fhfqjlytlbnb", "time": 1439251200000 } ],
                    "meta" : {
                        "next" : null
                    }
                } ''')

        # Meetup api /attendance
        if 'https://api.meetup.com/CodeForDenver/events/fhfqjlytlbnb/attendance' in url.geturl():
            return response(200, ''' [ {"status": "attended", "member": { "id": 111111, "name": "TESTNAME"}, "rsvp": {"response": "yes", "guests": 0}}, {"status": "attended", "member": { "id": 222222, "name": "TESTNAME 2"}, "rsvp": {"response": "yes", "guests": 0}}] ''')

        # cfapi all orgs list
        if url.geturl() == 'https://www.codeforamerica.org/api/organizations.geojson':
            return response(200, ''' { 
                "features": [
                    {
                      "geometry": {
                        "coordinates": [
                          -104.9847, 
                          39.7392
                        ], 
                        "type": "Point"
                      }, 
                      "id": "Code-for-Denver", 
                      "properties": {
                        "all_attendance": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/attendance", 
                        "all_events": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/events", 
                        "all_issues": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/issues", 
                        "all_projects": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/projects", 
                        "all_stories": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/stories", 
                        "api_url": "http://www.codeforamerica.org/api/organizations/Code-for-Denver", 
                        "city": "Denver, CO", 
                        "events_url": "http://www.meetup.com/CodeForDenver/", 
                        "id": "Code-for-Denver", 
                        "last_updated": 1439400128, 
                        "latitude": 39.7392, 
                        "longitude": -104.9847, 
                        "name": "Code for Denver", 
                        "past_events": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/past_events", 
                        "projects_list_url": "https://github.com/codefordenver", 
                        "rss": "", 
                        "started_on": "2015-03-09", 
                        "type": "Brigade, Official", 
                        "upcoming_events": "http://www.codeforamerica.org/api/organizations/Code-for-Denver/upcoming_events", 
                        "website": "http://www.codefordenver.org/"
                      }, 
                      "type": "Feature"
                    }]
                } ''')

        if url.geturl() == 'https://www.codeforamerica.org/brigade/Code-for-Denver/checkin/':
            return response(200, ''' <p id="flash"><small style="color:#00a175" class="note"><i class="icon-checkmark"></i>Thanks for volunteering</small></p>''')


    def test_get_our_meetup_groups(self):
        ''' Test getting a list of all the groups we have access for '''
        with HTTMock(self.response_content):
            groups = self.meetupclient.fetch_groups()
            self.assertTrue(len(groups) == 1)
            self.assertTrue(groups[0]["id"] == 6104442)


    def test_get_last_weeks_events(self):
        ''' Test getting the events from the last week '''
        with HTTMock(self.response_content):
            groups = self.meetupclient.fetch_groups()
            for group in groups:
                events = self.meetupclient.fetch_events(group["id"],time_frame="-1w,")
                self.assertTrue(len(events) == 1)
                self.assertTrue(events[0]["name"] == "Project Night")
                self.assertTrue(events[0]["id"] == "fhfqjlytlbnb")


    def test_get_attendance(self):
        ''' Test getting attendance from one event '''
        with HTTMock(self.response_content):
            groups = self.meetupclient.fetch_groups()
            for group in groups:
                events = self.meetupclient.fetch_events(group,time_frame="-1w,")
                for event in events:
                    attendees = self.meetupclient.fetch_attendees(group["urlname"], event["id"])
                    self.assertTrue(len(attendees) == 2)
                    self.assertTrue("name" in attendees[0]["member"].keys())


    def test_POST_checkin(self):
        ''' Test posting checkins '''
        with HTTMock(self.response_content):
            groups = self.meetupclient.fetch_groups()
            for group in groups:
                cfapi_org = self.cfapiclient.get_cfapi_org_from_meetup_urlname(group["urlname"])
                events = self.meetupclient.fetch_events(group,time_frame="-1w,")
                for event in events:
                    attendees = self.meetupclient.fetch_attendees(group["urlname"], event["id"])
                    for attendee in attendees:
                        attendee = self.cfapiclient.format_attendee(cfapi_org, event, attendee)
                        response = self.cfapiclient.push_attendee(cfapi_org, attendee)
                        self.assertTrue(response.status_code == 200)
                        self.assertTrue("Thanks for volunteering" in response.content)


if __name__ == '__main__':
    unittest.main()
