from factories import ProjectFactory, StoryFactory, OrganizationFactory
from test.base.integration_test import IntegrationTest
from app import db
import json

class TestStories(IntegrationTest):

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
