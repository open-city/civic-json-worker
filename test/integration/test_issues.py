import json

from test.factories import OrganizationFactory, ProjectFactory, IssueFactory, LabelFactory
from test.harness import IntegrationTest
from app import db, Label


class TestIssues(IntegrationTest):

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
        issue = IssueFactory(project_id=project.id, title=u'TEST ISSUE', body=u'TEST ISSUE BODY', created_at="2013-06-06T00:12:30Z", updated_at="2014-02-21T20:43:16Z")
        db.session.add(issue)
        db.session.commit()

        response = self.app.get('/api/issues', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)

        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'TEST ISSUE')
        self.assertEqual(response['objects'][0]['body'], u'TEST ISSUE BODY')
        self.assertEqual(response['objects'][0]['created_at'], u'2013-06-06T00:12:30Z')
        self.assertEqual(response['objects'][0]['updated_at'], u'2014-02-21T20:43:16Z')

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
