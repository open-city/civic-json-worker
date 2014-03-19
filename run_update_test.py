import os
import unittest
import tempfile
from httmock import response, HTTMock
from mock import Mock
import requests

class FakeResponse:
    def __init__(self, text):
        self.text = text

class RunUpdateTestCase(unittest.TestCase):

    def setUp(self):
        os.environ['DATABASE_URL'] = 'postgres://postgres@localhost/civic_json_worker_test'
        os.environ['SECRET_KEY'] = '123456'

        from app import db

        self.db = db
        self.db.create_all()

    def tearDown(self):
        self.db.session.close()
        self.db.drop_all()

    def mock_rss_response(self):
        import urllib2

        rss_file=open('blog.xml')
        rss_content = rss_file.read()
        rss_file.close()
        urllib2.urlopen = Mock()
        urllib2.urlopen.return_value.read = Mock(return_value=rss_content)
        return urllib2.urlopen

    def response_content(self, url, request):
        import run_update

        if url.geturl() == 'http://example.com/cfa-projects.csv':
            return response(200, '''name,description,link_url,code_url,type,categories\n,,,https://github.com/codeforamerica/cityvoice,web service,"community engagement, housing"\nSouthBendVoices,,,https://github.com/codeforamerica/cityvoice,,''')

        elif url.geturl() == run_update.gdocs_url:
            return response(200, '''name,website,events_url,rss,projects_list_url\nCode for America,http://codeforamerica.org,http://www.meetup.com/events/Code-For-Charlotte/,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv''')

        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
            return response(200, '''{ "id": 10515516, "name": "cityvoice", "full_name": "codeforamerica/cityvoice", "owner": { "login": "codeforamerica", "id": 337792, "avatar_url": "https://avatars.githubusercontent.com/u/337792", "gravatar_id": "ec81184c572bc827b72ebb489d49f821", "url": "https://api.github.com/users/codeforamerica", "html_url": "https://github.com/codeforamerica", "followers_url": "https://api.github.com/users/codeforamerica/followers", "following_url": "https://api.github.com/users/codeforamerica/following{/other_user}", "gists_url": "https://api.github.com/users/codeforamerica/gists{/gist_id}", "starred_url": "https://api.github.com/users/codeforamerica/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/codeforamerica/subscriptions", "organizations_url": "https://api.github.com/users/codeforamerica/orgs", "repos_url": "https://api.github.com/users/codeforamerica/repos", "events_url": "https://api.github.com/users/codeforamerica/events{/privacy}", "received_events_url": "https://api.github.com/users/codeforamerica/received_events", "type": "Organization", "site_admin": false }, "private": false, "html_url": "https://github.com/codeforamerica/cityvoice", "description": "A place-based call-in system for gathering and sharing community feedback", "fork": false, "url": "https://api.github.com/repos/codeforamerica/cityvoice", "forks_url": "https://api.github.com/repos/codeforamerica/cityvoice/forks", "keys_url": "https://api.github.com/repos/codeforamerica/cityvoice/keys{/key_id}", "collaborators_url": "https://api.github.com/repos/codeforamerica/cityvoice/collaborators{/collaborator}", "teams_url": "https://api.github.com/repos/codeforamerica/cityvoice/teams", "hooks_url": "https://api.github.com/repos/codeforamerica/cityvoice/hooks", "issue_events_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues/events{/number}", "events_url": "https://api.github.com/repos/codeforamerica/cityvoice/events", "assignees_url": "https://api.github.com/repos/codeforamerica/cityvoice/assignees{/user}", "branches_url": "https://api.github.com/repos/codeforamerica/cityvoice/branches{/branch}", "tags_url": "https://api.github.com/repos/codeforamerica/cityvoice/tags", "blobs_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs{/sha}", "git_tags_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/tags{/sha}", "git_refs_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/refs{/sha}", "trees_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/trees{/sha}", "statuses_url": "https://api.github.com/repos/codeforamerica/cityvoice/statuses/{sha}", "languages_url": "https://api.github.com/repos/codeforamerica/cityvoice/languages", "stargazers_url": "https://api.github.com/repos/codeforamerica/cityvoice/stargazers", "contributors_url": "https://api.github.com/repos/codeforamerica/cityvoice/contributors", "subscribers_url": "https://api.github.com/repos/codeforamerica/cityvoice/subscribers", "subscription_url": "https://api.github.com/repos/codeforamerica/cityvoice/subscription", "commits_url": "https://api.github.com/repos/codeforamerica/cityvoice/commits{/sha}", "git_commits_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/commits{/sha}", "comments_url": "https://api.github.com/repos/codeforamerica/cityvoice/comments{/number}", "issue_comment_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues/comments/{number}", "contents_url": "https://api.github.com/repos/codeforamerica/cityvoice/contents/{+path}", "compare_url": "https://api.github.com/repos/codeforamerica/cityvoice/compare/{base}...{head}", "merges_url": "https://api.github.com/repos/codeforamerica/cityvoice/merges", "archive_url": "https://api.github.com/repos/codeforamerica/cityvoice/{archive_format}{/ref}", "downloads_url": "https://api.github.com/repos/codeforamerica/cityvoice/downloads", "issues_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues{/number}", "pulls_url": "https://api.github.com/repos/codeforamerica/cityvoice/pulls{/number}", "milestones_url": "https://api.github.com/repos/codeforamerica/cityvoice/milestones{/number}", "notifications_url": "https://api.github.com/repos/codeforamerica/cityvoice/notifications{?since,all,participating}", "labels_url": "https://api.github.com/repos/codeforamerica/cityvoice/labels{/name}", "releases_url": "https://api.github.com/repos/codeforamerica/cityvoice/releases{/id}", "created_at": "2013-06-06T00:12:30Z", "updated_at": "2014-02-21T20:43:16Z", "pushed_at": "2014-02-21T20:43:16Z", "git_url": "git://github.com/codeforamerica/cityvoice.git", "ssh_url": "git@github.com:codeforamerica/cityvoice.git", "clone_url": "https://github.com/codeforamerica/cityvoice.git", "svn_url": "https://github.com/codeforamerica/cityvoice", "homepage": "http://www.cityvoiceapp.com/", "size": 6290, "stargazers_count": 10, "watchers_count": 10, "language": "Ruby", "has_issues": true, "has_downloads": true, "has_wiki": true, "forks_count": 12, "mirror_url": null, "open_issues_count": 37, "forks": 12, "open_issues": 37, "watchers": 10, "default_branch": "master", "master_branch": "master", "organization": { "login": "codeforamerica", "id": 337792, "avatar_url": "https://avatars.githubusercontent.com/u/337792", "gravatar_id": "ec81184c572bc827b72ebb489d49f821", "url": "https://api.github.com/users/codeforamerica", "html_url": "https://github.com/codeforamerica", "followers_url": "https://api.github.com/users/codeforamerica/followers", "following_url": "https://api.github.com/users/codeforamerica/following{/other_user}", "gists_url": "https://api.github.com/users/codeforamerica/gists{/gist_id}", "starred_url": "https://api.github.com/users/codeforamerica/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/codeforamerica/subscriptions", "organizations_url": "https://api.github.com/users/codeforamerica/orgs", "repos_url": "https://api.github.com/users/codeforamerica/repos", "events_url": "https://api.github.com/users/codeforamerica/events{/privacy}", "received_events_url": "https://api.github.com/users/codeforamerica/received_events", "type": "Organization", "site_admin": false }, "network_count": 12, "subscribers_count": 42 }''')

        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/contributors':
            return response(200, '''[ { "login": "daguar", "id": 994938, "avatar_url": "https://avatars.githubusercontent.com/u/994938", "gravatar_id": "bdd8cc46ae86e389388ae78dfc45effe", "url": "https://api.github.com/users/daguar", "html_url": "https://github.com/daguar", "followers_url": "https://api.github.com/users/daguar/followers", "following_url": "https://api.github.com/users/daguar/following{/other_user}", "gists_url": "https://api.github.com/users/daguar/gists{/gist_id}", "starred_url": "https://api.github.com/users/daguar/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/daguar/subscriptions", "organizations_url": "https://api.github.com/users/daguar/orgs", "repos_url": "https://api.github.com/users/daguar/repos", "events_url": "https://api.github.com/users/daguar/events{/privacy}", "received_events_url": "https://api.github.com/users/daguar/received_events", "type": "User", "site_admin": false, "contributions": 518 }, { "login": "rduecyg", "id": 1710759, "avatar_url": "https://avatars.githubusercontent.com/u/1710759", "gravatar_id": "ca617a981a0ba8423eb849843b21693c", "url": "https://api.github.com/users/rduecyg", "html_url": "https://github.com/rduecyg", "followers_url": "https://api.github.com/users/rduecyg/followers", "following_url": "https://api.github.com/users/rduecyg/following{/other_user}", "gists_url": "https://api.github.com/users/rduecyg/gists{/gist_id}", "starred_url": "https://api.github.com/users/rduecyg/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/rduecyg/subscriptions", "organizations_url": "https://api.github.com/users/rduecyg/orgs", "repos_url": "https://api.github.com/users/rduecyg/repos", "events_url": "https://api.github.com/users/rduecyg/events{/privacy}", "received_events_url": "https://api.github.com/users/rduecyg/received_events", "type": "User", "site_admin": false, "contributions": 159 }, { "login": "mholubowski", "id": 2035619, "avatar_url": "https://avatars.githubusercontent.com/u/2035619", "gravatar_id": "76743e4c14368f817ea4fff3c7e72b34", "url": "https://api.github.com/users/mholubowski", "html_url": "https://github.com/mholubowski", "followers_url": "https://api.github.com/users/mholubowski/followers", "following_url": "https://api.github.com/users/mholubowski/following{/other_user}", "gists_url": "https://api.github.com/users/mholubowski/gists{/gist_id}", "starred_url": "https://api.github.com/users/mholubowski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mholubowski/subscriptions", "organizations_url": "https://api.github.com/users/mholubowski/orgs", "repos_url": "https://api.github.com/users/mholubowski/repos", "events_url": "https://api.github.com/users/mholubowski/events{/privacy}", "received_events_url": "https://api.github.com/users/mholubowski/received_events", "type": "User", "site_admin": false, "contributions": 26 }, { "login": "mick", "id": 26278, "avatar_url": "https://avatars.githubusercontent.com/u/26278", "gravatar_id": "0a57f29a6d300554ed45c80b4e37ab49", "url": "https://api.github.com/users/mick", "html_url": "https://github.com/mick", "followers_url": "https://api.github.com/users/mick/followers", "following_url": "https://api.github.com/users/mick/following{/other_user}", "gists_url": "https://api.github.com/users/mick/gists{/gist_id}", "starred_url": "https://api.github.com/users/mick/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mick/subscriptions", "organizations_url": "https://api.github.com/users/mick/orgs", "repos_url": "https://api.github.com/users/mick/repos", "events_url": "https://api.github.com/users/mick/events{/privacy}", "received_events_url": "https://api.github.com/users/mick/received_events", "type": "User", "site_admin": false, "contributions": 1 }, { "login": "migurski", "id": 58730, "avatar_url": "https://avatars.githubusercontent.com/u/58730", "gravatar_id": "039667155d1baa533e461671e97891a1", "url": "https://api.github.com/users/migurski", "html_url": "https://github.com/migurski", "followers_url": "https://api.github.com/users/migurski/followers", "following_url": "https://api.github.com/users/migurski/following{/other_user}", "gists_url": "https://api.github.com/users/migurski/gists{/gist_id}", "starred_url": "https://api.github.com/users/migurski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/migurski/subscriptions", "organizations_url": "https://api.github.com/users/migurski/orgs", "repos_url": "https://api.github.com/users/migurski/repos", "events_url": "https://api.github.com/users/migurski/events{/privacy}", "received_events_url": "https://api.github.com/users/migurski/received_events", "type": "User", "site_admin": false, "contributions": 1 } ]''')

        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/stats/participation':
            return response(200, '''{ "all": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 23, 9, 4, 0, 77, 26, 7, 17, 53, 59, 37, 40, 0, 47, 59, 55, 118, 11, 8, 3, 3, 30, 0, 1, 1, 4, 6, 1, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1 ], "owner": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ] }''')

        elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/issues?labels=project-needs':
            return response(200, '''[ ]''')

        elif url.geturl() == 'https://api.github.com/users/daguar':
            return response(200, '''{ "login": "daguar", "id": 994938, "avatar_url": "https://gravatar.com/avatar/bdd8cc46ae86e389388ae78dfc45effe?d=https%3A%2F%2Fidenticons.github.com%2F4b102bf6681e25c44a3c980791826c1f.png&r=x", "gravatar_id": "bdd8cc46ae86e389388ae78dfc45effe", "url": "https://api.github.com/users/daguar", "html_url": "https://github.com/daguar", "followers_url": "https://api.github.com/users/daguar/followers", "following_url": "https://api.github.com/users/daguar/following{/other_user}", "gists_url": "https://api.github.com/users/daguar/gists{/gist_id}", "starred_url": "https://api.github.com/users/daguar/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/daguar/subscriptions", "organizations_url": "https://api.github.com/users/daguar/orgs", "repos_url": "https://api.github.com/users/daguar/repos", "events_url": "https://api.github.com/users/daguar/events{/privacy}", "received_events_url": "https://api.github.com/users/daguar/received_events", "type": "User", "site_admin": false, "name": "Dave Guarino", "company": "", "blog": null, "location": "Oakland, CA", "email": "dave@codeforamerica.org", "hireable": true, "bio": null, "public_repos": 66, "public_gists": 10, "followers": 30, "following": 14, "created_at": "2011-08-21T21:12:10Z", "updated_at": "2014-03-07T18:17:21Z" }''')

        elif url.geturl() == 'https://api.github.com/users/mholubowski':
            return response(200, '''{ "login": "mholubowski", "id": 2035619, "avatar_url": "https://gravatar.com/avatar/76743e4c14368f817ea4fff3c7e72b34?d=https%3A%2F%2Fidenticons.github.com%2Fbcc9be8dba131f187a3750a001e9d330.png&r=x", "gravatar_id": "76743e4c14368f817ea4fff3c7e72b34", "url": "https://api.github.com/users/mholubowski", "html_url": "https://github.com/mholubowski", "followers_url": "https://api.github.com/users/mholubowski/followers", "following_url": "https://api.github.com/users/mholubowski/following{/other_user}", "gists_url": "https://api.github.com/users/mholubowski/gists{/gist_id}", "starred_url": "https://api.github.com/users/mholubowski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mholubowski/subscriptions", "organizations_url": "https://api.github.com/users/mholubowski/orgs", "repos_url": "https://api.github.com/users/mholubowski/repos", "events_url": "https://api.github.com/users/mholubowski/events{/privacy}", "received_events_url": "https://api.github.com/users/mholubowski/received_events", "type": "User", "site_admin": false, "public_repos": 16, "public_gists": 6, "followers": 8, "following": 0, "created_at": "2012-07-24T17:46:53Z", "updated_at": "2014-03-07T07:23:50Z" }''')

        elif url.geturl() == 'https://api.github.com/users/mick':
            return response(200, '''{ "login": "mick", "id": 26278, "avatar_url": "https://gravatar.com/avatar/0a57f29a6d300554ed45c80b4e37ab49?d=https%3A%2F%2Fidenticons.github.com%2F523d0b250cf3fc7a5a04aec43fd55e43.png&r=x", "gravatar_id": "0a57f29a6d300554ed45c80b4e37ab49", "url": "https://api.github.com/users/mick", "html_url": "https://github.com/mick", "followers_url": "https://api.github.com/users/mick/followers", "following_url": "https://api.github.com/users/mick/following{/other_user}", "gists_url": "https://api.github.com/users/mick/gists{/gist_id}", "starred_url": "https://api.github.com/users/mick/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mick/subscriptions", "organizations_url": "https://api.github.com/users/mick/orgs", "repos_url": "https://api.github.com/users/mick/repos", "events_url": "https://api.github.com/users/mick/events{/privacy}", "received_events_url": "https://api.github.com/users/mick/received_events", "type": "User", "site_admin": false, "name": "Mick Thompson", "company": "Mapbox", "blog": "http://mick.im", "location": "San Francisco, CA", "email": "dthompson@gmail.com", "hireable": false, "bio": null, "public_repos": 86, "public_gists": 22, "followers": 103, "following": 32, "created_at": "2008-09-25T18:17:08Z", "updated_at": "2014-03-07T20:59:59Z" }''')

        elif url.geturl() == 'https://api.github.com/users/migurski':
            return response(200, '''{ "login": "migurski", "id": 58730, "avatar_url": "https://gravatar.com/avatar/039667155d1baa533e461671e97891a1?d=https%3A%2F%2Fidenticons.github.com%2F5ad9088b8b4fba5e76050c6c12f31a00.png&r=x", "gravatar_id": "039667155d1baa533e461671e97891a1", "url": "https://api.github.com/users/migurski", "html_url": "https://github.com/migurski", "followers_url": "https://api.github.com/users/migurski/followers", "following_url": "https://api.github.com/users/migurski/following{/other_user}", "gists_url": "https://api.github.com/users/migurski/gists{/gist_id}", "starred_url": "https://api.github.com/users/migurski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/migurski/subscriptions", "organizations_url": "https://api.github.com/users/migurski/orgs", "repos_url": "https://api.github.com/users/migurski/repos", "events_url": "https://api.github.com/users/migurski/events{/privacy}", "received_events_url": "https://api.github.com/users/migurski/received_events", "type": "User", "site_admin": false, "name": null, "company": null, "blog": "", "location": "", "email": "mike-github@teczno.com", "hireable": false, "bio": null, "public_repos": 67, "public_gists": 37, "followers": 305, "following": 78, "created_at": "2009-02-27T23:44:32Z", "updated_at": "2014-03-07T06:11:45Z" }''')

        elif url.geturl() == 'https://api.github.com/users/rduecyg':
            return response(200, '''{ "login": "rduecyg", "id": 1710759, "avatar_url": "https://gravatar.com/avatar/ca617a981a0ba8423eb849843b21693c?d=https%3A%2F%2Fidenticons.github.com%2F839df3551000263ba8c19e291482a371.png&r=x", "gravatar_id": "ca617a981a0ba8423eb849843b21693c", "url": "https://api.github.com/users/rduecyg", "html_url": "https://github.com/rduecyg", "followers_url": "https://api.github.com/users/rduecyg/followers", "following_url": "https://api.github.com/users/rduecyg/following{/other_user}", "gists_url": "https://api.github.com/users/rduecyg/gists{/gist_id}", "starred_url": "https://api.github.com/users/rduecyg/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/rduecyg/subscriptions", "organizations_url": "https://api.github.com/users/rduecyg/orgs", "repos_url": "https://api.github.com/users/rduecyg/repos", "events_url": "https://api.github.com/users/rduecyg/events{/privacy}", "received_events_url": "https://api.github.com/users/rduecyg/received_events", "type": "User", "site_admin": false, "name": "Reed", "company": null, "blog": null, "location": null, "email": null, "hireable": false, "bio": null, "public_repos": 8, "public_gists": 0, "followers": 1, "following": 0, "created_at": "2012-05-06T14:39:37Z", "updated_at": "2014-03-04T20:33:45Z" }''')

        elif url.geturl() == 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=Code-For-Charlotte&sig_id=None':
            events_file=open('meetup_events.json')
            events_content = events_file.read()
            events_file.close()
            return response(200, events_content)

        else:
            raise Exception('Asked for unknown URL ' + url.geturl())

    def test_import(self):
        ''' Add one sample organization with two projects, verify that it comes back.
        '''
        with HTTMock(self.response_content):
            import run_update

            # Iterate over organizations and projects, saving them to db.session.
            for org_info in run_update.get_organizations():
                organization = run_update.save_organization_info(self.db.session, org_info)

                projects = run_update.get_projects(organization)

                for proj_info in projects:
                    run_update.save_project_info(self.db.session, proj_info)

        self.db.session.flush()

        from app import Organization, Project

        # check for the one organization
        filter = Organization.name == 'Code for America'
        organization = self.db.session.query(Organization).filter(filter).first()
        self.assertIsNotNone(organization)
        self.assertEqual(organization.name,'Code for America')

        # check for the one project
        filter = Project.name == 'SouthBendVoices'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.name,'SouthBendVoices')

        # check for the other project
        filter = Project.name == 'cityvoice'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.name,'cityvoice')

    def test_main_with_good_new_data(self):
        ''' When current organization data is not the same set as existing, saved organization data,
            the new organization, its project, and events should be saved. The out of date
            organization, its project and event should be deleted.
        '''
        from factories import OrganizationFactory, ProjectFactory, EventFactory

        old_organization = OrganizationFactory(name='Old Organization')
        old_project = ProjectFactory(name='Old Project', organization_name='Old Organization')
        old_event = EventFactory(name='Old Event', organization_name='Old Organization')
        self.db.session.flush()

        self.mock_rss_response()

        with HTTMock(self.response_content):
            import run_update
            run_update.main()

        self.db.session.flush()

        from app import Organization, Project, Event

        # make sure old org is no longer there
        filter = Organization.name == 'Old Organization'
        organization = self.db.session.query(Organization).filter(filter).first()
        self.assertIsNone(organization)

        # make sure old project is no longer there
        filter = Project.name == 'Old Project'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertIsNone(project)

        # make sure old event is no longer there
        filter = Event.name == 'Old Event'
        event = self.db.session.query(Event).filter(filter).first()
        self.assertIsNone(event)

        # check for the one organization
        filter = Organization.name == 'Code for America'
        organization = self.db.session.query(Organization).filter(filter).first()
        self.assertEqual(organization.name,'Code for America')

        # check for the one project
        filter = Project.name == 'SouthBendVoices'
        project = self.db.session.query(Project).filter(filter).first()
        self.assertEqual(project.name,'SouthBendVoices')

        # check for events
        filter = Event.name.in_(['Organizational meeting',
                                 'Code Across: Launch event',
                                 'Brigade Ideation (Brainstorm and Prototyping) Session.'])
        events = self.db.session.query(Event).filter(filter).all()

        first_event = events.pop(0)
        self.assertEqual(first_event.name, 'Organizational meeting')

        second_event = events.pop(0)
        self.assertEqual(second_event.name, 'Code Across: Launch event')

        third_event = events.pop(0)
        self.assertEqual(third_event.name, 'Brigade Ideation (Brainstorm and Prototyping) Session.')

    def test_main_with_missing_projects(self):
        ''' When github returns a 404 when trying to retrieve project data,
            an error message should be logged.
        '''
        def response_content(url, request):
            import run_update

            if url.geturl() == 'http://example.com/cfa-projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories\n,,,https://github.com/codeforamerica/cityvoice,web service,"community engagement, housing"\nSouthBendVoices,,,https://github.com/codeforamerica/cityvoice,,''')

            elif url.geturl() == run_update.gdocs_url:
                return response(200, '''name,website,events_url,rss,projects_list_url\nCode for America,http://codeforamerica.org,http://www.meetup.com/events/Code-For-Charlotte/,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(404, '''Not Found!''')

            elif url.geturl() == 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=Code-For-Charlotte&sig_id=None':
                events_file=open('meetup_events.json')
                events_content = events_file.read()
                events_file.close()
                return response(200, events_content)

            else:
                raise Exception('Asked for unknown URL ' + url.geturl())

        import logging
        logging.error = Mock()

        self.mock_rss_response()

        with HTTMock(response_content):
            import run_update
            run_update.main()

        logging.error.assert_called_with('https://api.github.com/repos/codeforamerica/cityvoice doesn\'t exist.')

    def test_main_with_github_errors(self):
        ''' When github returns a non-404 error code, an IOError should be raised.
        '''
        def response_content(url, request):
            import run_update

            if url.geturl() == 'http://example.com/cfa-projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories\n,,,https://github.com/codeforamerica/cityvoice,web service,"community engagement, housing"\nSouthBendVoices,,,https://github.com/codeforamerica/cityvoice,,''')

            elif url.geturl() == run_update.gdocs_url:
                return response(200, '''name,website,events_url,rss,projects_list_url\nCode for America,http://codeforamerica.org,http://codeforamerica.org/events,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(422, '''Unprocessable Entity''')

        with HTTMock(response_content):
            import run_update
            self.assertRaises(IOError, run_update.main)

    def test_json_files(self):
        ''' Check the structure of proposed Civic JSON data structures.

            See discussion at
            https://github.com/codeforamerica/civic-json-worker/issues/18
        '''
        projects_detail = []

        with HTTMock(self.response_content):
            import run_update as ru

            # Iterate over organizations and projects, saving them to db.session.
            for org_info in ru.get_organizations():
                organization = ru.save_organization_info(self.db.session, org_info)

                projects = ru.get_projects(organization)
                project_details = ru.reformat_project_info_for_chicago(projects)
                projects_detail.append(project_details)

            for project_details in projects_detail:
                #
                # Verify correct output format for project_details.json.
                #
                for project in project_details:
                    for key in ('contributors', 'contributors_url', 'created_at',
                                'description', 'forks_count', 'homepage', 'html_url',
                                'id', 'language', 'name', 'open_issues', 'owner',
                                'participation', 'project_needs', 'pushed_at',
                                'updated_at', 'watchers_count'):
                        assert key in project

                    # project owner dict
                    for key in ('avatar_url', 'html_url', 'login', 'type'):
                        assert key in project['owner']

                    # project contributor list
                    for contributor in project['contributors']:
                        for key in ('avatar_url', 'contributions', 'html_url',
                                    'login', 'owner', 'url'):
                            assert key in contributor

                    # project participation history
                    assert type(project['participation']) is list

                #
                # Verify correct output format for people.json.
                #
                people = ru.count_people_totals(project_details)

                for person in people:
                    for key in ('company', 'repositories', 'html_url', 'blog',
                                'avatar_url', 'location', 'login', 'contributions'):
                        assert key in person

    def test_main_with_bad_events_url(self):
        ''' When an organization has a badly formed events url is passed, no events are saved
        '''
        def response_content(url, request):
            import run_update

            if url.geturl() == 'http://example.com/cfa-projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories\n,,,https://github.com/codeforamerica/cityvoice,web service,"community engagement, housing"\nSouthBendVoices,,,https://github.com/codeforamerica/cityvoice,,''')

            elif url.geturl() == run_update.gdocs_url:
                return response(200, '''name,website,events_url,rss,projects_list_url\nCode for America,http://codeforamerica.org,http://www.meetup.com/events/foo-%%%,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(200, '''{ "id": 10515516, "name": "cityvoice", "full_name": "codeforamerica/cityvoice", "owner": { "login": "codeforamerica", "id": 337792, "avatar_url": "https://avatars.githubusercontent.com/u/337792", "gravatar_id": "ec81184c572bc827b72ebb489d49f821", "url": "https://api.github.com/users/codeforamerica", "html_url": "https://github.com/codeforamerica", "followers_url": "https://api.github.com/users/codeforamerica/followers", "following_url": "https://api.github.com/users/codeforamerica/following{/other_user}", "gists_url": "https://api.github.com/users/codeforamerica/gists{/gist_id}", "starred_url": "https://api.github.com/users/codeforamerica/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/codeforamerica/subscriptions", "organizations_url": "https://api.github.com/users/codeforamerica/orgs", "repos_url": "https://api.github.com/users/codeforamerica/repos", "events_url": "https://api.github.com/users/codeforamerica/events{/privacy}", "received_events_url": "https://api.github.com/users/codeforamerica/received_events", "type": "Organization", "site_admin": false }, "private": false, "html_url": "https://github.com/codeforamerica/cityvoice", "description": "A place-based call-in system for gathering and sharing community feedback", "fork": false, "url": "https://api.github.com/repos/codeforamerica/cityvoice", "forks_url": "https://api.github.com/repos/codeforamerica/cityvoice/forks", "keys_url": "https://api.github.com/repos/codeforamerica/cityvoice/keys{/key_id}", "collaborators_url": "https://api.github.com/repos/codeforamerica/cityvoice/collaborators{/collaborator}", "teams_url": "https://api.github.com/repos/codeforamerica/cityvoice/teams", "hooks_url": "https://api.github.com/repos/codeforamerica/cityvoice/hooks", "issue_events_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues/events{/number}", "events_url": "https://api.github.com/repos/codeforamerica/cityvoice/events", "assignees_url": "https://api.github.com/repos/codeforamerica/cityvoice/assignees{/user}", "branches_url": "https://api.github.com/repos/codeforamerica/cityvoice/branches{/branch}", "tags_url": "https://api.github.com/repos/codeforamerica/cityvoice/tags", "blobs_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs{/sha}", "git_tags_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/tags{/sha}", "git_refs_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/refs{/sha}", "trees_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/trees{/sha}", "statuses_url": "https://api.github.com/repos/codeforamerica/cityvoice/statuses/{sha}", "languages_url": "https://api.github.com/repos/codeforamerica/cityvoice/languages", "stargazers_url": "https://api.github.com/repos/codeforamerica/cityvoice/stargazers", "contributors_url": "https://api.github.com/repos/codeforamerica/cityvoice/contributors", "subscribers_url": "https://api.github.com/repos/codeforamerica/cityvoice/subscribers", "subscription_url": "https://api.github.com/repos/codeforamerica/cityvoice/subscription", "commits_url": "https://api.github.com/repos/codeforamerica/cityvoice/commits{/sha}", "git_commits_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/commits{/sha}", "comments_url": "https://api.github.com/repos/codeforamerica/cityvoice/comments{/number}", "issue_comment_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues/comments/{number}", "contents_url": "https://api.github.com/repos/codeforamerica/cityvoice/contents/{+path}", "compare_url": "https://api.github.com/repos/codeforamerica/cityvoice/compare/{base}...{head}", "merges_url": "https://api.github.com/repos/codeforamerica/cityvoice/merges", "archive_url": "https://api.github.com/repos/codeforamerica/cityvoice/{archive_format}{/ref}", "downloads_url": "https://api.github.com/repos/codeforamerica/cityvoice/downloads", "issues_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues{/number}", "pulls_url": "https://api.github.com/repos/codeforamerica/cityvoice/pulls{/number}", "milestones_url": "https://api.github.com/repos/codeforamerica/cityvoice/milestones{/number}", "notifications_url": "https://api.github.com/repos/codeforamerica/cityvoice/notifications{?since,all,participating}", "labels_url": "https://api.github.com/repos/codeforamerica/cityvoice/labels{/name}", "releases_url": "https://api.github.com/repos/codeforamerica/cityvoice/releases{/id}", "created_at": "2013-06-06T00:12:30Z", "updated_at": "2014-02-21T20:43:16Z", "pushed_at": "2014-02-21T20:43:16Z", "git_url": "git://github.com/codeforamerica/cityvoice.git", "ssh_url": "git@github.com:codeforamerica/cityvoice.git", "clone_url": "https://github.com/codeforamerica/cityvoice.git", "svn_url": "https://github.com/codeforamerica/cityvoice", "homepage": "http://www.cityvoiceapp.com/", "size": 6290, "stargazers_count": 10, "watchers_count": 10, "language": "Ruby", "has_issues": true, "has_downloads": true, "has_wiki": true, "forks_count": 12, "mirror_url": null, "open_issues_count": 37, "forks": 12, "open_issues": 37, "watchers": 10, "default_branch": "master", "master_branch": "master", "organization": { "login": "codeforamerica", "id": 337792, "avatar_url": "https://avatars.githubusercontent.com/u/337792", "gravatar_id": "ec81184c572bc827b72ebb489d49f821", "url": "https://api.github.com/users/codeforamerica", "html_url": "https://github.com/codeforamerica", "followers_url": "https://api.github.com/users/codeforamerica/followers", "following_url": "https://api.github.com/users/codeforamerica/following{/other_user}", "gists_url": "https://api.github.com/users/codeforamerica/gists{/gist_id}", "starred_url": "https://api.github.com/users/codeforamerica/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/codeforamerica/subscriptions", "organizations_url": "https://api.github.com/users/codeforamerica/orgs", "repos_url": "https://api.github.com/users/codeforamerica/repos", "events_url": "https://api.github.com/users/codeforamerica/events{/privacy}", "received_events_url": "https://api.github.com/users/codeforamerica/received_events", "type": "Organization", "site_admin": false }, "network_count": 12, "subscribers_count": 42 }''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/contributors':
                return response(200, '''[ { "login": "daguar", "id": 994938, "avatar_url": "https://avatars.githubusercontent.com/u/994938", "gravatar_id": "bdd8cc46ae86e389388ae78dfc45effe", "url": "https://api.github.com/users/daguar", "html_url": "https://github.com/daguar", "followers_url": "https://api.github.com/users/daguar/followers", "following_url": "https://api.github.com/users/daguar/following{/other_user}", "gists_url": "https://api.github.com/users/daguar/gists{/gist_id}", "starred_url": "https://api.github.com/users/daguar/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/daguar/subscriptions", "organizations_url": "https://api.github.com/users/daguar/orgs", "repos_url": "https://api.github.com/users/daguar/repos", "events_url": "https://api.github.com/users/daguar/events{/privacy}", "received_events_url": "https://api.github.com/users/daguar/received_events", "type": "User", "site_admin": false, "contributions": 518 }, { "login": "rduecyg", "id": 1710759, "avatar_url": "https://avatars.githubusercontent.com/u/1710759", "gravatar_id": "ca617a981a0ba8423eb849843b21693c", "url": "https://api.github.com/users/rduecyg", "html_url": "https://github.com/rduecyg", "followers_url": "https://api.github.com/users/rduecyg/followers", "following_url": "https://api.github.com/users/rduecyg/following{/other_user}", "gists_url": "https://api.github.com/users/rduecyg/gists{/gist_id}", "starred_url": "https://api.github.com/users/rduecyg/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/rduecyg/subscriptions", "organizations_url": "https://api.github.com/users/rduecyg/orgs", "repos_url": "https://api.github.com/users/rduecyg/repos", "events_url": "https://api.github.com/users/rduecyg/events{/privacy}", "received_events_url": "https://api.github.com/users/rduecyg/received_events", "type": "User", "site_admin": false, "contributions": 159 }, { "login": "mholubowski", "id": 2035619, "avatar_url": "https://avatars.githubusercontent.com/u/2035619", "gravatar_id": "76743e4c14368f817ea4fff3c7e72b34", "url": "https://api.github.com/users/mholubowski", "html_url": "https://github.com/mholubowski", "followers_url": "https://api.github.com/users/mholubowski/followers", "following_url": "https://api.github.com/users/mholubowski/following{/other_user}", "gists_url": "https://api.github.com/users/mholubowski/gists{/gist_id}", "starred_url": "https://api.github.com/users/mholubowski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mholubowski/subscriptions", "organizations_url": "https://api.github.com/users/mholubowski/orgs", "repos_url": "https://api.github.com/users/mholubowski/repos", "events_url": "https://api.github.com/users/mholubowski/events{/privacy}", "received_events_url": "https://api.github.com/users/mholubowski/received_events", "type": "User", "site_admin": false, "contributions": 26 }, { "login": "mick", "id": 26278, "avatar_url": "https://avatars.githubusercontent.com/u/26278", "gravatar_id": "0a57f29a6d300554ed45c80b4e37ab49", "url": "https://api.github.com/users/mick", "html_url": "https://github.com/mick", "followers_url": "https://api.github.com/users/mick/followers", "following_url": "https://api.github.com/users/mick/following{/other_user}", "gists_url": "https://api.github.com/users/mick/gists{/gist_id}", "starred_url": "https://api.github.com/users/mick/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mick/subscriptions", "organizations_url": "https://api.github.com/users/mick/orgs", "repos_url": "https://api.github.com/users/mick/repos", "events_url": "https://api.github.com/users/mick/events{/privacy}", "received_events_url": "https://api.github.com/users/mick/received_events", "type": "User", "site_admin": false, "contributions": 1 }, { "login": "migurski", "id": 58730, "avatar_url": "https://avatars.githubusercontent.com/u/58730", "gravatar_id": "039667155d1baa533e461671e97891a1", "url": "https://api.github.com/users/migurski", "html_url": "https://github.com/migurski", "followers_url": "https://api.github.com/users/migurski/followers", "following_url": "https://api.github.com/users/migurski/following{/other_user}", "gists_url": "https://api.github.com/users/migurski/gists{/gist_id}", "starred_url": "https://api.github.com/users/migurski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/migurski/subscriptions", "organizations_url": "https://api.github.com/users/migurski/orgs", "repos_url": "https://api.github.com/users/migurski/repos", "events_url": "https://api.github.com/users/migurski/events{/privacy}", "received_events_url": "https://api.github.com/users/migurski/received_events", "type": "User", "site_admin": false, "contributions": 1 } ]''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/stats/participation':
                return response(200, '''{ "all": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 23, 9, 4, 0, 77, 26, 7, 17, 53, 59, 37, 40, 0, 47, 59, 55, 118, 11, 8, 3, 3, 30, 0, 1, 1, 4, 6, 1, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1 ], "owner": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ] }''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/issues?labels=project-needs':
                return response(200, '''[ ]''')

            else:
                raise Exception('Asked for unknown URL ' + url.geturl())

        import logging
        logging.error = Mock()

        self.mock_rss_response()

        with HTTMock(response_content):
            import run_update
            run_update.main()

        logging.error.assert_called_with('Code for America does not have a valid events url')

        from app import Event

        # Make sure no events exist
        events_count = self.db.session.query(Event).count()
        self.assertEqual(events_count, 0)

    def test_main_with_non_existant_meetup(self):
        ''' When meetup returns a 404 for an organization's events url, an error
            message should be logged
        '''
        def response_content(url, request):
            import run_update

            if url.geturl() == 'http://example.com/cfa-projects.csv':
                return response(200, '''name,description,link_url,code_url,type,categories\n,,,https://github.com/codeforamerica/cityvoice,web service,"community engagement, housing"\nSouthBendVoices,,,https://github.com/codeforamerica/cityvoice,,''')

            elif url.geturl() == run_update.gdocs_url:
                return response(200, '''name,website,events_url,rss,projects_list_url\nCode for America,http://codeforamerica.org,http://www.meetup.com/events/Code-For-Charlotte,http://www.codeforamerica.org/blog/feed/,http://example.com/cfa-projects.csv''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice':
                return response(200, '''{ "id": 10515516, "name": "cityvoice", "full_name": "codeforamerica/cityvoice", "owner": { "login": "codeforamerica", "id": 337792, "avatar_url": "https://avatars.githubusercontent.com/u/337792", "gravatar_id": "ec81184c572bc827b72ebb489d49f821", "url": "https://api.github.com/users/codeforamerica", "html_url": "https://github.com/codeforamerica", "followers_url": "https://api.github.com/users/codeforamerica/followers", "following_url": "https://api.github.com/users/codeforamerica/following{/other_user}", "gists_url": "https://api.github.com/users/codeforamerica/gists{/gist_id}", "starred_url": "https://api.github.com/users/codeforamerica/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/codeforamerica/subscriptions", "organizations_url": "https://api.github.com/users/codeforamerica/orgs", "repos_url": "https://api.github.com/users/codeforamerica/repos", "events_url": "https://api.github.com/users/codeforamerica/events{/privacy}", "received_events_url": "https://api.github.com/users/codeforamerica/received_events", "type": "Organization", "site_admin": false }, "private": false, "html_url": "https://github.com/codeforamerica/cityvoice", "description": "A place-based call-in system for gathering and sharing community feedback", "fork": false, "url": "https://api.github.com/repos/codeforamerica/cityvoice", "forks_url": "https://api.github.com/repos/codeforamerica/cityvoice/forks", "keys_url": "https://api.github.com/repos/codeforamerica/cityvoice/keys{/key_id}", "collaborators_url": "https://api.github.com/repos/codeforamerica/cityvoice/collaborators{/collaborator}", "teams_url": "https://api.github.com/repos/codeforamerica/cityvoice/teams", "hooks_url": "https://api.github.com/repos/codeforamerica/cityvoice/hooks", "issue_events_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues/events{/number}", "events_url": "https://api.github.com/repos/codeforamerica/cityvoice/events", "assignees_url": "https://api.github.com/repos/codeforamerica/cityvoice/assignees{/user}", "branches_url": "https://api.github.com/repos/codeforamerica/cityvoice/branches{/branch}", "tags_url": "https://api.github.com/repos/codeforamerica/cityvoice/tags", "blobs_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/blobs{/sha}", "git_tags_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/tags{/sha}", "git_refs_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/refs{/sha}", "trees_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/trees{/sha}", "statuses_url": "https://api.github.com/repos/codeforamerica/cityvoice/statuses/{sha}", "languages_url": "https://api.github.com/repos/codeforamerica/cityvoice/languages", "stargazers_url": "https://api.github.com/repos/codeforamerica/cityvoice/stargazers", "contributors_url": "https://api.github.com/repos/codeforamerica/cityvoice/contributors", "subscribers_url": "https://api.github.com/repos/codeforamerica/cityvoice/subscribers", "subscription_url": "https://api.github.com/repos/codeforamerica/cityvoice/subscription", "commits_url": "https://api.github.com/repos/codeforamerica/cityvoice/commits{/sha}", "git_commits_url": "https://api.github.com/repos/codeforamerica/cityvoice/git/commits{/sha}", "comments_url": "https://api.github.com/repos/codeforamerica/cityvoice/comments{/number}", "issue_comment_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues/comments/{number}", "contents_url": "https://api.github.com/repos/codeforamerica/cityvoice/contents/{+path}", "compare_url": "https://api.github.com/repos/codeforamerica/cityvoice/compare/{base}...{head}", "merges_url": "https://api.github.com/repos/codeforamerica/cityvoice/merges", "archive_url": "https://api.github.com/repos/codeforamerica/cityvoice/{archive_format}{/ref}", "downloads_url": "https://api.github.com/repos/codeforamerica/cityvoice/downloads", "issues_url": "https://api.github.com/repos/codeforamerica/cityvoice/issues{/number}", "pulls_url": "https://api.github.com/repos/codeforamerica/cityvoice/pulls{/number}", "milestones_url": "https://api.github.com/repos/codeforamerica/cityvoice/milestones{/number}", "notifications_url": "https://api.github.com/repos/codeforamerica/cityvoice/notifications{?since,all,participating}", "labels_url": "https://api.github.com/repos/codeforamerica/cityvoice/labels{/name}", "releases_url": "https://api.github.com/repos/codeforamerica/cityvoice/releases{/id}", "created_at": "2013-06-06T00:12:30Z", "updated_at": "2014-02-21T20:43:16Z", "pushed_at": "2014-02-21T20:43:16Z", "git_url": "git://github.com/codeforamerica/cityvoice.git", "ssh_url": "git@github.com:codeforamerica/cityvoice.git", "clone_url": "https://github.com/codeforamerica/cityvoice.git", "svn_url": "https://github.com/codeforamerica/cityvoice", "homepage": "http://www.cityvoiceapp.com/", "size": 6290, "stargazers_count": 10, "watchers_count": 10, "language": "Ruby", "has_issues": true, "has_downloads": true, "has_wiki": true, "forks_count": 12, "mirror_url": null, "open_issues_count": 37, "forks": 12, "open_issues": 37, "watchers": 10, "default_branch": "master", "master_branch": "master", "organization": { "login": "codeforamerica", "id": 337792, "avatar_url": "https://avatars.githubusercontent.com/u/337792", "gravatar_id": "ec81184c572bc827b72ebb489d49f821", "url": "https://api.github.com/users/codeforamerica", "html_url": "https://github.com/codeforamerica", "followers_url": "https://api.github.com/users/codeforamerica/followers", "following_url": "https://api.github.com/users/codeforamerica/following{/other_user}", "gists_url": "https://api.github.com/users/codeforamerica/gists{/gist_id}", "starred_url": "https://api.github.com/users/codeforamerica/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/codeforamerica/subscriptions", "organizations_url": "https://api.github.com/users/codeforamerica/orgs", "repos_url": "https://api.github.com/users/codeforamerica/repos", "events_url": "https://api.github.com/users/codeforamerica/events{/privacy}", "received_events_url": "https://api.github.com/users/codeforamerica/received_events", "type": "Organization", "site_admin": false }, "network_count": 12, "subscribers_count": 42 }''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/contributors':
                return response(200, '''[ { "login": "daguar", "id": 994938, "avatar_url": "https://avatars.githubusercontent.com/u/994938", "gravatar_id": "bdd8cc46ae86e389388ae78dfc45effe", "url": "https://api.github.com/users/daguar", "html_url": "https://github.com/daguar", "followers_url": "https://api.github.com/users/daguar/followers", "following_url": "https://api.github.com/users/daguar/following{/other_user}", "gists_url": "https://api.github.com/users/daguar/gists{/gist_id}", "starred_url": "https://api.github.com/users/daguar/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/daguar/subscriptions", "organizations_url": "https://api.github.com/users/daguar/orgs", "repos_url": "https://api.github.com/users/daguar/repos", "events_url": "https://api.github.com/users/daguar/events{/privacy}", "received_events_url": "https://api.github.com/users/daguar/received_events", "type": "User", "site_admin": false, "contributions": 518 }, { "login": "rduecyg", "id": 1710759, "avatar_url": "https://avatars.githubusercontent.com/u/1710759", "gravatar_id": "ca617a981a0ba8423eb849843b21693c", "url": "https://api.github.com/users/rduecyg", "html_url": "https://github.com/rduecyg", "followers_url": "https://api.github.com/users/rduecyg/followers", "following_url": "https://api.github.com/users/rduecyg/following{/other_user}", "gists_url": "https://api.github.com/users/rduecyg/gists{/gist_id}", "starred_url": "https://api.github.com/users/rduecyg/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/rduecyg/subscriptions", "organizations_url": "https://api.github.com/users/rduecyg/orgs", "repos_url": "https://api.github.com/users/rduecyg/repos", "events_url": "https://api.github.com/users/rduecyg/events{/privacy}", "received_events_url": "https://api.github.com/users/rduecyg/received_events", "type": "User", "site_admin": false, "contributions": 159 }, { "login": "mholubowski", "id": 2035619, "avatar_url": "https://avatars.githubusercontent.com/u/2035619", "gravatar_id": "76743e4c14368f817ea4fff3c7e72b34", "url": "https://api.github.com/users/mholubowski", "html_url": "https://github.com/mholubowski", "followers_url": "https://api.github.com/users/mholubowski/followers", "following_url": "https://api.github.com/users/mholubowski/following{/other_user}", "gists_url": "https://api.github.com/users/mholubowski/gists{/gist_id}", "starred_url": "https://api.github.com/users/mholubowski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mholubowski/subscriptions", "organizations_url": "https://api.github.com/users/mholubowski/orgs", "repos_url": "https://api.github.com/users/mholubowski/repos", "events_url": "https://api.github.com/users/mholubowski/events{/privacy}", "received_events_url": "https://api.github.com/users/mholubowski/received_events", "type": "User", "site_admin": false, "contributions": 26 }, { "login": "mick", "id": 26278, "avatar_url": "https://avatars.githubusercontent.com/u/26278", "gravatar_id": "0a57f29a6d300554ed45c80b4e37ab49", "url": "https://api.github.com/users/mick", "html_url": "https://github.com/mick", "followers_url": "https://api.github.com/users/mick/followers", "following_url": "https://api.github.com/users/mick/following{/other_user}", "gists_url": "https://api.github.com/users/mick/gists{/gist_id}", "starred_url": "https://api.github.com/users/mick/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/mick/subscriptions", "organizations_url": "https://api.github.com/users/mick/orgs", "repos_url": "https://api.github.com/users/mick/repos", "events_url": "https://api.github.com/users/mick/events{/privacy}", "received_events_url": "https://api.github.com/users/mick/received_events", "type": "User", "site_admin": false, "contributions": 1 }, { "login": "migurski", "id": 58730, "avatar_url": "https://avatars.githubusercontent.com/u/58730", "gravatar_id": "039667155d1baa533e461671e97891a1", "url": "https://api.github.com/users/migurski", "html_url": "https://github.com/migurski", "followers_url": "https://api.github.com/users/migurski/followers", "following_url": "https://api.github.com/users/migurski/following{/other_user}", "gists_url": "https://api.github.com/users/migurski/gists{/gist_id}", "starred_url": "https://api.github.com/users/migurski/starred{/owner}{/repo}", "subscriptions_url": "https://api.github.com/users/migurski/subscriptions", "organizations_url": "https://api.github.com/users/migurski/orgs", "repos_url": "https://api.github.com/users/migurski/repos", "events_url": "https://api.github.com/users/migurski/events{/privacy}", "received_events_url": "https://api.github.com/users/migurski/received_events", "type": "User", "site_admin": false, "contributions": 1 } ]''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/stats/participation':
                return response(200, '''{ "all": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 23, 9, 4, 0, 77, 26, 7, 17, 53, 59, 37, 40, 0, 47, 59, 55, 118, 11, 8, 3, 3, 30, 0, 1, 1, 4, 6, 1, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1 ], "owner": [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ] }''')

            elif url.geturl() == 'https://api.github.com/repos/codeforamerica/cityvoice/issues?labels=project-needs':
                return response(200, '''[ ]''')

            elif url.geturl() == 'https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname=Code-For-Charlotte&sig_id=None':
                return response(404, '''Not Found!''')

            else:
                raise Exception('Asked for unknown URL ' + url.geturl())

        import logging

        logging.error = Mock()
        self.mock_rss_response()

        with HTTMock(response_content):
            import run_update
            run_update.main()

        logging.error.assert_called_with('Code for America\'s meetup page cannot be found')

if __name__ == '__main__':
    unittest.main()
