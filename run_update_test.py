#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import unittest
import datetime
import logging
from re import match, sub

from httmock import response, HTTMock
from mock import Mock

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

        from app import db

        self.db = db
        self.db.create_all()

        import run_update
        run_update.github_throttling = False

    def tearDown(self):
        self.db.session.close()
        self.db.drop_all()

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
        lines = [u'''name,website,events_url,rss,projects_list_url'''.encode('utf8'), u'''Cöde for Ameriça,http://codeforamerica.org,http://www.meetup.com/events/Code-For-Charlotte/,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv'''.encode('utf8'), u'''Code for America (2),,,,https://github.com/codeforamerica'''.encode('utf8'), u'''Code for America (3),,http://www.meetup.com/events/Code-For-Rhode-Island/,http://www.codeforamerica.org/blog/another/feed/,https://www.github.com/orgs/codeforamerica'''.encode('utf8')]
        return '\n'.join(lines[0:count + 1])

    def response_content(self, url, request):

        # csv file of project descriptions
        if url.geturl() == 'http://example.com/cfa-projects.csv':
            project_lines = ['''Name,description,link_url,code_url,type,categories,status''', ''',,,https://github.com/codeforamerica/cityvoice,,,''', ''',,,https://github.com/codeforamerica/bizfriendly-web,,,''']
            if self.results_state == 'before':
                return response(200, '''\n'''.join(project_lines[0:3]), {'content-type': 'text/csv; charset=UTF-8'})
            elif self.results_state == 'after':
                return response(200, '''\n'''.join(project_lines[0:2]), {'content-type': 'text/csv; charset=UTF-8'})

        # json of project descriptions
        elif url.geturl() == 'https://api.github.com/users/codeforamerica/repos':
            return response(200, '''[{ "id": 10515516, "name": "cityvoice", "owner": { "login": "codeforamerica", "avatar_url": "https://avatars.githubusercontent.com/u/337792", "html_url": "https://github.com/codeforamerica", "type": "Organization"}, "html_url": "https://github.com/codeforamerica/cityvoice", "description": "A place-based call-in system for gathering and sharing community feedback",  "url": "https://api.github.com/repos/codeforamerica/cityvoice", "contributors_url": "https://api.github.com/repos/codeforamerica/cityvoice/contributors", "created_at": "2013-06-06T00:12:30Z", "updated_at": "2014-02-21T20:43:16Z", "pushed_at": "2014-02-21T20:43:16Z", "homepage": "http://www.cityvoiceapp.com/", "stargazers_count": 10, "watchers_count": 10, "language": "Ruby", "forks_count": 12, "open_issues": 37 }]''', headers=dict(Link='<https://api.github.com/user/337792/repos?page=2>; rel="next", <https://api.github.com/user/337792/repos?page=2>; rel="last"'))

        # csv file of organization descriptions
        elif "docs.google.com" in url:
            return response(200, self.get_raw_organization_list(self.organization_count))

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

        # json of meetup events
        elif 'meetup.com' in url.geturl() and 'Code-For-Charlotte' in url.geturl():
            events_filename = 'meetup_events.json'
            if self.results_state == 'after':
                events_filename = 'meetup_events_fewer.json'

            events_file = open(events_filename)
            events_content = events_file.read()
            events_file.close()
            return response(200, events_content)

        # json of alternate meetup events
        elif 'meetup.com' in url.geturl() and 'Code-For-Rhode-Island' in url.geturl():
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
                return response(200, '''"name","description","link_url","code_url","type","categories","status"\r\n"OpenPhillyGlobe","\"Google Earth for Philadelphia\" with open source and open transit data.","http://cesium.agi.com/OpenPhillyGlobe/","http://google.com","","",""''', {'content-type': 'text/csv; charset=UTF-8'})

        # csv of projects (austin)
        elif url.geturl() == 'http://openaustin.org/projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories,status\nHack Task Aggregator,"Web application to aggregate tasks across projects that are identified for ""hacking"".",,,web service,"project management, civic hacking",In Progress''', {'content-type': 'text/csv; charset=UTF-8'})

        else:
            raise Exception('Asked for unknown URL ' + url.geturl())

    def test_import(self):
        ''' Add one sample organization with two projects and issues, verify that it comes back.
        '''

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            import run_update
            run_update.main(org_sources="test_org_sources.csv")

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
        filter = Project.name == u'bizfriendly-web'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.status, u'')

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
        from factories import OrganizationFactory, ProjectFactory, EventFactory, IssueFactory

        old_organization = OrganizationFactory(name=u'Old Organization')
        old_project = ProjectFactory(name=u'Old Project', organization_name=u'Old Organization')
        old_event = EventFactory(name=u'Old Event', organization_name=u'Old Organization')
        old_issue = IssueFactory(title=u'Old Issue', project_id=1)
        self.db.session.flush()

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            import run_update
            run_update.main(org_sources="test_org_sources.csv")

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
        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(404, '''Not Found!''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/issues':
                return response(404, '''Not Found!''', {'ETag': '8456bc53d4cf6b78779ded3408886f82'})

        logging.error = Mock()

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")

        logging.error.assert_called_with('https://api.github.com/repos/codeforamerica/cityvoice doesn\'t exist.')

    def test_main_with_github_errors(self):
        ''' When github returns a non-404 error code, an IOError should be raised.
        '''
        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(422, '''Unprocessable Entity''')

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                self.assertFalse(run_update.github_throttling)
                with self.assertRaises(IOError):
                    run_update.main(org_sources="test_org_sources.csv")

    def test_main_with_weird_organization_name(self):
        ''' When an organization has a weird name, ...
        '''
        def overwrite_response_content(url, request):
            if "docs.google.com" in url:
                return response(200, '''name\nCode_for-America''')

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")
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

        def overwrite_response_content(url, request):
            return response(200, '''name\nCode#America\nCode?America\nCode/America\nCode for America''')

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")
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
        def overwrite_response_content(url, request):
            if "docs.google.com" in url:
                return response(200, '''name,events_url\nCode for America,http://www.meetup.com/events/foo-%%%''')

        logging.error = Mock()

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")

        logging.error.assert_called_with('Code for America does not have a valid events url')

        from app import Event

        # Make sure no events exist
        events_count = self.db.session.query(Event).count()
        self.assertEqual(events_count, 0)

    def test_main_with_non_existant_meetup(self):
        ''' When meetup returns a 404 for an organization's events url, an error
            message should be logged
        '''
        def overwrite_response_content(url, request):
            if "docs.google.com" in url:
                return response(200, '''name,events_url\nCode for America,http://www.meetup.com/events/Code-For-Charlotte''')

            if 'api.meetup.com' in url:
                return response(404, '''Not Found!''')

        logging.error = Mock()
        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")

        logging.error.assert_called_with('Code for America\'s meetup page cannot be found')

    def test_main_with_stories(self):
        '''
        Test that two most recent blog posts are in the db.
        '''
        self.setup_mock_rss_response()

        from factories import OrganizationFactory
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
        def overwrite_response_content(url, request):
            if url.netloc == 'api.github.com':
                return response(403, "", {"x-ratelimit-remaining": 0})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")

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
        from factories import OrganizationFactory
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
        from factories import OrganizationFactory
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

    def test_org_sources_csv(self):
        '''Test that there is a csv file with links to lists of organizations
        '''
        import run_update
        self.assertTrue(os.path.exists(run_update.ORG_SOURCES))

    def test_utf8_noncode_projects(self):
        ''' Test that utf8 project descriptions match exisiting projects.
        '''
        from factories import OrganizationFactory, ProjectFactory

        philly = OrganizationFactory(name=u'Code for Philly', projects_list_url=u'http://codeforphilly.org/projects.csv')
        old_project = ProjectFactory(name=u'Philly Map of Shame', organization_name=u'Code for Philly', description=u'PHL Map of Shame is a citizen-led project to map the impact of the School Reform Commission\u2019s \u201cdoomsday budget\u201d on students and parents. We will visualize complaints filed with the Pennsylvania Department of Education.', categories=u'Education, CivicEngagement', type=u'', link_url=u'http://phillymapofshame.org', status=u'In Progress')
        self.db.session.flush()

        def overwrite_response_content(url, request):
            if url.geturl() == 'http://codeforphilly.org/projects.csv':
                return response(200, '''"name","description","link_url","code_url","type","categories","status"\r\n"Philly Map of Shame","PHL Map of Shame is a citizen-led project to map the impact of the School Reform Commission\xe2\x80\x99s \xe2\x80\x9cdoomsday budget\xe2\x80\x9d on students and parents. We will visualize complaints filed with the Pennsylvania Department of Education.","http://phillymapofshame.org","","","Education, CivicEngagement","In Progress"''', {'content-type': 'text/csv; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                projects = run_update.get_projects(philly)
                # If the two descriptions are equal, it won't update last_updated
                assert projects[0]['last_updated'] == None

    def test_issue_paging(self):
        ''' test that issues are following page links '''
        from factories import OrganizationFactory, ProjectFactory

        organization = OrganizationFactory(name=u'Code for America', projects_list_url=u'http://codeforamerica.org/projects.csv')
        project = ProjectFactory(organization_name=u'Code for America',code_url=u'https://github.com/TESTORG/TESTPROJECT')
        self.db.session.flush()

        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/TESTORG/TESTPROJECT/issues':
                content = '''[{"number": 2,"title": "TEST TITLE 2","body": "TEST BODY 2","labels": [], "html_url":""}]'''
                headers = {"Link": '<https://api.github.com/repos/TESTORG/TESTPROJECT/issues?page=2>"; rel="next"', 'ETag': 'TEST ETAG'}
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
        from factories import OrganizationFactory
        organization = OrganizationFactory(projects_list_url=u'http://organization.org/projects.csv')

        def overwrite_response_content(url, request):
            if url.geturl() == 'http://organization.org/projects.csv':
                return response(200, '''name,description,link_url\n,,http://fakeprojectone.com\n,,,http://whatever.com/testproject''', {'content-type': 'text/csv; charset=UTF-8'})

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                projects = run_update.get_projects(organization)
                assert len(projects) == 2

    def test_html_returned_for_csv_project_list(self):
        ''' We requested a CSV project list and got HTML instead
        '''
        from factories import OrganizationFactory
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
        from app import Project
        import run_update

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources="test_org_sources.csv")
            self.db.session.query(Project).update({"last_updated": None})
            run_update.main(org_name=u"C\xf6de for Ameri\xe7a", org_sources="test_org_sources.csv")

        # :TODO: no assertion?

    def test_orphan_labels(self):
        ''' We keep getting orphan labels,
            run_update twice and check for orphan labels.
        '''
        from app import Label
        import run_update

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            run_update.main(org_sources="test_org_sources.csv")
            run_update.main(org_sources="test_org_sources.csv")

        labels = self.db.session.query(Label).all()
        for label in labels:
            self.assertIsNotNone(label.issue_id)

    def test_duplicate_labels(self):
        ''' Getting many duplicate labels on issues.
        '''
        from app import Label
        import run_update

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            run_update.main(org_sources="test_org_sources.csv")
            run_update.main(org_sources="test_org_sources.csv")

        labels = self.db.session.query(Label).all()
        unique_labels = []

        for label in labels:
            assert (label.issue_id, label.name) not in unique_labels
            unique_labels.append((label.issue_id, label.name))

    def test_unicode_warning(self):
        ''' Testing for the postgres unicode warning
        '''
        import run_update
        import warnings

        warnings.filterwarnings('error')

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            run_update.main(org_sources="test_org_sources.csv")

    def test_orphaned_organization_deleted(self):
        ''' Make sure that an organization and all its children are deleted when
            the organization is no longer included in the returned csv
        '''
        from app import Organization, Project, Event, Story, Issue, Label
        import run_update

        test_sources = "test_org_sources.csv"
        self.organization_count = 3
        full_orgs_list = []

        self.setup_mock_rss_response()

        with HTTMock(self.response_content):
            # get the orgs list for comparison
            full_orgs_list = run_update.get_organizations(test_sources)
            # run the update on the same orgs
            run_update.main(org_sources=test_sources)

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
            partial_orgs_list = run_update.get_organizations(test_sources)

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
            run_update.main(org_sources=test_sources)

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
        from app import Organization, Project, Event, Story, Issue, Label
        import run_update

        test_sources = 'test_org_sources.csv'

        self.setup_mock_rss_response()

        # for checking data from the source against what's in the database
        check_orgs = []
        check_events = {}
        check_stories = {}
        check_projects = {}
        check_issues = {}

        with HTTMock(self.response_content):
            # run the update
            run_update.main(org_sources=test_sources)

            # get raw data from the source to compare with what's in the database
            check_orgs = run_update.get_organizations(test_sources)
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
        from app import Project
        import run_update

        test_sources = "test_org_sources.csv"

        self.setup_mock_rss_response()

        # save the default response for the cityvoice project
        body_text = None
        headers_dict = None
        with HTTMock(self.response_content):
            from requests import get
            got = get('https://api.github.com/repos/codeforamerica/cityvoice')
            body_text = str(got.text)
            headers_dict = got.headers

        # overwrite to return a 304 (not modified) instead of a 200 for the cityvoice project
        def overwrite_response_content(url, request):
            if url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(304, body_text, headers_dict)

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                # run the update on the same orgs
                run_update.main(org_sources=test_sources)

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

    def test_repo_name_used_for_missing_project_name(self):
        ''' Verify that a repo name will be used when no project name is available
        '''
        from app import Organization, Project
        import run_update

        test_sources = 'test_org_sources.csv'

        self.setup_mock_rss_response()

        # only get one organization
        self.organization_count = 1

        with HTTMock(self.response_content):
            # run the update
            run_update.main(org_sources=test_sources)

            # verify only one organization was returned
            organizations = self.db.session.query(Organization).all()
            self.assertTrue(len(organizations) is 1)

        # now get the projects from the database
        projects = self.db.session.query(Project).all()
        for project in projects:
            # verify that the project name isn't empty
            self.assertTrue(project.name not in [u'', None])
            # verify that the project name is the same as the repo name
            self.assertTrue(project.name == project.github_details['name'])

        # reset to defaults
        self.organization_count = 3

    def test_bad_events_json(self):
        ''' Verify that a call for event data that returns bad or no json is handled
        '''
        def overwrite_response_content(url, request):
            if 'meetup.com' in url.geturl() and 'Code-For-Charlotte' in url.geturl():
                return response(200, 'no json object can be decoded from me')

            elif 'meetup.com' in url.geturl() and 'Code-For-Rhode-Island' in url.geturl():
                return response(200, None)

        with HTTMock(self.response_content):
            with HTTMock(overwrite_response_content):
                import run_update
                run_update.main(org_sources="test_org_sources.csv")

        # Make sure no events exist
        from app import Event
        self.assertEqual(self.db.session.query(Event).count(), 0)

    def test_unmodified_projects_stay_in_database(self):
        ''' Verify that unmodified projects are not deleted from the database
        '''
        from app import Project
        import run_update

        test_sources = "test_org_sources.csv"

        self.setup_mock_rss_response()

        # run a standard run_update
        with HTTMock(self.response_content):
            run_update.main(org_sources=test_sources)

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
                run_update.main(org_sources=test_sources)

        # verify that the same number of projects are in the database
        self.assertEqual(project_count, self.db.session.query(Project).count())


if __name__ == '__main__':
    unittest.main()
