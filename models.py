from __future__ import division

from datetime import datetime, date
import json
import time

from flask import request
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import types, desc
from sqlalchemy.orm import backref
from sqlalchemy import event, DDL
from dateutil.tz import tzoffset

from flask.ext.sqlalchemy import SQLAlchemy
from utils import raw_name, safe_name

db = SQLAlchemy()

# -------------------
# Initiation logic
# -------------------


def initialize_database(app):
    """ Takes an initalized flask application and binds a database context to allow query execution
    """
    # see https://github.com/mitsuhiko/flask-sqlalchemy/issues/82
    db.app = app
    db.init_app(app)

    return db

# -------------------
# Types
# -------------------


class JsonType(Mutable, types.TypeDecorator):
    """ JSON wrapper type for TEXT database storage.

        References:
        http://stackoverflow.com/questions/4038314/sqlalchemy-json-as-blob-text
        http://docs.sqlalchemy.org/en/rel_0_9/orm/extensions/mutable.html
    """
    impl = types.Unicode

    def process_bind_param(self, value, engine):
        return unicode(json.dumps(value))

    def process_result_value(self, value, engine):
        if value:
            return json.loads(value)
        else:
            # default can also be a list
            return {}


class TSVectorType(types.TypeDecorator):
    ''' TSVECTOR wrapper type for database storage.

        References:
        http://stackoverflow.com/questions/13837111/tsvector-in-sqlalchemy
    '''
    impl = types.UnicodeText


@compiles(TSVectorType, 'postgresql')
def compile_tsvector(element, compiler, **kw):
    return 'tsvector'


# -------------------
# Models
# -------------------

class Organization(db.Model):
    '''
        Brigades and other civic tech organizations
    '''
    # Columns
    name = db.Column(db.Unicode(), primary_key=True)
    website = db.Column(db.Unicode())
    events_url = db.Column(db.Unicode())
    rss = db.Column(db.Unicode())
    projects_list_url = db.Column(db.Unicode())
    type = db.Column(db.Unicode())
    city = db.Column(db.Unicode())
    latitude = db.Column(db.Float())
    longitude = db.Column(db.Float())
    last_updated = db.Column(db.Integer())
    started_on = db.Column(db.Unicode())
    member_count = db.Column(db.Integer())
    keep = db.Column(db.Boolean())
    tsv_body = db.Column(TSVectorType())
    id = db.Column(db.Unicode())

    # Relationships
    # can contain events, stories, projects (these relationships are defined in the child objects)

    def __init__(self, name, website=None, events_url=None, members_count=None,
                 rss=None, projects_list_url=None, type=None, city=None, latitude=None, longitude=None, last_updated=time.time()):
        self.name = name
        self.website = website
        self.events_url = events_url
        self.rss = rss
        self.projects_list_url = projects_list_url
        self.type = type
        self.city = city
        self.latitude = latitude
        self.longitude = longitude
        self.keep = True
        self.last_updated = last_updated
        self.started_on = unicode(date.today())
        self.id = safe_name(raw_name(name))
        self.members_count = members_count

    def current_events(self):
        '''
            Return the two soonest upcoming events
        '''
        filter_old = Event.start_time_notz >= datetime.utcnow()
        current_events = Event.query.filter_by(organization_name=self.name)\
            .filter(filter_old).order_by(Event.start_time_notz.asc()).limit(2).all()
        current_events_json = [row.asdict() for row in current_events]
        return current_events_json

    def current_projects(self):
        '''
            Return the three most current projects
        '''
        current_projects = Project.query.filter_by(organization_name=self.name).order_by(desc(Project.last_updated)).limit(3)
        current_projects_json = [project.asdict(include_issues=False) for project in current_projects]

        return current_projects_json

    def current_stories(self):
        '''
            Return the two most current stories
        '''
        current_stories = Story.query.filter_by(organization_name=self.name).order_by(desc(Story.id)).limit(2).all()
        current_stories_json = [row.asdict() for row in current_stories]
        return current_stories_json

    def all_events(self):
        ''' API link to all an orgs events
        '''
        # Make a nice org name
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/events' % (request.scheme, request.host, organization_name)

    def upcoming_events(self):
        ''' API link to an orgs upcoming events
        '''
        # Make a nice org name
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/upcoming_events' % (request.scheme, request.host, organization_name)

    def past_events(self):
        ''' API link to an orgs past events
        '''
        # Make a nice org name
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/past_events' % (request.scheme, request.host, organization_name)

    def all_projects(self):
        ''' API link to all an orgs projects
        '''
        # Make a nice org name
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/projects' % (request.scheme, request.host, organization_name)

    def all_issues(self):
        '''API link to all an orgs issues
        '''
        # Make a nice org name
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/issues' % (request.scheme, request.host, organization_name)

    def all_stories(self):
        ''' API link to all an orgs stories
        '''
        # Make a nice org name
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/stories' % (request.scheme, request.host, organization_name)

    def all_attendance(self):
        ''' API link to orgs attendance '''
        organization_name = safe_name(self.name)
        return '%s://%s/api/organizations/%s/attendance' % (request.scheme, request.host, organization_name)

    def api_id(self):
        ''' Return organization name made safe for use in a URL.
        '''
        return safe_name(self.name)

    def api_url(self):
        ''' API link to itself
        '''
        return '%s://%s/api/organizations/%s' % (request.scheme, request.host, self.api_id())

    def asdict(self, include_extras=False):
        ''' Return Organization as a dictionary, with some properties tweaked.

            Optionally include linked projects, events, and stories.
        '''
        organization_dict = db.Model.asdict(self)

        # remove fields that don't need to be public
        del organization_dict['keep']
        del organization_dict['tsv_body']

        for key in ('all_events', 'all_projects', 'all_stories', 'all_issues',
                    'upcoming_events', 'past_events', 'api_url', 'all_attendance'):
            organization_dict[key] = getattr(self, key)()

        if include_extras:
            for key in ('current_events', 'current_projects', 'current_stories'):
                organization_dict[key] = getattr(self, key)()

        return organization_dict


