#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import unittest
import datetime
import logging

from httmock import response, HTTMock

class MeetUpAttendanceTests(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def response_content(self, url, request):
        print url.geturl()
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


    def test_get_our_meetup_groups(self):
        ''' Test getting a list of all the groups we have access for '''
        from get_meetup_attendance import MeetupClient
        meetup = MeetupClient(os.environ["MEETUP_KEY"])
        with HTTMock(self.response_content):
            groups = meetup.get_our_meetup_groups()
            self.assertTrue(len(groups) == 1)
            self.assertTrue(groups[0] == 6104442)

    # Get all the meetup groups that we have permission to gather attendance for
    # for each group
        # get event ids for the last week
        # for each event
            # get attendance
                # for each attendee
                    # push to the checkin tool


if __name__ == '__main__':
    unittest.main()
