import json
from datetime import datetime, timedelta
import time

from test.factories import OrganizationFactory, ProjectFactory, EventFactory, StoryFactory, IssueFactory, LabelFactory
from test.harness import IntegrationTest
from app import db


class TestOrganizations(IntegrationTest):

    def test_current_projects(self):
        """
        Show three most recently updated github projects
        """
        organization = OrganizationFactory(name=u'Code for San Francisco')
        db.session.flush()

        ProjectFactory(organization_name=organization.name, name=u'Project 1', last_updated='Mon, 01 Jan 2010 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Project 2', last_updated='Tue, 01 Jan 2011 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Non Github Project', last_updated='Wed, 01 Jan 2013 00:00:00', github_details=None)
        ProjectFactory(organization_name=organization.name, name=u'Project 3', last_updated='Thu, 01 Jan 2014 00:00:00 GMT')
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-San-Francisco')
        response = json.loads(response.data)

        self.assertEqual(len(response['current_projects']), 3)
        self.assertEqual(response['current_projects'][0]['name'], u'Project 3')
        self.assertEqual(response['current_projects'][1]['name'], u'Non Github Project')
        self.assertEqual(response['current_projects'][2]['name'], u'Project 2')

    def test_orgs_projects_order(self):
        """
        Test that a orgs projects come back in order of last_updated.
        """
        organization = OrganizationFactory(name=u'Code for San Francisco')
        db.session.flush()

        ProjectFactory(organization_name=organization.name, name=u'Project 1', last_updated='Mon, 01 Jan 2010 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Project 2', last_updated='Tue, 01 Jan 2011 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Non Github Project', last_updated='Wed, 01 Jan 2013 00:00:00', github_details=None)
        ProjectFactory(organization_name=organization.name, name=u'Project 3', last_updated='Thu, 01 Jan 2014 00:00:00 GMT')
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-San-Francisco/projects')
        response = json.loads(response.data)

        self.assertEqual(response['objects'][0]['name'], u'Project 3')
        self.assertEqual(response['objects'][1]['name'], u'Non Github Project')
        self.assertEqual(response['objects'][2]['name'], u'Project 2')
        self.assertEqual(response['objects'][3]['name'], u'Project 1')

    def test_current_events(self):
        """
        The three soonest upcoming events should be returned.
        If there are no events in the future, no events will be returned
        """
        # Assuming today is Christmas...
        organization = OrganizationFactory(name=u'Collective of Ericas')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Christmas Eve', start_time_notz=datetime.now() - timedelta(1))
        EventFactory(organization_name=organization.name, name=u'New Years', start_time_notz=datetime.now() + timedelta(7))
        EventFactory(organization_name=organization.name, name=u'MLK Day', start_time_notz=datetime.now() + timedelta(25))
        EventFactory(organization_name=organization.name, name=u'Cesar Chavez Day', start_time_notz=datetime.now() + timedelta(37))
        db.session.commit()

        response = self.app.get('/api/organizations/Collective%20of%20Ericas')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['current_events']), 2)
        self.assertEqual(response_json['current_events'][0]['name'], u'New Years')
        self.assertEqual(response_json['current_events'][1]['name'], u'MLK Day')
        self.assertEqual(response_json['current_events'][0]['organization_name'], u'Collective of Ericas')

    def test_current_stories(self):
        """
        Test that only the two most recent stories are being returned
        """
        organization = OrganizationFactory(name=u'Collective of Ericas')
        db.session.flush()

        StoryFactory(organization_name=u'Collective of Ericas', title=u'First Story')
        StoryFactory(organization_name=u'Collective of Ericas', title=u'Second Story')
        db.session.commit()

        response = self.app.get('/api/organizations/Collective%20of%20Ericas')
        response_json = json.loads(response.data)
        self.assertEqual(response_json['current_stories'][0]['title'], u'Second Story')
        self.assertEqual(response_json['current_stories'][1]['title'], u'First Story')

    def test_headers(self):
        OrganizationFactory()
        db.session.commit()

        response = self.app.get('/api/organizations')
        assert response.headers['Access-Control-Allow-Origin'] == '*'
        assert response.headers['Content-Type'] == 'application/json'

    def test_brigade_name_request(self):
        OrganizationFactory(name=u'Code for San Francisco')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for San Francisco')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['city'], unicode)
        assert isinstance(response['current_events'], list)
        assert isinstance(response['latitude'], float)
        assert isinstance(response['longitude'], float)
        assert isinstance(response['name'], unicode)
        assert isinstance(response['current_projects'], list)
        assert isinstance(response['projects_list_url'], unicode)
        assert isinstance(response['rss'], unicode)
        assert isinstance(response['current_stories'], list)
        assert isinstance(response['type'], unicode)
        assert isinstance(response['website'], unicode)

    def test_organizations(self):
        OrganizationFactory()
        db.session.commit()

        response = self.app.get('/api/organizations')
        response = json.loads(response.data)

        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['api_url'], unicode)
        assert isinstance(response['objects'][0]['city'], unicode)
        assert isinstance(response['objects'][0]['current_events'], list)
        assert isinstance(response['objects'][0]['latitude'], float)
        assert isinstance(response['objects'][0]['longitude'], float)
        assert isinstance(response['objects'][0]['name'], unicode)
        assert isinstance(response['objects'][0]['current_projects'], list)
        assert isinstance(response['objects'][0]['projects_list_url'], unicode)
        assert isinstance(response['objects'][0]['rss'], unicode)
        assert isinstance(response['objects'][0]['current_stories'], list)
        assert isinstance(response['objects'][0]['type'], unicode)
        assert isinstance(response['objects'][0]['website'], unicode)
        assert isinstance(response['objects'][0]['last_updated'], int)
        assert isinstance(response['objects'][0]['started_on'], unicode)

    def test_org_projects_dont_include_tsv(self):
        OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=u"Code for San Francisco")
        db.session.commit()
        response = self.app.get('/api/organizations/Code-for-San-Francisco')
        response = json.loads(response.data)
        self.assertFalse('tsv_body' in response['current_projects'][0])

    def test_good_orgs_projects(self):
        organization = OrganizationFactory(name=u'Code for America')
        ProjectFactory(organization_name=organization.name)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/projects')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_bad_orgs_projects(self):
        ProjectFactory()
        db.session.commit()

        response = self.app.get('/api/organizations/Whatever/projects')
        self.assertEqual(response.status_code, 404)

    def test_orgs_stories(self):
        organization = OrganizationFactory(name=u'Code for America')
        StoryFactory(organization_name=organization.name)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/stories')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_orgs_current_stories_order(self):
        organization = OrganizationFactory(name=u'Code for America')
        StoryFactory(organization_name=organization.name)
        StoryFactory(organization_name=organization.name)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America')
        response = json.loads(response.data)
        assert response['current_stories'][0]['id'] == 2
        assert response['current_stories'][1]['id'] == 1

    def test_orgs_stories_order(self):
        organization = OrganizationFactory(name=u'Code for America')
        StoryFactory(organization_name=organization.name)
        StoryFactory(organization_name=organization.name)
        StoryFactory(organization_name=organization.name)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/stories')
        response = json.loads(response.data)
        assert response['objects'][0]['id'] == 3
        assert response['objects'][1]['id'] == 2
        assert response['objects'][2]['id'] == 1

    def test_org_search_nonexisting_text(self):
        OrganizationFactory(
            name=u'BetaNYC'
        )
        db.session.commit()
        response = self.app.get('/api/organizations?q=ruby')
        response = json.loads(response.data)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        self.assertEqual(response['total'], 0)
        self.assertEqual(len(response['objects']), 0)

    def test_org_search_existing_text(self):
        OrganizationFactory(
            name=u'BetaNYC'
        )
        db.session.commit()
        response = self.app.get('/api/organizations?q=BetaNYC')
        response = json.loads(response.data)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        self.assertEqual(response['total'], 1)
        self.assertEqual(len(response['objects']), 1)

    def test_org_search_existing_phrase(self):
        OrganizationFactory(
            name=u'Code for San Francisco',
        )
        db.session.commit()
        response = self.app.get('/api/organizations?q=Code for San Francisco')
        response = json.loads(response.data)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        self.assertEqual(response['total'], 1)
        self.assertEqual(len(response['objects']), 1)

    def test_org_search_existing_part_of_phrase(self):
        OrganizationFactory(
            name=u'Code for San Francisco',
        )
        db.session.commit()
        response = self.app.get('/api/organizations?q=Code for')
        response = json.loads(response.data)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        self.assertEqual(response['total'], 1)
        self.assertEqual(len(response['objects']), 1)

    def test_org_search_nonexisting_phrase(self):
        OrganizationFactory(
            name=u'BetaNYC'
        )
        db.session.commit()
        response = self.app.get('/api/organizations?q=joomla')
        response = json.loads(response.data)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        self.assertEqual(response['total'], 0)
        self.assertEqual(len(response['objects']), 0)

    def test_org_search_order_by_relevance(self):
        OrganizationFactory(
            name=u'Code for San Francisco',
            last_updated=time.time() - 10
        )
        OrganizationFactory(
            name=u'Code for Binghampton',
            last_updated=time.time() - 1
        )
        db.session.commit()
        response = self.app.get('/api/organizations?q=San Francisco')
        response = json.loads(response.data)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        self.assertEqual(response['objects'][0]['name'], 'Code for San Francisco')

    def test_orgs_events(self):
        organization = OrganizationFactory(name=u'Code for America')
        event = EventFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_org_upcoming_events(self):
        '''
        Only return events occurring in the future
        Make sure that they are ordered from most recent to
        furthest away in the future
        '''
        # Assuming today is Christmas...
        organization = OrganizationFactory(name=u'International Cat Association')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Christmas Eve', start_time_notz=datetime.now() - timedelta(1))
        EventFactory(organization_name=organization.name, name=u'New Years', start_time_notz=datetime.now() + timedelta(7))
        EventFactory(organization_name=organization.name, name=u'MLK Day', start_time_notz=datetime.now() + timedelta(25))
        db.session.commit()

        # Check that future events are returned in the correct order
        response = self.app.get('/api/organizations/International Cat Association/upcoming_events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'New Years')
        self.assertEqual(response['objects'][1]['name'], u'MLK Day')

    def test_organization_query_filter(self):
        '''
        Test that organization query params work as expected.
        '''
        OrganizationFactory(name=u'Brigade Organization', type=u'Brigade')
        OrganizationFactory(name=u'Bayamon Organization', type=u'Brigade', city=u'Bayamon, PR')
        OrganizationFactory(name=u'Meetup Organization', type=u'Meetup')

        db.session.commit()

        response = self.app.get('/api/organizations?type=Brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'Brigade Organization')
        self.assertEqual(response['objects'][1]['name'], u'Bayamon Organization')

        response = self.app.get('/api/organizations?type=Brigade&city=Bayamon,%20PR')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Bayamon Organization')

        response = self.app.get('/api/organizations?type=SomeType')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 0)

    def test_organization_issues(self):
        ''' Test getting all of an organization's issues
        '''
        organization = OrganizationFactory(name=u'Civic Project', type=u'Not a brigade')
        db.session.flush()

        project1 = ProjectFactory(organization_name=organization.name, name=u'Civic Project 1')
        project2 = ProjectFactory(organization_name=organization.name, name=u'Civic Project 2')
        db.session.flush()

        IssueFactory(project_id=project1.id, title=u'Civic Issue 1.1')
        IssueFactory(project_id=project1.id, title=u'Civic Issue 1.2')
        IssueFactory(project_id=project2.id, title=u'Civic Issue 2.1')
        db.session.commit()

        response = self.app.get('/api/organizations/{}/issues'.format(organization.name))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 3)

        self.assertTrue(u'Civic Issue 1.1' in [item['title'] for item in response['objects']])

    def test_issues_returned_randomly(self):
        ''' Issues are returned in random order by default
        '''
        org1 = OrganizationFactory(name=u'Civic Organization')
        org2 = OrganizationFactory(name=u'Institute of Institutions')
        db.session.flush()

        project1 = ProjectFactory(organization_name=org1.name, name=u'Civic Project 1')
        project2 = ProjectFactory(organization_name=org1.name, name=u'Civic Project 2')
        project3 = ProjectFactory(organization_name=org1.name, name=u'Civic Project 3')
        project4 = ProjectFactory(organization_name=org2.name, name=u'Civic Project A')
        project5 = ProjectFactory(organization_name=org2.name, name=u'Civic Project B')
        db.session.flush()

        IssueFactory(project_id=project1.id, title=u'Civic Issue 1.1')
        IssueFactory(project_id=project2.id, title=u'Civic Issue 2.1')
        IssueFactory(project_id=project3.id, title=u'Civic Issue 3.1')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.1')
        IssueFactory(project_id=project5.id, title=u'Civic Issue 5.1')
        IssueFactory(project_id=project3.id, title=u'Civic Issue 3.2')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.2')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.3')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.4')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.5')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.6')
        IssueFactory(project_id=project5.id, title=u'Civic Issue 5.2')
        IssueFactory(project_id=project1.id, title=u'Civic Issue 1.2')
        IssueFactory(project_id=project2.id, title=u'Civic Issue 2.2')
        IssueFactory(project_id=project3.id, title=u'Civic Issue 3.3')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.7')
        IssueFactory(project_id=project5.id, title=u'Civic Issue 5.3')
        IssueFactory(project_id=project3.id, title=u'Civic Issue 3.4')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.8')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.9')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.10')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.11')
        IssueFactory(project_id=project4.id, title=u'Civic Issue 4.12')
        IssueFactory(project_id=project5.id, title=u'Civic Issue 5.4')
        db.session.commit()

        # get all the issues twice and compare results
        response = self.app.get('/api/issues?per_page=24')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 24)
        ids_round_one = [item['id'] for item in response['objects']]

        response = self.app.get('/api/issues?per_page=24')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 24)
        ids_round_two = [item['id'] for item in response['objects']]

        self.assertTrue(ids_round_one != ids_round_two)

        # get project 4's issues twice and compare results
        response = self.app.get('/api/organizations/{}/issues?per_page=16'.format(project4.organization_name))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 16)
        ids_round_three = [item['id'] for item in response['objects']]

        response = self.app.get('/api/organizations/{}/issues?per_page=16'.format(project4.organization_name))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 16)
        ids_round_four = [item['id'] for item in response['objects']]

        self.assertTrue(ids_round_three != ids_round_four)

    def test_org_issues_filtered_by_label(self):
        ''' An organization's issues, filtered by label, are returned as expected.
        '''
        org1 = OrganizationFactory(name=u'Civic Organization')
        db.session.flush()

        project1 = ProjectFactory(organization_name=org1.name, name=u'Civic Project 1')
        db.session.flush()

        issue1 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.1')
        issue2 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.2')
        issue3 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.3')
        issue4 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.4')
        issue5 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.5')
        issue6 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.6')
        issue7 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.7')
        issue8 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.8')
        issue9 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.9')
        issue10 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.10')
        issue11 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.11')
        issue12 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.12')
        issue13 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.13')
        issue14 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.14')
        issue15 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.15')
        issue16 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.16')
        issue17 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.17')
        issue18 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.18')
        issue19 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.19')
        issue20 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.20')
        issue21 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.21')
        issue22 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.22')
        issue23 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.23')
        issue24 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.24')
        db.session.flush()

        label1 = LabelFactory(issue_id=issue1.id, name=u'bug')
        label2 = LabelFactory(issue_id=issue2.id, name=u'enhancement')
        label3 = LabelFactory(issue_id=issue3.id, name=u'bug')
        label4 = LabelFactory(issue_id=issue4.id, name=u'enhancement')
        label5 = LabelFactory(issue_id=issue5.id, name=u'bug')
        label6 = LabelFactory(issue_id=issue6.id, name=u'enhancement')
        label7 = LabelFactory(issue_id=issue7.id, name=u'bug')
        label8 = LabelFactory(issue_id=issue8.id, name=u'enhancement')
        label9 = LabelFactory(issue_id=issue9.id, name=u'bug')
        label10 = LabelFactory(issue_id=issue10.id, name=u'enhancement')
        label11 = LabelFactory(issue_id=issue11.id, name=u'bug')
        label12 = LabelFactory(issue_id=issue12.id, name=u'enhancement')
        label13 = LabelFactory(issue_id=issue13.id, name=u'bug')
        label14 = LabelFactory(issue_id=issue14.id, name=u'enhancement')
        label15 = LabelFactory(issue_id=issue15.id, name=u'bug')
        label16 = LabelFactory(issue_id=issue16.id, name=u'enhancement')
        label17 = LabelFactory(issue_id=issue17.id, name=u'bug')
        label18 = LabelFactory(issue_id=issue18.id, name=u'enhancement')
        label19 = LabelFactory(issue_id=issue19.id, name=u'bug')
        label20 = LabelFactory(issue_id=issue20.id, name=u'enhancement')
        label21 = LabelFactory(issue_id=issue21.id, name=u'bug')
        label22 = LabelFactory(issue_id=issue22.id, name=u'enhancement')
        label23 = LabelFactory(issue_id=issue23.id, name=u'bug')
        label24 = LabelFactory(issue_id=issue24.id, name=u'enhancement')
        db.session.commit()

        # get project 4's issues twice and compare results; there should
        # be results and they should be randomized
        response = self.app.get('/api/organizations/{}/issues/labels/{}?per_page=12'.format(org1.name, label1.name))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 12)
        ids_round_one = [item['id'] for item in response['objects']]
        self.assertTrue(label1.id in ids_round_one)
        self.assertTrue(label3.id in ids_round_one)
        self.assertTrue(label5.id in ids_round_one)
        self.assertTrue(label7.id in ids_round_one)
        self.assertTrue(label9.id in ids_round_one)
        self.assertTrue(label11.id in ids_round_one)
        self.assertTrue(label13.id in ids_round_one)
        self.assertTrue(label15.id in ids_round_one)
        self.assertTrue(label17.id in ids_round_one)
        self.assertTrue(label19.id in ids_round_one)
        self.assertTrue(label21.id in ids_round_one)
        self.assertTrue(label23.id in ids_round_one)

        response = self.app.get('/api/organizations/{}/issues/labels/{}?per_page=12'.format(org1.name, label1.name))
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 12)
        ids_round_two = [item['id'] for item in response['objects']]
        self.assertTrue(label1.id in ids_round_two)
        self.assertTrue(label3.id in ids_round_two)
        self.assertTrue(label5.id in ids_round_two)
        self.assertTrue(label7.id in ids_round_two)
        self.assertTrue(label9.id in ids_round_two)
        self.assertTrue(label11.id in ids_round_two)
        self.assertTrue(label13.id in ids_round_two)
        self.assertTrue(label15.id in ids_round_two)
        self.assertTrue(label17.id in ids_round_two)
        self.assertTrue(label19.id in ids_round_two)
        self.assertTrue(label21.id in ids_round_two)
        self.assertTrue(label23.id in ids_round_two)

        self.assertTrue(ids_round_one != ids_round_two)

    def test_org_dont_show_issues(self):
        ''' Test that calls to /organizations dont return project issues '''
        from test.factories import OrganizationFactory, ProjectFactory, IssueFactory
        organization = OrganizationFactory()
        db.session.flush()

        project = ProjectFactory(organization_name=organization.name)
        db.session.flush()

        issue = IssueFactory(project_id=project.id)
        db.session.commit()

        response = self.app.get('/api/organizations')
        response = json.loads(response.data)
        for org in response['objects']:
            if org['current_projects']:
                self.assertFalse('issues' in org['current_projects'][0])
                break
