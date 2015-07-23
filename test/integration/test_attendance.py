import json

from test.factories import AttendanceFactory, OrganizationFactory
from test.harness import IntegrationTest
from app import db, Attendance


class TestAttendance(IntegrationTest):

    def test_attendance(self):
        cfsf = OrganizationFactory(name="Code for San Francisco")
        url = "https://www.codeforamerica.org/api/organizations/Code-for-San-Francisco"
        cfsf_att = AttendanceFactory(organization_name="Code for San Francisco", organization_url=url)
        oakland = OrganizationFactory(name="Open Oakland")
        url = "https://www.codeforamerica.org/api/organizations/Open-Oakland"
        oakland_att = AttendanceFactory(organization_name="Open Oakland", organization_url=url)
        db.session.commit()

        response = self.app.get('/api/attendance')
        self.assertEquals(response.status_code, 200)
        response = json.loads(response.data)
        self.assertIsInstance(response, dict)
        self.assertTrue("total" in response.keys())
        self.assertTrue("weekly" in response.keys())

        # Check amounts
        attendance = Attendance.query.all()
        total = 0
        weekly = {}
        for att in attendance:
            total += att.total
            for week in att.weekly.keys():
                if week in weekly.keys():
                    weekly[week] += att.weekly[week]
                else:
                    weekly[week] = att.weekly[week]
        self.assertEqual(response["total"],total)
        self.assertEqual(response["weekly"],weekly)


    def test_orgs_attendance(self):
        OrganizationFactory(name="Code for San Francisco")
        url = "https://www.codeforamerica.org/api/organizations/Code-for-San-Francisco"
        AttendanceFactory(organization_name="Code for San Francisco", organization_url=url)
        OrganizationFactory(name="Open Oakland")
        url = "https://www.codeforamerica.org/api/organizations/Open-Oakland"
        AttendanceFactory(organization_name="Open Oakland", organization_url=url)
        db.session.commit()

        response = self.app.get('/api/organizations/attendance')
        self.assertEquals(response.status_code, 200)
        response = json.loads(response.data)
        self.assertIsInstance(response, list)
        self.assertTrue("organization_name" in response[0].keys())
        self.assertTrue("cfapi_url" in response[0].keys())
        self.assertTrue("total" in response[0].keys())
        self.assertTrue("weekly" in response[0].keys())


    def test_org_attendance(self):
        OrganizationFactory(name="Code for San Francisco")
        url = "https://www.codeforamerica.org/api/organizations/Code-for-San-Francisco"
        AttendanceFactory(organization_name="Code for San Francisco", organization_url=url)
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-San-Francisco/attendance')
        self.assertEquals(response.status_code, 200)
        response = json.loads(response.data)
        self.assertIsInstance(response, dict)
        self.assertTrue("organization_name" in response.keys())
        self.assertTrue("cfapi_url" in response.keys())
        self.assertTrue("total" in response.keys())
        self.assertTrue("weekly" in response.keys())

