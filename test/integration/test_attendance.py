import json

from test.factories import AttendanceFactory, OrganizationFactory
from test.harness import IntegrationTest
from app import db


class TestAttendance(IntegrationTest):

    def test_attendance(self):
        OrganizationFactory(name="Code for San Francisco")
        AttendanceFactory()
        db.session.commit()

        response = self.app.get('/api/attendance')
        response = json.loads(response.data)
        assert isinstance(response, dict)


    def test_orgs_attendance(self):
        OrganizationFactory(name="Code for San Francisco")
        AttendanceFactory()
        db.session.commit()

        response = self.app.get('/api/organizations/attendance')
        response = json.loads(response.data)
        assert isinstance(response, dict)


    def test_org_attendance(self):
        OrganizationFactory(name="Code for San Francisco")
        AttendanceFactory()
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-San-Francisco/attendance')
        response = json.loads(response.data)
        self.assertIsInstance(response, list, response)