tbl = Organization.__table__
# Index the tsvector column
db.Index('index_org_tsv_body', tbl.c.tsv_body, postgresql_using='gin')

# Trigger to populate the search index column
trig_ddl = DDL("""
    CREATE TRIGGER tsvupdate_orgs_trigger BEFORE INSERT OR UPDATE ON organization FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(tsv_body, 'pg_catalog.english', name);
""")
# Initialize the trigger after table is created
event.listen(tbl, 'after_create', trig_ddl.execute_if(dialect='postgresql'))


class Story(db.Model):
    '''
        Blog posts from a Brigade.
    '''
    # Columns
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.Unicode())
    link = db.Column(db.Unicode())
    type = db.Column(db.Unicode())
    keep = db.Column(db.Boolean())

    # Relationships
    # child
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("stories", cascade="save-update, delete"))
    organization_name = db.Column(db.Unicode(), db.ForeignKey('organization.name', ondelete='CASCADE'), nullable=False)

    def __init__(self, title=None, link=None, type=None, organization_name=None):
        self.title = title
        self.link = link
        self.type = type
        self.organization_name = organization_name
        self.keep = True

    def api_url(self):
        ''' API link to itself
        '''
        return '%s://%s/api/stories/%s' % (request.scheme, request.host, str(self.id))

    def asdict(self, include_organization=False):
        ''' Return Story as a dictionary, with some properties tweaked.

            Optionally include linked organization.
        '''
        story_dict = db.Model.asdict(self)

        # remove fields that don't need to be public
        del story_dict['keep']

        story_dict['api_url'] = self.api_url()

        if include_organization:
            story_dict['organization'] = self.organization.asdict()

        return story_dict


