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
                            "name" : "Hacks and Hackers",
                            "self": {
                                "actions": [ ]
                            },
                            "id": 1552364
                        },
                        {
                            "name": "Code for Denver",
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


    def test_get_our_meetup_groups(self):
        ''' Test getting a list of all the groups we have access for '''

        with HTTMock(self.response_content):
            groups = self.meetupclient.get_our_meetup_groups()
            self.assertTrue(len(groups) == 1)
            self.assertTrue(groups[0] == 6104442)


    def test_get_last_weeks_events(self):
        ''' Test getting the events from the last week '''
        with HTTMock(self.response_content):
            groupsids = self.meetupclient.get_our_meetup_groups()
            for groupid in groupsids:
                events = self.meetupclient.fetch_events(groupid,time_frame="-1w,")
                self.assertTrue(len(events) == 1)
                self.assertTrue(events[0]["name"] == "Project Night")
                self.assertTrue(events[0]["id"] == "fhfqjlytlbnb")



    # Get all the meetup groups that we have permission to gather attendance for
    # for each group
        # get event ids for the last week
        # for each event
            # get attendance
                # for each attendee
                    # push to the checkin tool


if __name__ == '__main__':
    unittest.main()
