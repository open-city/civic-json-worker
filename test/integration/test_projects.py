import json
from datetime import datetime, timedelta

from test.factories import ProjectFactory, OrganizationFactory, IssueFactory
from test.harness import IntegrationTest
from app import db, Issue


class TestProjects(IntegrationTest):

    def test_all_projects_order(self):
        """
        Test that projects gets returned in order of last_updated
        """
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
        assert isinstance(response['objects'][0]['tags'], unicode)
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
        assert isinstance(response['objects'][0]['languages'], list)

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


    def test_project_search_ranked_order(self):
        ''' Search results from the project and org/project endpoints are returned
            with correct ranking values
        '''
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, status='TEST', last_updated=datetime.now() - timedelta(10000))
        ProjectFactory(organization_name=organization.name, description='testing a new thing', last_updated=datetime.now() - timedelta(1))
        ProjectFactory(organization_name=organization.name, tags='test,tags,what,ever', last_updated=datetime.now() - timedelta(100))
        ProjectFactory(organization_name=organization.name, last_updated=datetime.now())
        db.session.commit()
        project_response = self.app.get('/api/projects?q=TEST')
        project_response = json.loads(project_response.data)
        self.assertEqual(project_response['total'], 3)
        self.assertEqual(project_response['objects'][0]['status'], 'TEST')
        self.assertEqual(project_response['objects'][1]['tags'], 'test,tags,what,ever')
        self.assertEqual(project_response['objects'][2]['description'], 'testing a new thing')


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


    def test_project_search_includes_tags(self):
        """
        The tags field is included in search results from the project and org/project endpoints
        """
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, tags=u'mapping, philly')
        ProjectFactory(organization_name=organization.name, tags=u'food stamps, health')
        db.session.commit()
        project_response = self.app.get('/api/projects?q=stamps')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 1)
        self.assertEqual(project_response['objects'][0]['tags'], 'food stamps, health')

        org_project_response = self.app.get('/api/organizations/Code-for-San-Francisco/projects?q=stamps')
        org_project_response = json.loads(org_project_response.data)
        self.assertEqual(len(org_project_response['objects']), 1)
        self.assertEqual(org_project_response['objects'][0]['tags'], 'food stamps, health')


    def test_project_search_includes_organization_name(self):
        """
        The organization name is included in the project search
        """
        organization = OrganizationFactory(name=u"Code for San Francisco")
        ProjectFactory(organization_name=organization.name, name="Project One")
        ProjectFactory(organization_name=organization.name, name="Project Two", description="America")

        organization = OrganizationFactory(name=u"Code for America")
        ProjectFactory(organization_name=organization.name, name="Project Three")
        ProjectFactory(organization_name=organization.name, name="Project Four", tags="San Francisco")
        db.session.commit()

        # Test that org_name matches return before project name
        project_response = self.app.get('/api/projects?q=Code+for+San+Francisco')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 3)
        self.assertEqual(project_response['objects'][0]['name'], 'Project One')
        self.assertEqual(project_response['objects'][1]['name'], 'Project Two')
        self.assertEqual(project_response['objects'][2]['name'], 'Project Four')
        self.assertTrue( 'San Francisco' in project_response['objects'][2]['tags'] )

        # Test that org name matches return before project description
        project_response = self.app.get('/api/projects?q=Code for America')
        project_response = json.loads(project_response.data)
        self.assertEqual(len(project_response['objects']), 3)
        self.assertEqual(project_response['objects'][0]['name'], 'Project Three')
        self.assertEqual(project_response['objects'][1]['name'], 'Project Four')
        self.assertEqual(project_response['objects'][2]['name'], 'Project Two')
        self.assertEqual(project_response['objects'][2]['description'], 'America')


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