class Project(db.Model):
    '''
        Civic tech projects on GitHub
    '''
    # Columns
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode())
    code_url = db.Column(db.Unicode())
    link_url = db.Column(db.Unicode())
    description = db.Column(db.Unicode())
    type = db.Column(db.Unicode())
    categories = db.Column(db.Unicode())
    tags = db.Column(db.Unicode())
    github_details = db.Column(JsonType())
    last_updated = db.Column(db.DateTime())
    last_updated_issues = db.Column(db.Unicode())
    last_updated_civic_json = db.Column(db.Unicode())
    last_updated_root_files = db.Column(db.Unicode())
    keep = db.Column(db.Boolean())
    tsv_body = db.Column(TSVectorType())
    status = db.Column(db.Unicode())
    languages = db.Column(JsonType())

    # Relationships
    # child
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("projects", cascade="save-update, delete"))
    organization_name = db.Column(db.Unicode(), db.ForeignKey('organization.name', ondelete='CASCADE'), nullable=False)

    # can contain issues (this relationship is defined in the child object)

    def __init__(self, name, code_url=None, link_url=None,
                 description=None, type=None, categories=None, tags=None,
                 github_details=None, last_updated=None, last_updated_issues=None,
                 last_updated_civic_json=None, last_updated_root_files=None, organization_name=None,
                 keep=None, status=None, languages=None):
        self.name = name
        self.code_url = code_url
        self.link_url = link_url
        self.description = description
        self.type = type
        self.categories = categories
        self.tags = tags
        self.github_details = github_details
        self.last_updated = last_updated
        self.last_updated_issues = last_updated_issues
        self.last_updated_civic_json = last_updated_civic_json
        self.last_updated_root_files = last_updated_root_files
        self.organization_name = organization_name
        self.keep = True
        self.status = status
        self.languages = languages

    def api_url(self):
        ''' API link to itself
        '''
        return '%s://%s/api/projects/%s' % (request.scheme, request.host, str(self.id))

    def asdict(self, include_organization=False, include_issues=True):
        ''' Return Project as a dictionary, with some properties tweaked.

            Optionally include linked organization.
        '''
        project_dict = db.Model.asdict(self)

        # remove fields that don't need to be public
        del project_dict['keep']
        del project_dict['tsv_body']
        del project_dict['last_updated_issues']
        del project_dict['last_updated_civic_json']
        del project_dict['last_updated_root_files']

        project_dict['api_url'] = self.api_url()

        if include_organization:
            project_dict['organization'] = self.organization.asdict()

        if include_issues:
            project_dict['issues'] = [o.asdict() for o in db.session.query(Issue).filter(Issue.project_id == project_dict['id']).all()]

        return project_dict

tbl = Project.__table__
# Index the tsvector column
db.Index('index_project_tsv_body', tbl.c.tsv_body, postgresql_using='gin')

# Trigger to populate the search index column
trig_ddl = DDL("""
    DROP FUNCTION IF EXISTS project_search_trigger();
    CREATE FUNCTION project_search_trigger() RETURNS trigger AS $$
    begin
      new.tsv_body :=
         setweight(to_tsvector('pg_catalog.english', coalesce(new.status,'')), 'A') ||
         setweight(to_tsvector('pg_catalog.english', coalesce(new.tags,'')), 'A') ||
         setweight(to_tsvector('pg_catalog.english', coalesce(new.name,'')), 'B') ||
         setweight(to_tsvector('pg_catalog.english', coalesce(new.description,'')), 'B') ||
         setweight(to_tsvector('pg_catalog.english', coalesce(new.languages,'')), 'A');
      return new;
    end
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER tsvupdate_projects_trigger BEFORE INSERT OR UPDATE ON project FOR EACH ROW EXECUTE PROCEDURE project_search_trigger();
""")
# Initialize the trigger after table is created
event.listen(tbl, 'after_create', trig_ddl.execute_if(dialect='postgresql'))


class Issue(db.Model):
    '''
        Issues of Civic Tech Projects on Github
    '''
    # Columns
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.Unicode())
    html_url = db.Column(db.Unicode())
    body = db.Column(db.Unicode())
    keep = db.Column(db.Boolean())

    # Relationships
    # child
    project = db.relationship('Project', single_parent=True, cascade='all, delete-orphan', backref=backref("issues", cascade="save-update, delete"))
    project_id = db.Column(db.Integer(), db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)

    # can contain labels (this relationship is defined in the child object)

    def __init__(self, title, project_id=None, html_url=None, labels=None, body=None):
        self.title = title
        self.html_url = html_url
        self.body = body
        self.project_id = project_id
        self.keep = True

    def api_url(self):
        ''' API link to itself
        '''
        return '%s://%s/api/issues/%s' % (request.scheme, request.host, str(self.id))

    def asdict(self, include_project=False):
        '''
            Return issue as a dictionary with some properties tweaked
        '''
        issue_dict = db.Model.asdict(self)

        # TODO: Also paged_results assumes asdict takes this argument, should be checked and fixed later
        if include_project:
            issue_dict['project'] = db.session.query(Project).filter(Project.id == self.project_id).first().asdict()
            del issue_dict['project']['issues']
            del issue_dict['project_id']

        # remove fields that don't need to be public
        del issue_dict['keep']

        issue_dict['api_url'] = self.api_url()
        issue_dict['labels'] = [l.asdict() for l in self.labels]

        return issue_dict


