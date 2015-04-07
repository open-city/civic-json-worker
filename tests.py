#!/usr/bin/env python
# -*- coding: utf8 -*-

import unittest
import json
from datetime import datetime, timedelta
from urlparse import urlparse
import time

from sqlalchemy.exc import IntegrityError

from app import app, db, Organization, Project, Event, Story, Issue, Label
from factories import OrganizationFactory, ProjectFactory, EventFactory, StoryFactory, IssueFactory, LabelFactory


class ApiTest(unittest.TestCase):

    def setUp(self):
        # Set up the database settings
        # app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://postgres@localhost/civic_json_worker_test'
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres:///civic_json_worker_test'
        db.create_all()
        self.app = app.test_client()

    def tearDown(self):
        db.session.close()
        db.drop_all()

    # Test API -----------------------
    def test_current_projects(self):
        '''
        Show three most recently updated github projects
        '''
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

    def test_all_projects_order(self):
        '''
        Test that projects gets returned in order of last_updated
        '''
        ProjectFactory(name=u'Project 1', last_updated='Mon, 01 Jan 2010 00:00:00 GMT')
        ProjectFactory(name=u'Project 2', last_updated='Tue, 01 Jan 2011 00:00:00 GMT')
        ProjectFactory(name=u'Non Github Project', last_updated='Wed, 01 Jan 2013 00:00:00', github_details=None)
        ProjectFactory(name=u'Project 3', last_updated='Thu, 01 Jan 2014 00:00:00 GMT')
        db.session.commit()

        response = self.app.get('/api/projects')
        response = json.loads(response.data)

        self.assertEqual(response['objects'][0]['name'], u'Project 3')
        self.assertEqual(response['objects'][1]['name'], u'Non Github Project')
        self.assertEqual(response['objects'][2]['name'], u'Project 2')
        self.assertEqual(response['objects'][3]['name'], u'Project 1')

    def test_orgs_projects_order(self):
        ''' Test that a orgs projects come back in order of last_updated.
        '''
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
        '''
        The three soonest upcoming events should be returned.
        If there are no events in the future, no events will be returned
        '''
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

    def test_all_upcoming_events(self):
        '''
        Test the /events/upcoming_events end point.
        '''
        # World Cup teams
        organization = OrganizationFactory(name=u'USA USA USA')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(1000))
        EventFactory(organization_name=organization.name, name=u'Event One', start_time_notz=datetime.now() + timedelta(10))
        EventFactory(organization_name=organization.name, name=u'Event Four', start_time_notz=datetime.now() + timedelta(100))
        EventFactory(organization_name=organization.name, name=u'Event Seven', start_time_notz=datetime.now() + timedelta(1000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'Brazil')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(2000))
        EventFactory(organization_name=organization.name, name=u'Event Two', start_time_notz=datetime.now() + timedelta(20))
        EventFactory(organization_name=organization.name, name=u'Event Five', start_time_notz=datetime.now() + timedelta(200))
        EventFactory(organization_name=organization.name, name=u'Event Eight', start_time_notz=datetime.now() + timedelta(2000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'GER')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(3000))
        EventFactory(organization_name=organization.name, name=u'Event Three', start_time_notz=datetime.now() + timedelta(30))
        EventFactory(organization_name=organization.name, name=u'Event Six', start_time_notz=datetime.now() + timedelta(300))
        EventFactory(organization_name=organization.name, name=u'Event Nine', start_time_notz=datetime.now() + timedelta(3000))
        db.session.commit()

        response = self.app.get('/api/events/upcoming_events')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['objects']), 9)
        self.assertEqual(response_json['objects'][0]['name'], u'Event One')
        self.assertEqual(response_json['objects'][1]['name'], u'Event Two')
        self.assertEqual(response_json['objects'][8]['name'], u'Event Nine')

    def test_all_upcoming_events_with_params(self):
        '''
        Test the /events/upcoming_events end point with params.
        '''
        # World Cup teams
        organization = OrganizationFactory(name=u'USA USA USA', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(1000))
        EventFactory(organization_name=organization.name, name=u'Event One', start_time_notz=datetime.now() + timedelta(10))
        EventFactory(organization_name=organization.name, name=u'Event Four', start_time_notz=datetime.now() + timedelta(100))
        EventFactory(organization_name=organization.name, name=u'Event Seven', start_time_notz=datetime.now() + timedelta(1000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'Brazil')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(2000))
        EventFactory(organization_name=organization.name, name=u'Event Two', start_time_notz=datetime.now() + timedelta(20))
        EventFactory(organization_name=organization.name, name=u'Event Five', start_time_notz=datetime.now() + timedelta(200))
        EventFactory(organization_name=organization.name, name=u'Event Eight', start_time_notz=datetime.now() + timedelta(2000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'GER', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(3000))
        EventFactory(organization_name=organization.name, name=u'Event Three', start_time_notz=datetime.now() + timedelta(30))
        EventFactory(organization_name=organization.name, name=u'Event Six', start_time_notz=datetime.now() + timedelta(300))
        EventFactory(organization_name=organization.name, name=u'Event Nine', start_time_notz=datetime.now() + timedelta(3000))
        db.session.commit()

        response = self.app.get('/api/events/upcoming_events?organization_type=Code for All')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['objects']), 6)
        self.assertEqual(response_json['objects'][0]['name'], u'Event One')
        self.assertEqual(response_json['objects'][1]['name'], u'Event Three')
        self.assertEqual(response_json['objects'][5]['name'], u'Event Nine')

    def test_all_past_events(self):
        '''
        Test the /events/past_events end point.
        '''
        # World Cup teams
        organization = OrganizationFactory(name=u'USA USA USA', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(1000))
        EventFactory(organization_name=organization.name, name=u'Event One', start_time_notz=datetime.now() + timedelta(10))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'Brazil')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(2000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'GER', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(3000))
        EventFactory(organization_name=organization.name, name=u'Event Three', start_time_notz=datetime.now() + timedelta(30))
        db.session.commit()

        response = self.app.get('/api/events/past_events?organization_type=Code for All')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['objects']), 2)

    def test_current_stories(self):
        '''
        Test that only the two most recent stories are being returned
        '''
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

    def test_404(self):
        response = self.app.get('/blahblahblah')
        assert response.status_code == 404
        response = self.app.get('/api/blahblahblah')
        assert response.status_code == 404
        response = self.app.get('/api/organizations/123456789')
        assert response.status_code == 404
        response = self.app.get('/api/stories/123456789')
        assert response.status_code == 404
        response = self.app.get('/api/events/123456789')
        assert response.status_code == 404
        response = self.app.get('/api/issues/123456789')
        assert response.status_code == 404

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

    def test_projects(self):
        ProjectFactory()
        db.session.commit()

        response = self.app.get('/api/projects')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['categories'], unicode)
        assert isinstance(response['objects'][0]['code_url'], unicode)
        assert isinstance(response['objects'][0]['description'], unicode)
        assert isinstance(response['objects'][0]['github_details'], dict)
        assert isinstance(response['objects'][0]['id'], int)
        assert isinstance(response['objects'][0]['api_url'], unicode)
        assert isinstance(response['objects'][0]['link_url'], unicode)
        assert isinstance(response['objects'][0]['name'], unicode)
        assert isinstance(response['objects'][0]['organization'], dict)
        assert isinstance(response['objects'][0]['organization_name'], unicode)
        assert isinstance(response['objects'][0]['type'], unicode)
        assert isinstance(response['objects'][0]['status'], unicode)

    def test_project_search_nonexisting_text(self):
        ''' Searching for non-existing text in the project and org/project
            endpoints returns no results
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'Coder')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(project_response['total'], 0)
        self.assertEqual(len(project_response['objects']), 0)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(org_project_response['total'], 0)
        self.assertEqual(len(org_project_response['objects']), 0)

    def test_project_search_existing_text(self):
        ''' Searching for existing text in the project and org/project endpoints
            returns expected results
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby')
        ProjectFactory(organization_name=organization.name, description=u'python')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(project_response['total'], 1)
        self.assertEqual(len(project_response['objects']), 1)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(org_project_response['total'], 1)
        self.assertEqual(len(org_project_response['objects']), 1)

    def test_project_search_existing_phrase(self):
        ''' Searching for an existing phrase in the project and org/project endpoints
            returns expected results
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby on rails')
        ProjectFactory(organization_name=organization.name, description=u'i love lamp')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby on rails')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(project_response['total'], 1)
        self.assertEqual(len(project_response['objects']), 1)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby on rails')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(org_project_response['total'], 1)
        self.assertEqual(len(org_project_response['objects']), 1)

    def test_project_search_existing_part_of_phrase(self):
        ''' Searching for a partial phrase in the project and org/project endpoints
            returns expected results
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby on rails')
        ProjectFactory(organization_name=organization.name, description=u'i love lamp')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(project_response['total'], 1)
        self.assertEqual(len(project_response['objects']), 1)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(org_project_response['total'], 1)
        self.assertEqual(len(org_project_response['objects']), 1)

    def test_project_search_nonexisting_phrase(self):
        ''' Searching for a term that is not part of an existing phrase in the project and
            org/project endpoints returns no results
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby on rails')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=joomla')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(project_response['total'], 0)
        self.assertEqual(len(project_response['objects']), 0)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=joomla')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(org_project_response['total'], 0)
        self.assertEqual(len(org_project_response['objects']), 0)

    def test_project_search_order_by_relevance(self):
        ''' Search results from the project and org/project endpoints are returned
            in order of relevance
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(len(project_response["objects"]), 2)
        self.assertEqual(project_response['objects'][0]['description'], 'ruby ruby ruby ruby ruby')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(len(org_project_response["objects"]), 2)
        self.assertEqual(org_project_response['objects'][0]['description'], 'ruby ruby ruby ruby ruby')

    def test_project_search_order_by_relevance_requested(self):
        ''' Search results from the project and org/project endpoints are returned
            in order of relevance when explicitly requested
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby&sort_by=relevance')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(len(project_response["objects"]), 2)
        self.assertEqual(project_response['objects'][0]['description'], 'ruby ruby ruby ruby ruby')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby&sort_by=relevance')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(len(org_project_response["objects"]), 2)
        self.assertEqual(org_project_response['objects'][0]['description'], 'ruby ruby ruby ruby ruby')

    def test_project_search_order_by_last_updated(self):
        ''' Search results from the project and org/project endpoints are returned
            in order of last_updated, if requested
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby&sort_by=last_updated')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(len(project_response["objects"]), 2)
        self.assertEqual(project_response['objects'][0]['description'], 'ruby')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby&sort_by=last_updated')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(len(org_project_response["objects"]), 2)
        self.assertEqual(org_project_response['objects'][0]['description'], 'ruby')

    def test_project_search_order_by_last_updated_sort_desc(self):
        ''' Search results from the project and org/project endpoints are returned
            in descending order of last_updated, if requested
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby&sort_by=last_updated&sort_dir=desc')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(len(project_response["objects"]), 2)
        self.assertEqual(project_response['objects'][0]['description'], 'ruby')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby&sort_by=last_updated&sort_dir=desc')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(len(org_project_response["objects"]), 2)
        self.assertEqual(org_project_response['objects'][0]['description'], 'ruby')

    def test_project_search_order_by_last_updated_sort_asc(self):
        ''' Search results from the project and org/project endpoints are returned
            in ascending order of last_updated, if requested
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=ruby&sort_by=last_updated&sort_dir=asc')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(len(project_response["objects"]), 2)
        self.assertEqual(project_response['objects'][0]['description'], 'ruby ruby ruby ruby ruby')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby&sort_by=last_updated&sort_dir=asc')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(len(org_project_response["objects"]), 2)
        self.assertEqual(org_project_response['objects'][0]['description'], 'ruby ruby ruby ruby ruby')

    def test_project_return_only_ids(self):
        ''' Search results from the project and org/project endpoints are returned
            as only IDs if requested
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        project_one = ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        project_two = ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_one_id = project_one.id
        project_two_id = project_two.id

        project_response = self.app.get('/api/projects?q=ruby&only_ids=true')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(len(project_response["objects"]), 2)
        assert isinstance(project_response['objects'][0], int)
        assert isinstance(project_response['objects'][1], int)
        self.assertEqual(project_response['objects'][0], project_one_id)
        self.assertEqual(project_response['objects'][1], project_two_id)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=ruby&only_ids=true')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(len(org_project_response["objects"]), 2)
        assert isinstance(org_project_response['objects'][0], int)
        assert isinstance(org_project_response['objects'][1], int)
        self.assertEqual(org_project_response['objects'][0], project_one_id)
        self.assertEqual(org_project_response['objects'][1], project_two_id)

    def test_project_search_empty_string(self):
        ''' Searching an empty string on the project and org/project endpoints returns all projects
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=')
        project_response = json.loads(project_response.data)
        assert isinstance(project_response['total'], int)
        assert isinstance(project_response['objects'], list)
        self.assertEqual(project_response['total'], 2)
        self.assertEqual(len(project_response['objects']), 2)

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=')
        org_project_response = json.loads(org_project_response.data)
        assert isinstance(org_project_response['total'], int)
        assert isinstance(org_project_response['objects'], list)
        self.assertEqual(org_project_response['total'], 2)
        self.assertEqual(len(org_project_response['objects']), 2)

    def test_project_search_tsv_body_not_in_response(self):
        ''' The tsv_body field is not in the response from the project and org/project endpoints
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, description=u'ruby ruby ruby ruby ruby', last_updated=datetime.now() - timedelta(10))
        ProjectFactory(organization_name=organization.name, description=u'ruby', last_updated=datetime.now() - timedelta(1))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 2)
        self.assertFalse('tsv_body' in project_response['objects'][0])
        self.assertFalse('tsv_body' in project_response['objects'][1])

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=')
        org_project_response = json.loads(org_project_response.data)
        self.assertEqual(len(org_project_response['objects']), 2)
        self.assertFalse('tsv_body' in org_project_response['objects'][0])
        self.assertFalse('tsv_body' in org_project_response['objects'][1])

    def test_org_projects_dont_include_tsv(self):
        OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=u"Code for San Francisco")
        db.session.commit()
        response = self.app.get('/api/organizations/Code-for-San-Francisco')
        response = json.loads(response.data)
        self.assertFalse('tsv_body' in response['current_projects'][0])

    def test_project_orgs_dont_include_tsv(self):
        OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=u"Code for San Francisco")
        db.session.commit()
        response = self.app.get('/api/projects')
        response = json.loads(response.data)
        self.assertFalse('tsv_body' in response['objects'][0]['organization'])

    def test_project_search_includes_status(self):
        ''' The status field is included in search results from the project and org/project endpoints
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, status=u'Beta')
        ProjectFactory(organization_name=organization.name, status=u'Alpha')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=alpha')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 1)
        self.assertEqual(project_response['objects'][0]['status'], 'Alpha')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=alpha')
        org_project_response = json.loads(org_project_response.data)
        self.assertEqual(len(org_project_response['objects']), 1)
        self.assertEqual(org_project_response['objects'][0]['status'], 'Alpha')

    def test_project_search_includes_name(self):
        ''' The name field is included in search results from the project and org/project endpoints
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, name=u'My Cool Project')
        ProjectFactory(organization_name=organization.name, name=u'My Dumb Project')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=cool')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 1)
        self.assertEqual(project_response['objects'][0]['name'], 'My Cool Project')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=cool')
        org_project_response = json.loads(org_project_response.data)
        self.assertEqual(len(org_project_response['objects']), 1)
        self.assertEqual(org_project_response['objects'][0]['name'], 'My Cool Project')

    def test_project_search_includes_categories(self):
        ''' The categories field is included in search results from the project and org/project endpoints
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, categories=u'project management, civic hacking')
        ProjectFactory(organization_name=organization.name, categories=u'animal control, twitter')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=control')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 1)
        self.assertEqual(project_response['objects'][0]['categories'], 'animal control, twitter')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=control')
        org_project_response = json.loads(org_project_response.data)
        self.assertEqual(len(org_project_response['objects']), 1)
        self.assertEqual(org_project_response['objects'][0]['categories'], 'animal control, twitter')

    def test_project_search_includes_github_details(self):
        ''' The github_details field is included in search results from the project and org/project endpoints
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, github_details=json.dumps({'panic': 'disco'}))
        ProjectFactory(organization_name=organization.name, github_details=json.dumps({'button': 'red'}))
        db.session.commit()
        project_response = self.app.get('/api/projects?q=disco')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 1)
        self.assertEqual(project_response['objects'][0]['github_details'], '{"panic": "disco"}')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=disco')
        org_project_response = json.loads(org_project_response.data)
        self.assertEqual(len(org_project_response['objects']), 1)
        self.assertEqual(org_project_response['objects'][0]['github_details'], '{"panic": "disco"}')

    def test_pagination(self):
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()
        db.session.commit()

        response = self.app.get('/api/projects?per_page=2')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        self.assertEqual(len(response['objects']), 2)
        self.assertEqual(response['pages']['next'], 'http://localhost/api/projects?per_page=2&page=2')
        self.assertEqual(response['pages']['last'], 'http://localhost/api/projects?per_page=2&page=2')
        self.assertNotIn('first', response['pages'])
        self.assertNotIn('prev', response['pages'])

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

    def test_stories(self):
        StoryFactory()
        db.session.commit()

        response = self.app.get('/api/stories')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['id'], int)
        assert isinstance(response['objects'][0]['link'], unicode)
        assert isinstance(response['objects'][0]['organization'], dict)
        assert isinstance(response['objects'][0]['organization_name'], unicode)
        assert isinstance(response['objects'][0]['title'], unicode)
        assert isinstance(response['objects'][0]['type'], unicode)

    def test_stories_order(self):
        StoryFactory()
        StoryFactory()
        StoryFactory()
        db.session.commit()

        response = self.app.get('/api/stories')
        response = json.loads(response.data)
        assert (response['objects'][0]['id'] == 3)
        assert (response['objects'][1]['id'] == 2)
        assert (response['objects'][2]['id'] == 1)

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

    def test_events(self):
        '''
        Return all events past/future ordered by oldest to newest
        '''
        EventFactory()
        db.session.commit()

        response = self.app.get('/api/events')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['description'], unicode)
        assert isinstance(response['objects'][0]['end_time'], unicode)
        assert isinstance(response['objects'][0]['event_url'], unicode)
        assert isinstance(response['objects'][0]['api_url'], unicode)
        assert isinstance(response['objects'][0]['id'], int)
        assert isinstance(response['objects'][0]['location'], unicode)
        assert isinstance(response['objects'][0]['name'], unicode)
        assert isinstance(response['objects'][0]['organization'], dict)
        assert isinstance(response['objects'][0]['organization_name'], unicode)
        assert isinstance(response['objects'][0]['start_time'], unicode)

    def test_orgs_events(self):
        organization = OrganizationFactory(name=u'Code for America')
        event = EventFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_utf8_characters(self):
        organization = OrganizationFactory(name=u'Cöde for Ameriça')
        db.session.add(organization)
        db.session.commit()

        response = self.app.get(u'/api/organizations/Cöde for Ameriça')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

        response = self.app.get(u'/api/organizations/Cöde-for-Ameriça')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

        response = self.app.get('/api/organizations/C%C3%B6de for Ameri%C3%A7a')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

        response = self.app.get('/api/organizations/C%C3%B6de-for-Ameri%C3%A7a')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

    def test_underscores_and_spaces(self):
        organization = OrganizationFactory(name=u'Code for America')
        db.session.add(organization)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        scheme, netloc, path, _, _, _ = urlparse(response['all_events'])
        self.assertTrue('-' in path)
        self.assertFalse('_' in path)
        self.assertFalse(' ' in path)
        scheme, netloc, path, _, _, _ = urlparse(response['all_stories'])
        self.assertTrue('-' in path)
        self.assertFalse('_' in path)
        self.assertFalse(' ' in path)
        scheme, netloc, path, _, _, _ = urlparse(response['all_projects'])
        self.assertTrue('-' in path)
        self.assertFalse('_' in path)
        self.assertFalse(' ' in path)

        response = self.app.get('/api/organizations/Code-for-America')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['name'], u'Code for America')

        project = ProjectFactory(organization_name=u'Code for America')
        db.session.add(project)
        db.session.commit()

        response = self.app.get('/api/organizations/Code_for_America/projects')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America/projects')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        event = EventFactory(organization_name=u'Code for America')
        db.session.add(event)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America/events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        story = StoryFactory(organization_name=u'Code for America')
        db.session.add(story)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/stories')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America/stories')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

    def test_dashes_in_slugs(self):
        organization = OrganizationFactory(name=u'Code for America')
        event = EventFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-America')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['name'], u'Code for America')

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

    def test_past_events(self):
        '''
        Only return events that occurred in the past
        Make sure they are ordered from most recent to
        furthest in the past
        '''
        # Assuming today is Christmas...
        organization = OrganizationFactory(name=u'International Cat Association')
        db.session.flush()

        # Create multiple events, one in the future, some in the past
        EventFactory(organization_name=organization.name, name=u'Thanksgiving', start_time_notz=datetime.now() - timedelta(30))
        EventFactory(organization_name=organization.name, name=u'Christmas Eve', start_time_notz=datetime.now() - timedelta(1))
        EventFactory(organization_name=organization.name, name=u'New Years', start_time_notz=datetime.now() + timedelta(7))
        db.session.commit()

        # Check that past events are returned in the correct order
        response = self.app.get('/api/organizations/International Cat Association/past_events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'Christmas Eve')
        self.assertEqual(response['objects'][1]['name'], u'Thanksgiving')

    def test_issues(self):
        '''
        Test that issues have everything we expect.
        Make sure linked issues are not included in the linked project
        '''
        organization = OrganizationFactory()
        db.session.add(organization)
        db.session.commit()
        project = ProjectFactory(organization_name=organization.name)
        db.session.add(project)
        db.session.commit()
        issue = IssueFactory(project_id=project.id, title=u'TEST ISSUE', body=u'TEST ISSUE BODY')
        db.session.add(issue)
        db.session.commit()

        response = self.app.get('/api/issues', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)

        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'TEST ISSUE')
        self.assertEqual(response['objects'][0]['body'], u'TEST ISSUE BODY')

        # Check for linked issues in linked project
        self.assertTrue('project' in response['objects'][0])
        self.assertFalse('issues' in response['objects'][0])

        # Check that project_id is hidden
        self.assertTrue('project_id' not in response['objects'][0])

        # Check for linked project issues on single issue
        response = self.app.get('/api/issues/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertTrue('project' in response)
        self.assertTrue('issues' not in response['project'])

    def test_issues_with_labels(self):
        '''
        Test that /api/issues/labels works as expected.
        Should return issues with any of the passed in label names
        '''
        project = ProjectFactory()
        db.session.flush()

        issue = IssueFactory(project_id=project.id)
        issue2 = IssueFactory(project_id=project.id)

        label1 = LabelFactory(name=u'enhancement')
        label2 = LabelFactory(name=u'hack')
        issue.labels = [label1]
        issue2.labels = [label2]

        db.session.commit()

        response = self.app.get('/api/issues/labels/enhancement')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['labels'][0]['name'], u'enhancement')

        response = self.app.get('/api/issues/labels/enhancement,hack')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 0)

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

    def test_project_query_filter(self):
        '''
        Test that project query params work as expected.
        '''
        brigade = OrganizationFactory(name=u'Whatever', type=u'Brigade')
        brigade_somewhere_far = OrganizationFactory(name=u'Brigade Organization', type=u'Brigade, Code for All')
        web_project = ProjectFactory(name=u'Random Web App', type=u'web service')
        other_web_project = ProjectFactory(name=u'Random Web App 2', type=u'web service', description=u'Another')
        non_web_project = ProjectFactory(name=u'Random Other App', type=u'other service')

        web_project.organization = brigade
        non_web_project.organization = brigade_somewhere_far

        db.session.add(web_project)
        db.session.add(non_web_project)
        db.session.commit()

        response = self.app.get('/api/projects?type=web%20service')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'Random Web App')
        self.assertEqual(response['objects'][1]['name'], u'Random Web App 2')

        response = self.app.get('/api/projects?type=web%20service&description=Another')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Random Web App 2')

        response = self.app.get('/api/projects?type=different%20service')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 0)

        response = self.app.get('/api/projects?organization_type=Code+for+All')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)

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

    def test_cascading_delete(self):
        '''
        Test that when an organization is deleted, all of its projects, issues, stories, events are deleted
        '''
        # Create an organization
        organization = OrganizationFactory()
        db.session.flush()

        # Create a project, an event and a story
        project = ProjectFactory(organization_name=organization.name)
        EventFactory(organization_name=organization.name)
        StoryFactory(organization_name=organization.name)
        db.session.flush()

        # Create an issue and give it a label
        issue = IssueFactory(project_id=project.id)
        db.session.flush()

        label = LabelFactory()
        issue.labels = [label]
        db.session.flush()

        # Get all of the stuff
        orgs = Organization.query.all()
        eve = Event.query.all()
        sto = Story.query.all()
        proj = Project.query.all()
        iss = Issue.query.all()
        lab = Label.query.all()

        # Verify they are there
        self.assertEqual(len(orgs), 1)
        self.assertEqual(len(eve), 1)
        self.assertEqual(len(sto), 1)
        self.assertEqual(len(proj), 1)
        self.assertEqual(len(iss), 1)
        self.assertEqual(len(lab), 1)

        # Delete the one organization
        db.session.delete(orgs[0])
        db.session.commit()

        # Get all the stuff again
        orgs = Organization.query.all()
        eve = Event.query.all()
        sto = Story.query.all()
        proj = Project.query.all()
        iss = Issue.query.all()
        lab = Label.query.all()

        # Make sure they are all gone
        self.assertEqual(len(orgs), 0)
        self.assertEqual(len(eve), 0)
        self.assertEqual(len(sto), 0)
        self.assertEqual(len(proj), 0)
        self.assertEqual(len(iss), 0)
        self.assertEqual(len(lab), 0)

    def test_story_query_filter(self):
        org = OrganizationFactory(type=u'Brigade')
        another_org = OrganizationFactory(type=u'Code for All')

        awesome_story = StoryFactory(title=u'Awesome story')
        sad_story = StoryFactory(title=u'Sad story', type=u'a video')

        awesome_story.organization = org
        sad_story.organization = another_org

        db.session.commit()

        # Make sure total number of stories is 2
        response = self.app.get('/api/stories')
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)

        # Filter by title should return only 1
        response = self.app.get('/api/stories?title=awesome')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome story')

        # Filter by type should return only 1
        response = self.app.get('/api/stories?type=video')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Sad story')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/stories?organization_type=brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome story')

    def test_events_query_filter(self):
        org = OrganizationFactory(type=u'Brigade')
        another_org = OrganizationFactory(type=u'Code for All')
        awesome_event = EventFactory(name=u'Awesome event')
        sad_event = EventFactory(name=u'Sad event', description=u'sad stuff will happen')

        awesome_event.organization = org
        sad_event.organization = another_org

        db.session.commit()

        # Make sure total number of stories is 2
        response = self.app.get('/api/events')
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)

        # Filter by name should return only 1
        response = self.app.get('/api/events?name=awesome')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Awesome event')

        # Filter by description should return only 1
        response = self.app.get('/api/events?description=sad%20stuff')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Sad event')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/events?organization_type=brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Awesome event')

    def test_issues_query_filter(self):
        org1 = OrganizationFactory(name=u'Code for Africa', type=u'Code for All')
        org2 = OrganizationFactory(name=u'Code for San Francisco', type=u'Brigade')
        proj = ProjectFactory(type=u'web', organization_name=u'Code for Africa')
        another_proj = ProjectFactory(type=u'mobile', organization_name=u'Code for San Francisco')
        db.session.flush()
        awesome_issue = IssueFactory(title=u'Awesome issue', project_id=proj.id)
        sad_issue = IssueFactory(title=u'Sad issue', body=u'learning swift is sad', project_id=another_proj.id)
        db.session.commit()

        # Make sure total number of stories is 2
        response = self.app.get('/api/issues')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)

        # Filter by title should return only 1
        response = self.app.get('/api/issues?title=awesome')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome issue')

        # Filter by type should return only 1
        response = self.app.get('/api/issues?body=swift')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Sad issue')

        # Filter by deep searching project type should return 1
        response = self.app.get('/api/issues?project_type=web')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome issue')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/issues?organization_type=Code for All')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome issue')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/issues?organization_type=Brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Sad issue')

    def test_org_dont_show_issues(self):
        ''' Test that calls to /organizations dont return project issues '''
        from factories import OrganizationFactory, ProjectFactory, IssueFactory
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

    def test_issue_cascading_deletes(self):
        ''' Test that labels get deleted when their parent
            issue, project, and org is deleted
        '''

        # set up test objects and delete an issue
        organization = OrganizationFactory(name=u'TEST ORG')
        db.session.flush()

        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        db.session.flush()

        label = LabelFactory(issue_id=issue.id)
        db.session.flush()

        db.session.execute('DELETE FROM issue')
        db.session.commit()
        labels = db.session.query(Label).all()
        self.assertFalse(len(labels))

        # delete a project
        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        db.session.flush()

        label = LabelFactory(issue_id=issue.id)
        db.session.flush()

        db.session.execute('DELETE FROM project')
        db.session.commit()
        labels = db.session.query(Label).all()
        self.assertFalse(len(labels))

        # delete an organization
        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        db.session.flush()

        label = LabelFactory(issue_id=issue.id)
        db.session.flush()

        db.session.execute('DELETE FROM organization')
        db.session.commit()
        labels = db.session.query(Label).all()
        self.assertFalse(len(labels))

    def test_project_cascading_deletes(self):
        ''' Test that issues get deleted when their parent
            project and org is deleted
        '''

        # set up test objects and delete a project
        organization = OrganizationFactory(name=u'TEST ORG')
        db.session.flush()

        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        another_issue = IssueFactory(title=u'ANOTHER TEST ISSUE', project_id=project.id)
        a_third_issue = IssueFactory(title=u'A THIRD TEST ISSUE', project_id=project.id)
        db.session.commit()

        # make sure the issues are in the db
        issues = db.session.query(Issue).all()
        self.assertTrue(len(issues) == 3)

        db.session.execute('DELETE FROM project')
        db.session.commit()
        issues = db.session.query(Issue).all()
        self.assertFalse(len(issues))

        # delete an organization
        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        another_issue = IssueFactory(title=u'ANOTHER TEST ISSUE', project_id=project.id)
        a_third_issue = IssueFactory(title=u'A THIRD TEST ISSUE', project_id=project.id)
        db.session.commit()

        # make sure the issues are in the db
        issues = db.session.query(Issue).all()
        self.assertTrue(len(issues) == 3)

        db.session.execute('DELETE FROM organization')
        db.session.commit()
        issues = db.session.query(Issue).all()
        self.assertFalse(len(issues))

    def test_create_child_without_parent(self):
        ''' Test that children created without parents cannot be committed to the database
        '''
        test_passed = False
        project = ProjectFactory(organization_name=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        story = StoryFactory(organization_name=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        event = EventFactory(organization_name=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        issue = IssueFactory(project_id=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        label = LabelFactory(issue_id=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)

    def test_set_childs_parent_association_null(self):
        ''' Test that a child's parent association cannot be deleted
        '''

        test_passed = False
        project = ProjectFactory()
        db.session.commit()
        setattr(project, 'organization_name', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        story = StoryFactory()
        db.session.commit()
        setattr(story, 'organization_name', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        event = EventFactory()
        db.session.commit()
        setattr(event, 'organization_name', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        project = ProjectFactory()
        db.session.flush()
        issue = IssueFactory(project_id=project.id)
        db.session.commit()
        setattr(issue, 'project_id', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        project = ProjectFactory()
        db.session.flush()
        issue = IssueFactory(project_id=project.id)
        db.session.flush()
        label = LabelFactory(issue_id=issue.id)
        db.session.commit()
        setattr(label, 'issue_id', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)

    def test_spaces_in_issues_requests_list(self):
        ''' Test that spaces in the list of labels works
        '''
        # Set up an issue with labels
        # Try requesting it with spaces in the request
        # Assert that it returns
        organization = OrganizationFactory()
        db.session.commit()
        project = ProjectFactory(organization_name=organization.name)
        db.session.commit()
        issue = IssueFactory(project_id=project.id)
        db.session.commit()
        hw_label = LabelFactory(name=u'help wanted', issue_id=issue.id)
        bug_label = LabelFactory(name=u'bug', issue_id=issue.id)
        db.session.commit()

        # Test that help wanted works
        response = self.app.get('/api/issues/labels/help wanted')
        response = json.loads(response.data)
        self.assertEqual(len(response['objects']), 1)

        # Test that help wanted, bug works
        response = self.app.get('/api/issues/labels/help wanted, bug')
        response = json.loads(response.data)
        self.assertEqual(len(response['objects']), 1)

if __name__ == '__main__':
    unittest.main()
