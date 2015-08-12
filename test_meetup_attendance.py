#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import unittest
import datetime
import logging

from httmock import response, HTTMock

class MeetUpAttendanceTests(unittest.TestCase):


    def setUp(self):
        from get_meetup_attendance import MeetupClient
        self.meetupclient = MeetupClient(os.environ["MEETUP_KEY"])


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
                    [ { "name" : "Project Night", "id": "fhfqjlytlbnb" } ],
                    "meta" : {
                        "next" : null
                    }
                } ''')

        # Meetup api /attendance
        if 'https://api.meetup.com/CodeForDenver/events/fhfqjlytlbnb/attendance' in url.geturl():
            return response(200, ''' [ {"status": "attended", "member": { "id": 111111, "name": "TESTNAME"}, "rsvp": {"response": "yes", "guests": 0}}, {"status": "attended", "member": { "id": 222222, "name": "TESTNAME 2"}, "rsvp": {"response": "yes", "guests": 0}}] ''')


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



    # Get all the meetup groups that we have permission to gather attendance for
    # for each group
        # get event ids for the last week
        # for each event
            # get attendance
                # for each attendee
                    # push to the checkin tool


if __name__ == '__main__':
    unittest.main()