class Label(db.Model):
    '''
        Issue labels for projects on Github
    '''
    # Columns
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode())
    color = db.Column(db.Unicode())
    url = db.Column(db.Unicode())

    # Relationships
    # child
    issue = db.relationship('Issue', single_parent=True, cascade='all, delete-orphan', backref=backref("labels", cascade="save-update, delete"))
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id', ondelete='CASCADE'), nullable=False, index=True)

    def __init__(self, name, color, url, issue_id=None):
        self.name = name
        self.color = color
        self.url = url
        self.issue_id = issue_id

    def asdict(self):
        '''
            Return label as a dictionary with some properties tweaked
        '''
        label_dict = db.Model.asdict(self)

        # remove fields that don't need to be public
        del label_dict['id']
        del label_dict['issue_id']

        return label_dict


class Event(db.Model):
    '''
        Organizations events from Meetup
    '''
    # Columns
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode())
    description = db.Column(db.Unicode())
    event_url = db.Column(db.Unicode())
    location = db.Column(db.Unicode())
    created_at = db.Column(db.Unicode())
    start_time_notz = db.Column(db.DateTime(False))
    end_time_notz = db.Column(db.DateTime(False))
    utc_offset = db.Column(db.Integer())
    rsvps = db.Column(db.Integer())
    keep = db.Column(db.Boolean())

    # Relationships
    # child
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("events", cascade="save-update, delete"))
    organization_name = db.Column(db.Unicode(), db.ForeignKey('organization.name', ondelete='CASCADE'), nullable=False)

    def __init__(self, name, event_url, start_time_notz, created_at, utc_offset,
                 organization_name, location=None, end_time_notz=None, description=None, rsvps=None):
        self.name = name
        self.description = description
        self.location = location
        self.event_url = event_url
        self.start_time_notz = start_time_notz
        self.utc_offset = utc_offset
        self.end_time_notz = end_time_notz
        self.organization_name = organization_name
        self.created_at = created_at
        self.rsvps = rsvps
        self.keep = True

    def start_time(self):
        ''' Get a string representation of the start time with UTC offset.
        '''
        if self.start_time_notz is None:
            return None
        tz = tzoffset(None, self.utc_offset)
        st = self.start_time_notz
        dt = datetime(st.year, st.month, st.day, st.hour, st.minute, st.second, tzinfo=tz)
        return dt.strftime('%Y-%m-%d %H:%M:%S %z')

    def end_time(self):
        ''' Get a string representation of the end time with UTC offset.
        '''
        if self.end_time_notz is None:
            return None
        tz = tzoffset(None, self.utc_offset)
        et = self.end_time_notz
        dt = datetime(et.year, et.month, et.day, et.hour, et.minute, et.second, tzinfo=tz)
        return dt.strftime('%Y-%m-%d %H:%M:%S %z')

    def api_url(self):
        ''' API link to itself
        '''
        return '%s://%s/api/events/%s' % (request.scheme, request.host, str(self.id))

    def asdict(self, include_organization=False):
        ''' Return Event as a dictionary, with some properties tweaked.

            Optionally include linked organization.
        '''
        event_dict = db.Model.asdict(self)

        # remove fields that don't need to be public
        for key in ('keep', 'start_time_notz', 'end_time_notz', 'utc_offset'):
            del event_dict[key]

        for key in ('start_time', 'end_time', 'api_url'):
            event_dict[key] = getattr(self, key)()

        if include_organization:
            event_dict['organization'] = self.organization.asdict()

        return event_dict


class Attendance(db.Model):
    ''' Attendance at organization events
        sourced from the peopledb
    '''
    # Columns
    organization_url = db.Column(db.Unicode(), primary_key=True)
    total = db.Column(db.Integer())
    weekly = db.Column(JsonType())

    # Relationship
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("attendance", cascade="save-update, delete"))
    organization_name = db.Column(db.Unicode(), db.ForeignKey('organization.name', ondelete='CASCADE'), nullable=False)

    def __init__(self, organization_url, organization_name, total, weekly):
        self.organization_url = organization_url
        self.organization_name = organization_name
        self.total = total
        self.weekly = weekly


class Error(db.Model):
    '''
        Errors from run_update.py
    '''
    # Columns
    id = db.Column(db.Integer(), primary_key=True)
    error = db.Column(db.Unicode())
    time = db.Column(db.DateTime(False))
