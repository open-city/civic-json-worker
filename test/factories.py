# -*- coding: utf8 -*-

from random import choice, randint
from datetime import datetime, timedelta

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app import Organization, Project, Event, Story, db, Issue, Label, Attendance


class OrganizationFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Organization
    FACTORY_SESSION = db.session

    name = factory.Sequence(lambda n: u'Civiç Örganizatioñ {0}'.format(n))
    website = factory.Sequence(lambda n: u'http://www.civicorganization{0}.com'.format(n))
    events_url = factory.Sequence(lambda n: u'http://www.meetup.com.com/events/civicproject{0}'.format(n))
    rss = factory.Sequence(lambda n: u'http://www.civicorganization{0}.rss'.format(n))
    projects_list_url = factory.Sequence(lambda n: u'http://www.civicorganization{0}.com/projects.csv'.format(n))
    city = u'San Francisco, CA'
    latitude = 37.7749
    longitude = -122.4194
    type = u'Brigade'

class ProjectFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Project
    FACTORY_SESSION = db.session

    name = u'Civic Project'
    code_url = u'http://www.github.com/civic-project'
    link_url = u'http://www.civicproject.com'
    description = u'This is a description'
    type = factory.LazyAttribute(lambda n: choice([u'web service', u'api', u'data standard']))
    categories = factory.LazyAttribute(lambda n: choice([u'housing', u'community engagement', u'criminal justice', u'education']))
    tags = ['what','ever']
    github_details = {'repo': u'git@github.com:codeforamerica/civic-project.git'}
    organization_name = factory.LazyAttribute(lambda e: OrganizationFactory().name)
    status = u'Project status'
    languages = ['Python','CSS']

class EventFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Event
    FACTORY_SESSION = db.session
    FACTORY_HIDDEN_ARGS = ('now',)

    name = factory.Sequence(lambda n: u'Civic Event {0}'.format(n))
    description = u'A civic event'
    event_url = factory.Sequence(lambda n: u'http://www.meetup.com/civic-project-hack-night{0}'.format(n))
    location = u'155 9th St., San Francisco, CA'

    now = factory.LazyAttribute(lambda o: datetime.utcnow())
    start_time_notz = factory.LazyAttribute(lambda o: o.now - timedelta(hours=10))
    end_time_notz = factory.LazyAttribute(lambda o: o.now - timedelta(hours=12))
    utc_offset = -28800
    created_at = factory.LazyAttribute(lambda o: o.now)
    organization_name = factory.LazyAttribute(lambda e: OrganizationFactory().name)

    rsvps = 1234

class StoryFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Story
    FACTORY_SESSION = db.session

    title = factory.Sequence(lambda n: u'Civic Story {0}'.format(n))
    link = u'http://www.codeforamerica.org/blog/2014/03/19/thanks-again-for-your-support-esri/'
    type = u'blog'
    organization_name = factory.LazyAttribute(lambda e: OrganizationFactory().name)

class IssueFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Issue
    FACTORY_SESSION = db.session

    title = factory.Sequence(lambda n: u'Civic Issue {0}'.format(n))
    html_url = factory.Sequence(lambda n: u'http://www.github.com/codeforamerica/cfapi/issues/{0}'.format(n))
    body = factory.Sequence(lambda n: u'Civic Issue blah blah blah {0}'.format(n))
    created_at = factory.LazyAttribute(lambda o: datetime.utcnow())
    updated_at = factory.LazyAttribute(lambda o: datetime.utcnow())

    project_id = factory.LazyAttribute(lambda e: ProjectFactory().id)

class LabelFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Label
    FACTORY_SESSION = db.session

    name = factory.Sequence(lambda n: u'enhancement {0}'.format(n))
    url = factory.Sequence(lambda n: u'https://api.github.com/repos/codeforamerica/cfapi/labels/enhancement{0}'.format(n))
    color = factory.Sequence(lambda n: u'FFF {0}'.format(n))

class AttendanceFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Attendance
    FACTORY_SESSION = db.session

    organization_name = factory.LazyAttribute(lambda e: OrganizationFactory().name)
    organization_url = "https://www.codeforamerica.org/api/organizations/" + str(factory.LazyAttribute(lambda e: OrganizationFactory().name)).replace(" ","-")
    total = randint(1,1000)
    weekly = {
        "2014 01" : randint(1,50),
        "2014 02" : randint(1,50),
        "2015 01" : randint(1,50),
        "2015 02" : randint(1,50)
    }
