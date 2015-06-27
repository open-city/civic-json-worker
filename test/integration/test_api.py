# -*- coding: utf8 -*-

from urlparse import urlparse
from sqlalchemy.exc import IntegrityError
from factories import ProjectFactory, OrganizationFactory, EventFactory, StoryFactory, IssueFactory, LabelFactory
from test.base.integration_test import IntegrationTest
from app import db, Organization, Event, Story, Project, Issue, Label
import json

class TestApi(IntegrationTest):

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
