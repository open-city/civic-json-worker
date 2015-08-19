import json
from datetime import datetime, timedelta

from test.factories import OrganizationFactory, EventFactory
from test.harness import IntegrationTest
from app import db


class TestEvents(IntegrationTest):

    def test_all_upcoming_events(self):
        """
        Test the /events/upcoming_events end point.
        """
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
        assert isinstance(response['objects'][0]['rsvps'], int)

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


    def test_rsvp_routes(self):
        org = OrganizationFactory(name=u"Code for San Francisco")
        another_org = OrganizationFactory(type=u'Code for All')
        awesome_event = EventFactory(name=u'Awesome event')
        sad_event = EventFactory(name=u'Sad event', description=u'sad stuff will happen')

        awesome_event.organization = org
        sad_event.organization = another_org

        db.session.commit()

        # Make sure total number rsvps is 2468
        response = self.app.get('/api/events/rsvps')
        response = json.loads(response.data)
        self.assertEqual(response["total"], 2468)

        # Make sure org number rsvps is 1234
        response = self.app.get('/api/organizations/Code-for-San-Francisco/events/rsvps')
        response = json.loads(response.data)
        self.assertEqual(response["total"], 1234)


