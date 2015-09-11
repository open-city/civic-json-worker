#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import unittest
import datetime
import logging
import time
import json
from re import match, search, sub

from httmock import response, HTTMock
from mock import Mock

from psycopg2 import connect, extras

root_logger = logging.getLogger()
root_logger.disabled = True

class FakeResponse:
    def __init__(self, text):
        self.text = text

class RunUpdateTestCase(unittest.TestCase):

    # change to modify the number of mock organizations returned
    organization_count = 3
    # change to switch between before and after states for results
    # 'after' state returns fewer events,stories,projects,issues,labels
    results_state = 'before'

    def setUp(self):
        os.environ['DATABASE_URL'] = 'postgres:///civic_json_worker_test'
        os.environ['SECRET_KEY'] = '123456'
        os.environ['MEETUP_KEY'] = 'abcdef'
        os.environ["PEOPLEDB"] = 'postgres:///peopledbtest'

        from app import db

        self.db = db
        self.db.create_all()

        import run_update
        run_update.github_throttling = False

        # FAKE PEOPLEDB
        with connect(os.environ["PEOPLEDB"]) as conn:
            with conn.cursor() as db:
                with open('test/peopledbtest-destroy.pgsql') as filename:
                    db.execute(filename.read())
                with open('test/peopledbtest.pgsql') as filename:
                    db.execute(filename.read())

    def tearDown(self):
        self.db.session.close()
        self.db.drop_all()

        with connect('postgres:///peopledbtest') as conn:
            with conn.cursor() as db:
                with open('test/peopledbtest-destroy.pgsql') as filename:
                    db.execute(filename.read())

    def setup_mock_rss_response(self):
        ''' This overwrites urllib2.urlopen to return a mock response, which stops
            get_first_working_feed_link() in feeds.py from pulling data from the
            internet
        '''

        import urllib2

        rss_file = open('blog.xml')
        rss_content = rss_file.read()
        rss_file.close()
        urllib2.urlopen = Mock()
        urllib2.urlopen.return_value.read = Mock(return_value=rss_content)
        return urllib2.urlopen

    def get_raw_organization_list(self, count=3):
        if type(count) is not int:
            count = 3
        # 'https://github.com/codeforamerica' and 'https://www.github.com/orgs/codeforamerica' are transformed
        #  to 'https://api.github.com/users/codeforamerica/repos' in run_update/get_projects()
        lines = [u'''name,website,events_url,rss,projects_list_url'''.encode('utf8'), u'''Cöde for Ameriça,http://codeforamerica.org,http://www.meetup.com/events/Code-For-Charlotte/,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv'''.encode('utf8'), u'''Code for America (2),,,,https://github.com/codeforamerica'''.encode('utf8'), u'''Code for America (3),,http://www.meetup.com/events/Code-For-Rhode-Island/,http://www.codeforamerica.org/blog/another/feed/,https://www.github.com/orgs/codeforamerica'''.encode('utf8')]
        return '\n'.join(lines[0:count + 1])

    def response_content(self, url, request):
        # csv file of project descriptions
        if url.geturl() == 'http://example.com/cfa-projects.csv':
            project_lines = ['''Name,description,link_url,code_url,type,categories,tags,status''', ''',,,https://github.com/codeforamerica/cityvoice,,,"safety, police, poverty",Shuttered''', ''',,,https://github.com/codeforamerica/bizfriendly-web,,,,''']

            if self.results_state == 'before':
                return response(200, '''\n'''.join(project_lines[0:3]), {'content-type': 'text/csv; charset=UTF-8'})
            elif self.results_state == 'after':
                return response(200, '''\n'''.join(project_lines[0:2]), {'content-type': 'text/csv; charset=UTF-8'})

        # json of project descriptions
        elif url.geturl() == 'https://api.github.com/users/codeforamerica/repos':
            return response(200, '''[{ "id": 10515516, "name": "cityvoice", "owner": { "login": "codeforamerica", "avatar_url": "https://avatars.githubusercontent.com/u/337792", "html_url": "https://github.com/codeforamerica", "type": "Organization"}, "html_url": "https://github.com/codeforamerica/cityvoice", "description": "A place-based call-in system for gathering and sharing community feedback",  "url": "https://api.github.com/repos/codeforamerica/cityvoice", "contributors_url": "https://api.github.com/repos/codeforamerica/cityvoice/contributors", "created_at": "2013-06-06T00:12:30Z", "updated_at": "2014-02-21T20:43:16Z", "pushed_at": "2014-02-21T20:43:16Z", "homepage": "http://www.cityvoiceapp.com/", "stargazers_count": 10, "watchers_count": 10, "language": "Ruby", "forks_count": 12, "open_issues": 37 }]''', headers=dict(Link='<https://api.github.com/user/337792/repos?page=2>; rel="next", <https://api.github.com/user/337792/repos?page=2>; rel="last"'))

        # csv file of organization descriptions
        # this catches the request for the URL contained in run_update.TEST_ORG_SOURCES_FILENAME
        elif "docs.google.com" in url:
            return response(200, self.get_raw_organization_list(self.organization_count))

        # contents of civic.json file in root directory for cityvoice
        elif "cityvoice/contents/civic.json" in url.geturl():
            return response(200, '''{"status": "Beta", "tags": ["mapping", "transportation", "community organizing"]}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})

        # contents of civic.json file in root directory for bizfriendly-web
        elif "bizfriendly-web/contents/civic.json" in url.geturl():
            return response(404, '''Not Found!''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})

        # json of github directory contents for cityvoice (has civic.json)
        elif search(r'cityvoice\/contents\/$', url.geturl()):
            return response(200, '''[{"name": "civic.json", "path": "civic.json", "sha": "01a16ec5902e04c170c648c0ff65cb0210468e96", "size": 82, "url": "https://api.github.com/repos/codeforamerica/cityvoice/contents/civic.json?ref=master", "html_url": "https://github.com/codeforamerica/cityvoice/blob/master/civic.json", "git_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs/01a16ec5902e04c170c648c0ff65cb0210468e96", "download_url": "https://raw.githubusercontent.com/codeforamerica/cityvoice/master/civic.json", "type": "file", "_links": {"self": "https://api.github.com/repos/codeforamerica/cityvoice/contents/civic.json?ref=master", "git": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs/01a16ec5902e04c170c648c0ff65cb0210468e96", "html": "https://github.com/codeforamerica/cityvoice/blob/master/civic.json"}}]''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})

        # json of github directory contents for bizfriendly-web (no civic.json)
        elif search(r'bizfriendly-web\/contents\/$', url.geturl()):
            return response(200, '''[{"name": "civic-not.json", "path": "civic-not.json", "sha": "01a16ec5902e04c170c648c0ff65cb0210468e96", "size": 82, "url": "https://api.github.com/repos/codeforamerica/cityvoice/contents/civic-not.json?ref=master", "html_url": "https://github.com/codeforamerica/cityvoice/blob/master/civic-not.json", "git_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs/01a16ec5902e04c170c648c0ff65cb0210468e96", "download_url": "https://raw.githubusercontent.com/codeforamerica/cityvoice/master/civic-not.json", "type": "file", "_links": {"self": "https://api.github.com/repos/codeforamerica/cityvoice/contents/civic-not.json?ref=master", "git": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs/01a16ec5902e04c170c648c0ff65cb0210468e96", "html": "https://github.com/codeforamerica/cityvoice/blob/master/civic-not.json"}}]''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})

        # json of project description (cityvoice)
        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
            return response(200, '''{ "id": 10515516, "name": "cityvoice", "owner": { "login": "codeforamerica", "avatar_url": "https://avatars.githubusercontent.com/u/337792", "html_url": "https://github.com/codeforamerica", "type": "Organization"}, "html_url": "https://github.com/codeforamerica/cityvoice", "description": "A place-based call-in system for gathering and sharing community feedback",  "url": "https://api.github.com/repos/codeforamerica/cityvoice", "contributors_url": "https://api.github.com/repos/codeforamerica/cityvoice/contributors", "created_at": "2013-06-06T00:12:30Z", "updated_at": "2014-02-21T20:43:16Z", "pushed_at": "2014-02-21T20:43:16Z", "homepage": "http://www.cityvoiceapp.com/", "stargazers_count": 10, "watchers_count": 10, "language": "Ruby", "forks_count": 12, "open_issues": 37 }''', {'last-modified': datetime.datetime.strptime('Fri, 15 Nov 2013 00:08:07 GMT', "%a, %d %b %Y %H:%M:%S GMT")})

        # json of project description (bizfriendly-web)
        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/bizfriendly-web':
            return response(200, ''' { "id": 11137392, "name": "bizfriendly-web", "owner": { "login": "codeforamerica", "avatar_url": "https://avatars.githubusercontent.com/u/337792?v=3", "html_url": "https://github.com/codeforamerica", "type": "Organization" }, "html_url": "https://github.com/codeforamerica/bizfriendly-web", "description": "An online service that teaches small business owners how to use the internet to better run their businesses.", "url": "https://api.github.com/repos/codeforamerica/bizfriendly-web", "contributors_url": "https://api.github.com/repos/codeforamerica/bizfriendly-web/contributors", "created_at": "2013-07-02T23:14:10Z", "updated_at": "2014-11-02T18:55:33Z", "pushed_at": "2014-10-14T21:55:04Z", "homepage": "http://bizfriend.ly", "stargazers_count": 17, "watchers_count": 17, "language": "JavaScript", "forks_count": 21, "open_issues": 31 } ''', {'last-modified': datetime.datetime.strptime('Fri, 15 Nov 2013 00:08:07 GMT', "%a, %d %b %Y %H:%M:%S GMT")})

        # json of project contributors (cityvoice)
        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/contributors' or url.geturl() == 'https://api.github.com/repos/codeforamerica/bizfriendly-web/contributors':
            return response(200, '''[ { "login": "daguar", "avatar_url": "https://avatars.githubusercontent.com/u/994938", "url": "https://api.github.com/users/daguar", "html_url": "https://github.com/daguar", "contributions": 518 } ]''')

        # json of project participation (cityvoice)
        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/stats/participation' or url.geturl() == 'https://api.github.com/repos/codeforamerica/bizfriendly-web/stats/participation':
            return response(200, '''{ "all": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 23, 9, 4, 0, 77, 26, 7, 17, 53, 59, 37, 40, 0, 47, 59, 55, 118, 11, 8, 3, 3, 30, 0, 1, 1, 4, 6, 1, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1 ], "owner": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ] }''')

        # json of project issues (cityvoice, bizfriendly-web)
        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/issues' or url.geturl() == 'https://api.github.com/repos/codeforamerica/bizfriendly-web/issues':
            # build issues dynamically based on results_state value
            issue_lines = ['''{"html_url": "https://github.com/codeforamerica/cityvoice/issue/210","title": "Important cityvoice issue", "labels": [ xxx ], "body" : "WHATEVER"}''', '''{"html_url": "https://github.com/codeforamerica/cityvoice/issue/211","title": "More important cityvoice issue", "labels": [ xxx ], "body" : "WHATEVER"}''']
            label_lines = ['''{ "color" : "84b6eb", "name" : "enhancement", "url": "https://api.github.com/repos/codeforamerica/cityvoice/labels/enhancement"}''', '''{ "color" : "84b6eb", "name" : "question", "url": "https://api.github.com/repos/codeforamerica/cityvoice/labels/question"}''']
            issue_lines_before = [sub('xxx', ','.join(label_lines[0:2]), issue_lines[0]), sub('xxx', ','.join(label_lines[0:2]), issue_lines[1])]
            issue_lines_after = [sub('xxx', ','.join(label_lines[0:1]), issue_lines[0])]
            response_etag = {'ETag': '8456bc53d4cf6b78779ded3408886f82'}

            if self.results_state == 'before':
                return response(200, ''' [ ''' + ', '.join(issue_lines_before) + ''' ] ''', response_etag)
            if self.results_state == 'after':
                return response(200, ''' [ ''' + ', '.join(issue_lines_after) + ''' ] ''', response_etag)

        # json of contributor profile
        elif url.geturl() == 'https://api.github.com/users/daguar':
            return response(200, '''{ "login": "daguar", "avatar_url": "https://gravatar.com/avatar/whatever", "html_url": "https://github.com/daguar", "name": "Dave Guarino", "company": "", "blog": null, "location": "Oakland, CA", "email": "dave@codeforamerica.org",  }''')

        # json of page two of project descriptions (empty)
        elif url.geturl() == 'https://api.github.com/user/337792/repos?page=2':
            return response(200, '''[ ]''', headers=dict(Link='<https://api.github.com/user/337792/repos?page=1>; rel="prev", <https://api.github.com/user/337792/repos?page=1>; rel="first"'))

        # elif meetup member count
        elif 'https://api.meetup.com/2/groups?group_urlname=' in url.geturl():
            return response(200, ''' { "results" : [ { "members" : 100 } ] } ''')

        # json of meetup events
        elif 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=' in url.geturl() and 'Code-For-Charlotte' in url.geturl():
            events_filename = 'meetup_events.json'
            if self.results_state == 'after':
                events_filename = 'meetup_events_fewer.json'

            events_file = open(events_filename)
            events_content = events_file.read()
            events_file.close()
            return response(200, events_content)

        # json of alternate meetup events
        elif 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=' in url.geturl() and 'Code-For-Rhode-Island' in url.geturl():
            events_file = open('meetup_events_another.json')
            events_content = events_file.read()
            events_file.close()
            return response(200, events_content)

        # xml of blog feed (stories)
        elif url.geturl() == 'http://www.codeforamerica.org/blog/feed/' or match(r'http:\/\/.+\.rss', url.geturl()):
            stories_filename = 'blog.xml'
            if self.results_state == 'after':
                stories_filename = 'blog_fewer.xml'

            stories_file = open(stories_filename)
            stories_content = stories_file.read()
            stories_file.close()
            return response(200, stories_content)

        # xml of alternate blog feed (stories)
        elif url.geturl() == 'http://www.codeforamerica.org/blog/another/feed/':
            stories_file = open('blog_another.xml')
            stories_content = stories_file.read()
            stories_file.close()
            return response(200, stories_content)

        # csv of projects (philly)
        elif url.geturl() == 'http://codeforphilly.org/projects.csv':
            return response(200, '''"name","description","link_url","code_url","type","categories","tags","status"\r\n"OpenPhillyGlobe","\"Google Earth for Philadelphia\" with open source and open transit data.","http://cesium.agi.com/OpenPhillyGlobe/","http://google.com","","","",""''', {'content-type': 'text/csv; charset=UTF-8'})

        # csv of projects (austin)
        elif url.geturl() == 'http://openaustin.org/projects.csv':
            return response(200, '''name,description,link_url,code_url,type,categories,tags,status\nHack Task Aggregator,"Web application to aggregate tasks across projects that are identified for ""hacking"".",,,web service,"project management, civic hacking",,In Progress''', {'content-type': 'text/csv; charset=UTF-8'})

        else:
            raise Exception('Asked for unknown URL ' + url.geturl())

    def test_import(self):
        ''' Add one sample organization with two projects and issues, verify that it comes back.
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if "/contents/civic.json" in url.geturl():
                return response(404, '''Not Found!''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})
            elif search(r'\/contents\/$', url.geturl()):
                return response(200, '''[{"name": "civic-not.json"}]''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        self.db.session.flush()

        from app import Organization, Project, Issue

        # check for the one organization
        filter = Organization.name == u'Cöde for Ameriça'
        organization = self.db.session.query(Organization).filter(filter).first()
        self.assertIsNotNone(organization)
        self.assertEqual(organization.name, u'Cöde for Ameriça')

        # check for the one project
        filter = Project.name == u'bizfriendly-web'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.name, u'bizfriendly-web')

        # check for the one project status
        filter = [Project.organization_name == u'Cöde for Ameriça', Project.name == u'cityvoice']
        project = self.db.session.query(Project).filter(*filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'Shuttered')

        # check for the other project
        filter = Project.name == u'cityvoice'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.name, u'cityvoice')

        # check for cityvoice project's issues
        filter = Issue.project_id == project.id
        issue = self.db.session.query(Issue).filter(filter).first()
        self.assertIsNotNone(issue)
        self.assertEqual(issue.title, u'More important cityvoice issue')

    def test_main_with_good_new_data(self):
        ''' When current organization data is not the same set as existing, saved organization data,
            the new organization, its project, and events should be saved. The out of date
            organization, its project and event should be deleted.
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory, ProjectFactory, EventFactory, IssueFactory

        old_organization = OrganizationFactory(name=u'Old Organization')
        old_project = ProjectFactory(name=u'Old Project', organization_name=u'Old Organization')
        old_event = EventFactory(name=u'Old Event', organization_name=u'Old Organization')
        old_issue = IssueFactory(title=u'Old Issue', project_id=1)
        self.db.session.flush()

        with HTTMock(self.response_content):
            import run_update
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        self.db.session.flush()

        from app import Organization, Project, Event, Issue

        # make sure old org is no longer there
        filter = Organization.name == u'Old Organization'
        organization = self.db.session.query(Organization).filter(filter).first()
        self.assertIsNone(organization)

        # make sure old project is no longer there
        filter = Project.name == u'Old Project'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNone(project)

        # make sure the old issue is no longer there
        filter = Issue.title == u'Old Issue'
        issue = self.db.session.query(Issue).filter(filter).first()
        self.assertIsNone(issue)

        # make sure old event is no longer there
        filter = Event.name == u'Old Event'
        event = self.db.session.query(Event).filter(filter).first()
        self.assertIsNone(event)

        # check for the one organization
        filter = Organization.name == u'Cöde for Ameriça'
        organization = self.db.session.query(Organization).filter(filter).first()
        self.assertEqual(organization.name, u'Cöde for Ameriça')

        # check for the one project
        filter = Project.name == u'bizfriendly-web'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertEqual(project.name, u'bizfriendly-web')

        # check for the one issue
        filter = Issue.title == u'Important cityvoice issue'
        issue = self.db.session.query(Issue).filter(filter).first()
        self.assertEqual(issue.title, u'Important cityvoice issue')

        # check for events
        filter = Event.name.in_([u'Organizational meeting',
                                 u'Code Across: Launch event',
                                 u'Brigade Ideation (Brainstorm and Prototyping) Session.'])
        events = self.db.session.query(Event).filter(filter).all()

        first_event = events.pop(0)
        # Thu, 16 Jan 2014 19:00:00 -05:00
        self.assertEqual(first_event.utc_offset, -5 * 3600)
        self.assertEqual(first_event.start_time_notz, datetime.datetime(2014, 1, 16, 19, 0, 0))
        self.assertEqual(first_event.name,u'Organizational meeting')

        second_event = events.pop(0)
        # Thu, 20 Feb 2014 18:30:00 -05:00
        self.assertEqual(first_event.utc_offset, -5 * 3600)
        self.assertEqual(second_event.start_time_notz, datetime.datetime(2014, 2, 20, 18, 30, 0))
        self.assertEqual(second_event.name, u'Code Across: Launch event')

        third_event = events.pop(0)
        # Wed, 05 Mar 2014 17:30:00 -05:00
        self.assertEqual(first_event.utc_offset, -5 * 3600)
        self.assertEqual(third_event.start_time_notz, datetime.datetime(2014, 3, 5, 17, 30, 0))
        self.assertEqual(third_event.name, u'Brigade Ideation (Brainstorm and Prototyping) Session.')

    def test_main_with_missing_projects(self):
        ''' When github returns a 404 when trying to retrieve project data,
            an error message should be logged.
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(404, '''Not Found!''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/issues':
                return response(404, '''Not Found!''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})

        logging.error = Mock()

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        logging.error.assert_called_with('https://api.github.com/repos/codeforamerica/cityvoice doesn\'t exist.')

    def test_main_with_github_errors(self):
        ''' When github returns a non-404 error code, an IOError should be raised.
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(422, '''Unprocessable Entity''')

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                self.assertFalse(run_update.github_throttling)
                with self.assertRaises(IOError):
                    run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

    def test_main_with_weird_organization_name(self):
        ''' When an organization has a weird name, ...
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if "docs.google.com" in url:
                return response(200, '''name\nCode_for-America''')

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)
                from app import Error
                errors = self.db.session.query(Error).all()
                for error in errors:
                    self.assertTrue("ValueError" in error.error)
                self.assertEqual(self.db.session.query(Error).count(), 1)

        from app import Organization

        # Make sure no organizations exist
        orgs_count = self.db.session.query(Organization).count()
        self.assertEqual(orgs_count, 0)

    def test_main_with_bad_organization_name(self):
        ''' When an org has a invalid name, test that it gets skipped and an error is added to the db
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            return response(200, '''name\nCode#America\nCode?America\nCode/America\nCode for America''')

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)
                from app import Error
                errors = self.db.session.query(Error).all()
                for error in errors:
                    self.assertTrue("ValueError" in error.error)
                self.assertEqual(self.db.session.query(Error).count(), 3)

        # Make sure one good organization exists
        from app import Organization
        orgs_count = self.db.session.query(Organization).count()
        self.assertEqual(orgs_count, 1)

    def test_main_with_bad_events_url(self):
        ''' When an organization has a badly formed events url is passed, no events are saved
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if "docs.google.com" in url:
                return response(200, '''name,events_url\nCode for America,http://www.meetup.com/events/foo-%%%''')

        logging.error = Mock()

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        logging.error.assert_called_with('Code for America does not have a valid events url')

        from app import Event

        # Make sure no events exist
        events_count = self.db.session.query(Event).count()
        self.assertEqual(events_count, 0)

    def test_main_with_non_existant_meetup(self):
        ''' When meetup returns a 404 for an organization's events url, an error
            message should be logged
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if "docs.google.com" in url:
                return response(200, '''name,events_url\nCode for America,http://www.meetup.com/events/Code-For-Charlotte''')

            if 'api.meetup.com' in url:
                return response(404, '''Not Found!''')

        logging.error = Mock()
        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        logging.error.assert_called_with('Code for America\'s meetup page cannot be found')

    def test_main_with_stories(self):
        '''
        Test that two most recent blog posts are in the db.
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory
        organization = OrganizationFactory(name=u'Code for America')

        with HTTMock(self.response_content):
            import run_update
            for story_info in run_update.get_stories(organization):
                run_update.save_story_info(self.db.session, story_info)

        self.db.session.flush()

        from app import Story

        stories_count = self.db.session.query(Story).count()
        self.assertEqual(stories_count, 2)

        stories = self.db.session.query(Story).all()
        self.assertEqual(stories[0].title, u'Four Great Years')
        self.assertEqual(stories[1].title, u'Open, transparent Chattanooga')

    def test_github_throttling(self):
        '''
        Test that when GitHub throttles us, we skip updating projects and record an error.
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if url.netloc == 'api.github.com':
                return response(403, "", {"x-ratelimit-remaining": 0})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        from app import Project
        projects = self.db.session.query(Project).all()
        for project in projects:
            self.assertIsNone(project.github_details)

        from app import Error
        error = self.db.session.query(Error).first()
        self.assertEqual(error.error, "IOError: We done got throttled by GitHub")

    def test_csv_sniffer(self):
        '''
        Testing weird csv dialects we've encountered
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory
        philly = OrganizationFactory(name=u'Code for Philly', projects_list_url=u'http://codeforphilly.org/projects.csv')
        austin = OrganizationFactory(name=u'Open Austin', projects_list_url=u'http://openaustin.org/projects.csv')

        with HTTMock(self.response_content):
            import run_update
            projects = run_update.get_projects(philly)
            self.assertEqual(projects[0]['name'], "OpenPhillyGlobe")
            self.assertEqual(projects[0]['description'], 'Google Earth for Philadelphia" with open source and open transit data."')

            projects = run_update.get_projects(austin)
            self.assertEqual(projects[0]['name'], "Hack Task Aggregator")
            self.assertEqual(projects[0]['description'], 'Web application to aggregate tasks across projects that are identified for "hacking".')

    def test_non_github_projects(self):
        ''' Test that non github and non code projects get last_updated timestamps.
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory
        philly = OrganizationFactory(name=u'Code for Philly', projects_list_url=u'http://codeforphilly.org/projects.csv')
        austin = OrganizationFactory(name=u'Open Austin', projects_list_url=u'http://openaustin.org/projects.csv')

        with HTTMock(self.response_content):
            import run_update
            projects = run_update.get_projects(philly)
            self.assertEqual(projects[0]['name'], "OpenPhillyGlobe")
            self.assertEqual(projects[0]['last_updated'], datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z"))

            projects = run_update.get_projects(austin)
            self.assertEqual(projects[0]['name'], "Hack Task Aggregator")
            self.assertEqual(projects[0]['last_updated'], datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z"))

    def test_non_github_projects_updates(self):
        ''' Test that non github projects update their timestamp when something in the sheet changes.
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory
        philly = OrganizationFactory(name=u'Code for Philly', projects_list_url=u'http://codeforphilly.org/projects.csv')

        # Get a Philly project into the db
        with HTTMock(self.response_content):
            import run_update
            projects = run_update.get_projects(philly)
            for proj_info in projects:
                run_update.save_project_info(self.db.session, proj_info)
                self.db.session.flush()

        time.sleep(1)

        def updated_description(url, request):
            if url.geturl() == 'http://codeforphilly.org/projects.csv':
                    return response(200, '''"name","description","link_url","code_url","type","categories","tags","status"\r\n"OpenPhillyGlobe","UPDATED DESCRIPTION","http://cesium.agi.com/OpenPhillyGlobe/","http://google.com","","","",""''', {'content-type': 'text/csv; charset=UTF-8'})

        # Test that a different description gives a new timestamp
        with HTTMock(updated_description):
            projects = run_update.get_projects(philly)
            self.assertEqual(projects[0]['description'], "UPDATED DESCRIPTION")
            self.assertEqual(projects[0]['last_updated'], datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z"))
            for proj_info in projects:
                run_update.save_project_info(self.db.session, proj_info)
                self.db.session.flush()

        time.sleep(1)

        def updated_status(url, request):
            if url.geturl() == 'http://codeforphilly.org/projects.csv':
                return response(200, '''"name","description","link_url","code_url","type","categories","tags","status"\r\n"OpenPhillyGlobe","UPDATED DESCRIPTION","http://cesium.agi.com/OpenPhillyGlobe/","http://google.com","","","","active"''', {'content-type': 'text/csv; charset=UTF-8'})

        # Test that a different status gives a new timestamp
        with HTTMock(updated_status):
            projects = run_update.get_projects(philly)
            self.assertEqual(projects[0]['status'], "active")
            self.assertEqual(projects[0]['last_updated'], datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z"))

    def test_utf8_noncode_projects(self):
        ''' Test that utf8 project descriptions match exisiting projects.
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory, ProjectFactory

        philly = OrganizationFactory(name=u'Code for Philly', projects_list_url=u'http://codeforphilly.org/projects.csv')
        old_project = ProjectFactory(name=u'Philly Map of Shame', organization_name=u'Code for Philly', description=u'PHL Map of Shame is a citizen-led project to map the impact of the School Reform Commission\u2019s \u201cdoomsday budget\u201d on students and parents. We will visualize complaints filed with the Pennsylvania Department of Education.', categories=u'Education, CivicEngagement', tags=u'philly, mapping', type=None, link_url=u'http://phillymapofshame.org', code_url=None, status=u'In Progress')
        self.db.session.flush()

        def overwrite_response_content(url, request):
            if url.geturl() == 'http://codeforphilly.org/projects.csv':
                return response(200, '''"name","description","link_url","code_url","type","categories","tags","status"\r\n"Philly Map of Shame","PHL Map of Shame is a citizen-led project to map the impact of the School Reform Commission\xe2\x80\x99s \xe2\x80\x9cdoomsday budget\xe2\x80\x9d on students and parents. We will visualize complaints filed with the Pennsylvania Department of Education.","http://phillymapofshame.org","","","Education, CivicEngagement","philly, mapping","In Progress"''', {'content-type': 'text/csv; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                projects = run_update.get_projects(philly)
                # If the two descriptions are equal, it won't update last_updated
                assert projects[0]['last_updated'] == None

    def test_issue_paging(self):
        ''' test that issues are following page links '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory, ProjectFactory

        organization = OrganizationFactory(name=u'Code for America', projects_list_url=u'http://codeforamerica.org/projects.csv')
        project = ProjectFactory(organization_name=u'Code for America',code_url=u'https://github.com/TESTORG/TESTPROJECT')
        self.db.session.flush()

        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/TESTORG/TESTPROJECT/issues':
                content = '''[{"number": 2,"title": "TEST TITLE 2","body": "TEST BODY 2","labels": [], "html_url":""}]'''
                headers = {"Link": '<https://api.github.com/repos/TESTORG/TESTPROJECT/issues?page=2>"; rel="next"', 'ETag': '8456bc53d4cf6b78779ded3408886f82'}
                return response(200, content, headers)

            elif url.geturl() == 'https://api.github.com/repos/TESTORG/TESTPROJECT/issues?page=2':
                content = '''[{"number": 2,"title": "TEST TITLE 2","body": "TEST BODY 2","labels": [], "html_url":""}]'''
                return response(200, content)

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                issues = run_update.get_issues(organization.name)
                assert (len(issues) == 2)

    def test_project_list_without_all_columns(self):
        ''' Get a project list that doesn't have all the columns.
            Don't die.
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory
        organization = OrganizationFactory(projects_list_url=u'http://organization.org/projects.csv')

        def overwrite_response_content(url, request):
            if url.geturl() == 'http://organization.org/projects.csv':
                return response(200, '''name,description,link_url\n,,http://fakeprojectone.com\n,,,http://whatever.com/testproject''', {'content-type': 'text/csv; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                projects = run_update.get_projects(organization)
                assert len(projects) == 2

    def test_new_value_in_csv_project_list(self):
        ''' A value that has changed in the CSV project list should be saved, even if the
            related GitHub project reports that it hasn't been updated
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        org_csv = '''name,website,events_url,rss,projects_list_url\nOrganization Name,,,,http://organization.org/projects.csv'''

        def status_one_response_content(url, request):
            if "docs.google.com" in url.geturl():
                return response(200, org_csv, {'content-type': 'text/csv; charset=UTF-8'})
            # return an empty civic.json so the value of status there won't overwrite the one from the spreadsheet
            elif "/contents/civic.json" in url.geturl():
                return response(200, '''{}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})
            # return a status of 'In Progress'
            elif url.geturl() == 'http://organization.org/projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories,tags,status\nProject Name,"Long project description here.",,https://github.com/codeforamerica/cityvoice,,,,In Progress''', {'content-type': 'text/csv; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(status_one_response_content):
                run_update.main(org_name=u"Organization Name", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        project_v1 = self.db.session.query(Project).first()
        # the project status was correctly set
        self.assertEqual(project_v1.status, u'In Progress')
        v1_github_details = project_v1.github_details

        # save the default github response so we can send it with a 304 status below
        cv_body_text = None
        cv_headers_dict = None
        with HTTMock(self.response_content):
            from requests import get
            got = get('https://api.github.com/repos/codeforamerica/cityvoice')
            cv_body_text = str(got.text)
            cv_headers_dict = got.headers

        def status_two_response_content(url, request):
            if "docs.google.com" in url.geturl():
                return response(200, org_csv, {'content-type': 'text/csv; charset=UTF-8'})
            # return an empty civic.json so the value of status there won't overwrite the one from the spreadsheet
            elif "/contents/civic.json" in url.geturl():
                return response(200, '''{}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})
            # return a status of 'Released' instead of 'In Progress'
            elif url.geturl() == 'http://organization.org/projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories,tags,status\nProject Name,"Long project description here.",,https://github.com/codeforamerica/cityvoice,,,,Released''', {'content-type': 'text/csv; charset=UTF-8'})
            # return a 304 (not modified) instead of a 200 for the project
            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(304, cv_body_text, cv_headers_dict)

        with HTTMock(self.response_content):
            with HTTMock(status_two_response_content):
                run_update.main(org_name=u"Organization Name", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        project_v2 = self.db.session.query(Project).first()
        # the new project status was correctly set
        self.assertEqual(project_v2.status, u'Released')
        # the untouched details from the GitHub project weren't changed
        self.assertEqual(project_v2.github_details, v1_github_details)

    def test_html_returned_for_csv_project_list(self):
        ''' We requested a CSV project list and got HTML instead
        '''
        self.setup_mock_rss_response()

        from test.factories import OrganizationFactory
        organization = OrganizationFactory(projects_list_url=u'http://organization.org/projects.csv')

        def overwrite_response_content(url, request):
            if url.geturl() == 'http://organization.org/projects.csv':
                return response(200, ''''\n<!DOCTYPE html>\n<html lang="en">\n</html>\n''', {'content-type': 'text/html; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                try:
                    projects = run_update.get_projects(organization)
                except KeyError:
                    raise Exception('Tried to parse HTML as CSV')
                self.assertEqual(len(projects), 0)

    def test_missing_last_updated(self):
        ''' In rare cases, a project will be in the db without a last_updated date
            Remove a project's last_updated and try and update it.
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        with HTTMock(self.response_content):
            run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)
            self.db.session.query(Project).update({"last_updated": None})
            run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # :TODO: no assertion?

    def test_orphan_labels(self):
        ''' We keep getting orphan labels,
            run_update twice and check for orphan labels.
        '''
        self.setup_mock_rss_response()

        from app import Label
        import run_update

        with HTTMock(self.response_content):
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        labels = self.db.session.query(Label).all()
        for label in labels:
            self.assertIsNotNone(label.issue_id)

    def test_duplicate_labels(self):
        ''' Getting many duplicate labels on issues.
        '''
        self.setup_mock_rss_response()

        from app import Label
        import run_update

        with HTTMock(self.response_content):
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        labels = self.db.session.query(Label).all()
        unique_labels = []

        for label in labels:
            assert (label.issue_id, label.name) not in unique_labels
            unique_labels.append((label.issue_id, label.name))

    def test_unicode_warning(self):
        ''' Testing for the postgres unicode warning
        '''
        self.setup_mock_rss_response()

        import run_update
        import warnings

        warnings.filterwarnings('error')

        with HTTMock(self.response_content):
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

    def test_orphaned_organization_deleted(self):
        ''' Make sure that an organization and all its children are deleted when
            the organization is no longer included in the returned csv
        '''
        self.setup_mock_rss_response()

        from app import Organization, Project, Event, Story, Issue, Label
        import run_update

        self.organization_count = 3
        full_orgs_list = []

        with HTTMock(self.response_content):
            # get the orgs list for comparison
            full_orgs_list = run_update.get_organizations(run_update.TEST_ORG_SOURCES_FILENAME)
            # run the update on the same orgs
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # confirm that the orgs in the list are in the database
        for org_check in full_orgs_list:
            filter = Organization.name == org_check['name']
            organization = self.db.session.query(Organization).filter(filter).first()
            self.assertIsNotNone(organization)
            self.assertEqual(organization.name, org_check['name'])
            self.assertTrue(organization.keep)

        # reset with just two organizations
        self.organization_count = 2
        partial_orgs_list = []
        with HTTMock(self.response_content):
            partial_orgs_list = run_update.get_organizations(run_update.TEST_ORG_SOURCES_FILENAME)

        # save details about the organization(s) and their children who will be orphaned
        orphaned_org_names = list(set([item['name'] for item in full_orgs_list]) - set([item['name'] for item in partial_orgs_list]))
        orphaned_issue_ids = []
        orphaned_label_ids = []
        for org_name in orphaned_org_names:
            projects = self.db.session.query(Project).filter(Project.organization_name == org_check['name']).all()
            for project in projects:
                issues = self.db.session.query(Issue).filter(Issue.project_id == project.id).all()
                for issue in issues:
                    orphaned_issue_ids.append(issue.id)
                    labels = self.db.session.query(Label).filter(Label.issue_id == issue.id).all()
                    for label in labels:
                        orphaned_label_ids.append(label.id)

        with HTTMock(self.response_content):
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # confirm that the two organizations are in the database
        for org_check in partial_orgs_list:
            filter = Organization.name == org_check['name']
            organization = self.db.session.query(Organization).filter(filter).first()
            self.assertIsNotNone(organization)
            self.assertEqual(organization.name, org_check['name'])
            self.assertTrue(organization.keep)

        # confirm that the orphaned organization and its children are no longer in the database
        for org_name_check in orphaned_org_names:
            filter = Organization.name == org_name_check
            organization = self.db.session.query(Organization).filter(filter).first()
            self.assertIsNone(organization)

            events = self.db.session.query(Event).filter(Event.organization_name == org_name_check).all()
            self.assertEqual(len(events), 0)

            stories = self.db.session.query(Story).filter(Story.organization_name == org_name_check).all()
            self.assertEqual(len(stories), 0)

            projects = self.db.session.query(Project).filter(Project.organization_name == org_name_check).all()
            self.assertEqual(len(projects), 0)

            for issue_id in orphaned_issue_ids:
                issue = self.db.session.query(Issue).filter(Issue.id == issue_id).first()
                self.assertIsNone(issue)

            for label_id in orphaned_label_ids:
                label = self.db.session.query(Label).filter(Label.id == label_id).first()
                self.assertIsNone(label)

        # reset to three projects
        self.organization_count = 3

    def check_database_against_input(self):
        ''' verify that what's in the database matches the input
        '''
        self.setup_mock_rss_response()

        from app import Organization, Project, Event, Story, Issue, Label
        import run_update

        # for checking data from the source against what's in the database
        check_orgs = []
        check_events = {}
        check_stories = {}
        check_projects = {}
        check_issues = {}

        with HTTMock(self.response_content):
            # run the update
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

            # get raw data from the source to compare with what's in the database
            check_orgs = run_update.get_organizations(run_update.TEST_ORG_SOURCES_FILENAME)
            for check_org in check_orgs:
                check_org_obj = Organization(**check_org)
                check_events[check_org_obj.name] = run_update.get_meetup_events(check_org_obj, run_update.get_event_group_identifier(check_org_obj.events_url))
                check_stories[check_org_obj.name] = run_update.get_stories(check_org_obj)
                check_projects[check_org_obj.name] = run_update.get_projects(check_org_obj)
                check_issues[check_org_obj.name] = {}
                for check_project in check_projects[check_org_obj.name]:
                    check_project_obj = Project(**check_project)
                    check_issues[check_org_obj.name][check_project_obj.name] = run_update.get_issues_for_project(check_project_obj)

        # confirm that the org and its children are in the database and save records to compare later
        db_events = {}
        db_stories = {}
        db_projects = {}
        db_issues = {}
        db_labels = {}
        # verify that we have the number of organizations that we expect
        self.assertEqual(len(check_orgs), len(self.db.session.query(Organization).all()))
        for org_dict in check_orgs:
            # get the matching ORGANIZATION from the database
            organization = self.db.session.query(Organization).filter(Organization.name == org_dict['name']).first()
            self.assertIsNotNone(organization)
            self.assertTrue(organization.keep)

            # get the matching EVENTS for this organization from the database
            db_events[organization.name] = self.db.session.query(Event).filter(Event.organization_name == org_dict['name']).all()
            # verify that we have the number of events that we expect
            self.assertEqual(len(check_events[organization.name]), len(db_events[organization.name]))
            for event_dict in check_events[organization.name]:
                event = self.db.session.query(Event).filter(Event.event_url == event_dict['event_url'], Event.organization_name == event_dict['organization_name']).first()
                self.assertIsNotNone(event)
                self.assertTrue(event.keep)

            # get the matching STORIES for this organization from the database
            db_stories[organization.name] = self.db.session.query(Story).filter(Story.organization_name == org_dict['name']).all()
            # verify that we have the number of stories we expect
            self.assertEqual(len(check_stories[organization.name]), len(db_stories[organization.name]))
            for story_dict in check_stories[organization.name]:
                story = self.db.session.query(Story).filter(Story.organization_name == story_dict['organization_name'], Story.link == story_dict['link']).first()
                self.assertIsNotNone(story)
                self.assertTrue(story.keep)

            # get the matching PROJECTS for this organization from the database
            db_projects[organization.name] = self.db.session.query(Project).filter(Project.organization_name == org_dict['name']).all()
            # verify that we have the number of projects we expect
            self.assertEqual(len(check_projects[organization.name]), len(db_projects[organization.name]))
            db_issues[organization.name] = {}
            db_labels[organization.name] = {}

            for project_dict in check_projects[organization.name]:
                project = self.db.session.query(Project).filter(Project.name == project_dict['name'], Project.organization_name == project_dict['organization_name']).first()
                self.assertIsNotNone(project)
                self.assertTrue(project.keep)

                # get the matching ISSUES for this project from the database
                db_issues[organization.name][project.name] = self.db.session.query(Issue).filter(Issue.project_id == project.id).all()
                # verify that we have the number of issues we expect
                self.assertEqual(len(check_issues[organization.name][project.name]), len(db_issues[organization.name][project.name]))
                db_labels[organization.name][project.name] = {}

                for issue_dict in check_issues[organization.name][project.name]:
                    issue = self.db.session.query(Issue).filter(Issue.title == issue_dict['title'], Issue.project_id == project.id).first()
                    self.assertIsNotNone(issue)
                    self.assertTrue(issue.keep)

                    # get the matching LABELS for this issue from the database
                    db_labels[organization.name][project.name][issue.title] = self.db.session.query(Label).filter(Label.issue_id == issue.id).all()
                    # verify that we have the number of labels we expect
                    self.assertEqual(len(issue_dict['labels']), len(db_labels[organization.name][project.name][issue.title]))

                    for label_dict in issue_dict['labels']:
                        label = self.db.session.query(Label).filter(Label.issue_id == issue.id, Label.name == label_dict['name']).first()
                        self.assertIsNotNone(label)
                        # labels don't have a 'keep' parameter

    def test_orphaned_objects_deleted(self):
        ''' Make sure that sub-organization objects are deleted when
            they're no longer referenced in returned data
        '''

        # only get one organization
        self.organization_count = 1
        # when results_state is 'before' we get more events, stories, projects, issues, labels
        self.results_state = 'before'

        self.check_database_against_input()

        # when results_state is 'after' we get fewer events, stories, projects, issues, labels
        self.results_state = 'after'

        self.check_database_against_input()

        # reset to defaults
        self.organization_count = 3
        self.results_state = 'before'

    def test_same_projects_different_organizations(self):
        ''' Verify that the same project can be associated with two different organizations
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        # save the default response for the cityvoice project
        body_text = None
        headers_dict = None
        with HTTMock(self.response_content):
            from requests import get
            got = get('https://api.github.com/repos/codeforamerica/cityvoice')
            body_text = str(got.text)
            headers_dict = got.headers

        with HTTMock(self.response_content):
            # run the update
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # overwrite to return a 304 (not modified) instead of a 200 for the cityvoice project
        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(304, body_text, headers_dict)

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                # run the update on the same orgs
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # verify that there are multiple 'cityvoice' projects that are identical except in organization name
        projects = self.db.session.query(Project).filter(Project.name == u'cityvoice').all()
        project_names = [item.name for item in projects]
        project_code_urls = [item.code_url for item in projects]
        project_organization_names = [item.organization_name for item in projects]

        # there should be more than one project returned
        self.assertTrue(len(projects) > 1)
        # there should be only one project name
        self.assertTrue(len(set(project_names)) == 1)
        # there should be only one code url
        self.assertTrue(len(set(project_code_urls)) == 1)
        # all the organization names should be unique
        self.assertTrue(len(set(project_organization_names)) == len(project_organization_names))

    def test_empty_project_values_set_null(self):
        ''' Values in a project csv or civic.json that are empty are saved to the
            database as None rather than empty strings
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        # overwrite response content to send back a civic.json with some empty values
        # these should be transformed to None values in run_update
        def overwrite_response_content(url, request):
            if "cityvoice/contents/civic.json" in url.geturl():
                return response(200, '''{"status": "", "tags": ["", "", ""]}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                # run the update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # check for empty strings in the saved project you know doesn't have status & tags set
        # because they're missing from the spreadsheet/csv...
        filter = [Project.organization_name == u'Cöde for Ameriça', Project.name == u'bizfriendly-web']
        project = self.db.session.query(Project).filter(*filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, None)
        self.assertEqual(project.tags, None)

        # and in the saved project you know doesn't have status & tags set because they're
        # missing from civic.json
        filter = [Project.organization_name == u'Code for America (3)', Project.name == u'cityvoice']
        project = self.db.session.query(Project).filter(*filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, None)
        self.assertEqual(project.tags, None)

    def test_repo_name_used_for_missing_project_name(self):
        ''' Verify that a repo name will be used when no project name is available
        '''
        self.setup_mock_rss_response()

        from app import Organization, Project
        import run_update

        # only get one organization
        self.organization_count = 1

        with HTTMock(self.response_content):
            # run the update
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

            # verify only one organization was returned
            organizations = self.db.session.query(Organization).all()
            self.assertTrue(len(organizations) is 1)

        # now get the projects from the database
        projects = self.db.session.query(Project).all()
        for project in projects:
            # verify that the project name isn't empty
            self.assertTrue(project.name)
            # verify that the project name is the same as the repo name
            self.assertTrue(project.name == project.github_details['name'])

        # reset to defaults
        self.organization_count = 3

    def test_bad_events_json(self):
        ''' Verify that a call for event data that returns bad or no json is handled
        '''
        self.setup_mock_rss_response()

        def overwrite_response_content(url, request):
            if 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=' in url.geturl() and 'Code-For-Charlotte' in url.geturl():
                return response(200, 'no json object can be decoded from me')

            elif 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=' in url.geturl() and 'Code-For-Rhode-Island' in url.geturl():
                return response(200, None)

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # Make sure no events exist
        from app import Event
        self.assertEqual(self.db.session.query(Event).count(), 0)

    def test_unmodified_projects_stay_in_database(self):
        ''' Verify that unmodified projects are not deleted from the database
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        # run a standard run_update
        with HTTMock(self.response_content):
            run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # remember how many projects were saved
        project_count = self.db.session.query(Project).count()

        # save the default response for the cityvoice and bizfriendly projects
        citivoice_body_text = None
        citivoice_headers_dict = None
        bizfriendly_body_text = None
        bizfriendly_headers_dict = None
        with HTTMock(self.response_content):
            from requests import get
            citivoice_got = get('https://api.github.com/repos/codeforamerica/cityvoice')
            citivoice_body_text = str(citivoice_got.text)
            citivoice_headers_dict = citivoice_got.headers
            bizfriendly_got = get('https://api.github.com/repos/codeforamerica/bizfriendly-web')
            bizfriendly_body_text = str(bizfriendly_got.text)
            bizfriendly_headers_dict = bizfriendly_got.headers

        # overwrite to return a 304 (not modified) instead of a 200 for the cityvoice project
        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(304, citivoice_body_text, citivoice_headers_dict)
            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/bizfriendly-web':
                return response(304, bizfriendly_body_text, bizfriendly_headers_dict)

        # re-run run_update with the new 304 responses
        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                # run the update on the same orgs
                run_update.main(org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # verify that the same number of projects are in the database
        self.assertEqual(project_count, self.db.session.query(Project).count())

    def test_values_set_from_civic_json(self):
        ''' Values from a civic.json file are read and stored in the database.
            Also tests that civic.json values overwrite values set in the project spreadsheet.
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        # run a standard run_update
        with HTTMock(self.response_content):
            run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # check a project for the status and tags from the mock civic.json
        project = self.db.session.query(Project).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'Beta')
        self.assertEqual(project.tags, u'mapping,transportation,community organizing')

    def test_new_values_in_civic_json(self):
        ''' A value that has changed in civic.json should be saved, even if the
            related GitHub project reports that it hasn't been updated
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        org_csv = '''name,website,events_url,rss,projects_list_url\nOrganization Name,,,,http://example.com/cfa-projects.csv'''

        # set results_state to 'after' so we'll only get one project
        self.results_state = 'after'

        def status_one_response_content(url, request):
            if "docs.google.com" in url.geturl():
                return response(200, org_csv, {'content-type': 'text/csv; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(status_one_response_content):
                run_update.main(org_name=u"Organization Name", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        project_v1 = self.db.session.query(Project).first()
        # the project status was correctly set
        self.assertEqual(project_v1.status, u'Beta')
        # the project tags were correctly set
        self.assertEqual(project_v1.tags, u'mapping,transportation,community organizing')
        v1_github_details = project_v1.github_details

        # save the default github response so we can send it with a 304 status below
        cv_body_text = None
        cv_headers_dict = None
        with HTTMock(self.response_content):
            from requests import get
            got = get('https://api.github.com/repos/codeforamerica/cityvoice')
            cv_body_text = str(got.text)
            cv_headers_dict = got.headers

        def status_two_response_content(url, request):
            if "docs.google.com" in url.geturl():
                return response(200, org_csv, {'content-type': 'text/csv; charset=UTF-8'})
            # return a civic.json with a new status value
            elif "/contents/civic.json" in url.geturl():
                return response(200, '''{"status": "Cromulent", "tags": ["community organizing", "safety and justice"]}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})
            # return a 304 (not modified) instead of a 200 for the project
            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(304, cv_body_text, cv_headers_dict)

        with HTTMock(self.response_content):
            with HTTMock(status_two_response_content):
                run_update.main(org_name=u"Organization Name", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        project_v2 = self.db.session.query(Project).first()
        # the new project status was correctly set
        self.assertEqual(project_v2.status, u'Cromulent')
        # the new tags were correctly set
        self.assertEqual(project_v2.tags, u'community organizing,safety and justice')
        # the untouched details from the GitHub project weren't changed
        self.assertEqual(project_v2.github_details, v1_github_details)

        self.results_state = 'before'

    def test_unicode_values_in_civic_json(self):
        ''' Unicode values in the civic.json file are handled correctly
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        def unicode_response_content(url, request):
            if "/contents/civic.json" in url.geturl():
                return response(200, '''{"status": "汉语 漢語", "tags": ["한국어 조선말", "ру́сский язы́к", "†≈ç®åz¥≈†"]}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})

        # run a standard run_update
        with HTTMock(self.response_content):
            with HTTMock(unicode_response_content):
                run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # check a project for the status and tags from the mock civic.json
        project = self.db.session.query(Project).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'汉语 漢語')
        self.assertEqual(project.tags, u'한국어 조선말,ру́сский язы́к,†≈ç®åz¥≈†')
        # testing for the roman text representations as well, just for reference
        self.assertEqual(project.status, u'\u6c49\u8bed \u6f22\u8a9e')
        self.assertEqual(project.tags, u'\ud55c\uad6d\uc5b4 \uc870\uc120\ub9d0,\u0440\u0443\u0301\u0441\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u0301\u043a,\u2020\u2248\xe7\xae\xe5z\xa5\u2248\u2020')

    def test_alt_tag_format_in_civic_json(self):
        ''' Tags represented as objects rather than strings are read correctly.
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        def unicode_response_content(url, request):
            if "/contents/civic.json" in url.geturl():
                return response(200, '''{"status": "Cromulent", "tags": [{"tag": "economic development"}, {"tag": "twitter"}, {"tag": "người máy"}, {"tag": "python"}]}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})

        # run a standard run_update
        with HTTMock(self.response_content):
            with HTTMock(unicode_response_content):
                run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # check a project for the status and tags from the mock civic.json
        project = self.db.session.query(Project).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'Cromulent')
        self.assertEqual(project.tags, u'economic development,twitter,người máy,python')
        # testing for the roman text representations as well, just for reference
        self.assertEqual(project.tags, u'economic development,twitter,ng\u01b0\u1eddi m\xe1y,python')

    def test_civic_json_values_preferred(self):
        ''' Values set in civic.json are preferred over values set in spreadsheets,
            even after multiple updates.
        '''
        self.setup_mock_rss_response()

        from app import Project
        import run_update

        # set results_state to 'after' so we'll only get one project
        self.results_state = 'after'

        # run a standard run_update
        with HTTMock(self.response_content):
            run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # check a project for the status and tags from the mock civic.json
        project = self.db.session.query(Project).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'Beta')
        self.assertEqual(project.tags, u'mapping,transportation,community organizing')

        # respond to requests for project, root file listing, and civic.json with 304s
        # only if a 'If-None-Match' or 'If-Modified-Since' header is passed
        def files_not_updated(url, request):
            if "/contents/civic.json" in url.geturl():
                if 'If-None-Match' in request.headers:
                    return response(304, '''{}''', {'Etag': '8456bc53d4cf6b78779ded3408886f82'})
            elif search(r'\/contents\/$', url.geturl()):
                if 'If-None-Match' in request.headers:
                    return response(304, '''[]''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})
            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                if 'If-Modified-Since' in request.headers:
                    return response(304, '', {})

        # run another run_update
        with HTTMock(self.response_content):
            with HTTMock(files_not_updated):
                run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources=run_update.TEST_ORG_SOURCES_FILENAME)

        # check a project for the status and tags from the mock civic.json
        project = self.db.session.query(Project).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'Beta')
        self.assertEqual(project.tags, u'mapping,transportation,community organizing')

        self.results_state = 'before'


    def test_attendance(self):
        ''' Test gathering attendance from the peopledb '''
        # Mock attendance data
        cfsf_url = "https://www.codeforamerica.org/api/organizations/Code-for-San-Francisco"
        cfsf_name = "Code for San Francisco"
        oakland_url = "https://www.codeforamerica.org/api/organizations/Open-Oakland"
        oakland_name = "Open Oakland"
        cfsf_checkin1 = datetime.datetime.strptime("2015-01-01","%Y-%m-%d")
        cfsf_checkin2 = datetime.datetime.strptime("2015-01-08","%Y-%m-%d")
        oakland_checkin1 = datetime.datetime.strptime("2015-01-16","%Y-%m-%d")
        oakland_checkin2 = datetime.datetime.strptime("2015-01-24","%Y-%m-%d")

        # Access the peopledb
        PEOPLEDB = 'postgres:///peopledbtest'

        with connect(PEOPLEDB) as conn:
            with conn.cursor() as db:
                # Put some fake attendance data in it
                q = '''INSERT INTO attendance
                       ( datetime, organization_url)
                       VALUES ( %s, %s )'''
                db.execute(q, (cfsf_checkin1, cfsf_url))
                db.execute(q, (cfsf_checkin2, cfsf_url))
                db.execute(q, (oakland_checkin1, oakland_url))
                db.execute(q, (oakland_checkin2, oakland_url))

        # Call a function to pull data out of it
        with connect(PEOPLEDB) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as peopledb:
                import run_update
                from app import Attendance, Organization
                from test.factories import OrganizationFactory
                cfsf = OrganizationFactory(name='Code for San Francisco')
                oakland = OrganizationFactory(name='Open Oakland')

                cfsf_attendance = run_update.get_attendance(peopledb, cfsf_url, cfsf.name)
                self.assertEqual(cfsf_attendance["organization_name"], "Code for San Francisco")
                self.assertTrue("2015 01" in cfsf_attendance["weekly"].keys())

                oakland_attendance = run_update.get_attendance(peopledb, oakland_url, oakland.name)
                self.assertEqual(oakland_attendance["organization_name"], "Open Oakland")
                self.assertTrue("2015 03" in oakland_attendance["weekly"].keys())

        run_update.update_attendance(self.db, cfsf.name, cfsf_attendance)
        run_update.update_attendance(self.db, oakland.name, oakland_attendance)
        attendance = self.db.session.query(Attendance).all()
        self.assertEqual(attendance[0].organization_name, "Code for San Francisco")
        self.assertEqual(attendance[1].organization_name, "Open Oakland")
        self.assertTrue("2015 03" in attendance[1].weekly.keys())


    def test_meetup_count(self):
        ''' Test getting membership count from Meetup '''
        from test.factories import OrganizationFactory
        org = OrganizationFactory(name="TEST ORG")
        with HTTMock(self.response_content):
            import run_update
            run_update.get_meetup_count(organization=org, identifier="TEST-MEETUP")
        self.assertEqual(org.member_count, 100)



if __name__ == '__main__':
    unittest.main()
