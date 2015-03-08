# -------------------
# Imports
# -------------------

from __future__ import division

from datetime import datetime, date
import json
import os
import time
from mimetypes import guess_type
from os.path import join
from math import ceil
from urllib import urlencode

from flask import Flask, make_response, request, jsonify, render_template
import requests
from flask.ext.heroku import Heroku
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy import types, desc
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import backref
from dictalchemy import make_class_dictable
from dateutil.tz import tzoffset
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand


# -------------------
# Init
# -------------------

app = Flask(__name__)
heroku = Heroku(app)
db = SQLAlchemy(app)

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

make_class_dictable(db.Model)

# -------------------
# Settings
# -------------------

def add_cors_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, PUT, PATCH, DELETE, OPTIONS'
    return response

app.after_request(add_cors_header)


# -------------------
# Types
# -------------------

class JsonType(Mutable, types.TypeDecorator):
    ''' JSON wrapper type for TEXT database storage.

        References:
        http://stackoverflow.com/questions/4038314/sqlalchemy-json-as-blob-text
        http://docs.sqlalchemy.org/en/rel_0_9/orm/extensions/mutable.html
    '''
    impl = types.Unicode

    def process_bind_param(self, value, engine):
        return unicode(json.dumps(value))

    def process_result_value(self, value, engine):
        if value:
            return json.loads(value)
        else:
            # default can also be a list
            return {}


# -------------------
# Models
# -------------------

class Organization(db.Model):
    '''
        Brigades and other civic tech organizations
    '''
    #Columns
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
    keep = db.Column(db.Boolean())

    # Relationships
    # can contain events, stories, projects (these relationships are defined in the child objects)

    def __init__(self, name, website=None, events_url=None,
                 rss=None, projects_list_url=None, type=None, city=None, latitude=None, longitude=None):
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
        self.last_updated = time.time()
        self.started_on = unicode(date.today())

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

        del organization_dict['keep']

        for key in ('all_events', 'all_projects', 'all_stories', 'all_issues',
                    'upcoming_events', 'past_events', 'api_url'):
            organization_dict[key] = getattr(self, key)()

        if include_extras:
            for key in ('current_events', 'current_projects', 'current_stories'):
                organization_dict[key] = getattr(self, key)()

        return organization_dict

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
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("stories", cascade="save-update, delete")) #child
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
    github_details = db.Column(JsonType())
    last_updated = db.Column(db.DateTime())
    last_updated_issues = db.Column(db.Unicode())
    keep = db.Column(db.Boolean())
    status = db.Column(db.Unicode())

    # Relationships
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("projects", cascade="save-update, delete")) #child
    organization_name = db.Column(db.Unicode(), db.ForeignKey('organization.name', ondelete='CASCADE'), nullable=False)

    # can contain issues (this relationship is defined in the child object)

    def __init__(self, name, code_url=None, link_url=None,
                 description=None, type=None, categories=None,
                 github_details=None, last_updated=None, last_updated_issues=None,
                 organization_name=None, keep=None, status=None):
        self.name = name
        self.code_url = code_url
        self.link_url = link_url
        self.description = description
        self.type = type
        self.categories = categories
        self.github_details = github_details
        self.last_updated = last_updated
        self.last_updated_issues = last_updated_issues
        self.organization_name = organization_name
        self.keep = True
        self.status = status

    def api_url(self):
        ''' API link to itself
        '''
        return '%s://%s/api/projects/%s' % (request.scheme, request.host, str(self.id))

    def asdict(self, include_organization=False, include_issues=True):
        ''' Return Project as a dictionary, with some properties tweaked.

            Optionally include linked organization.
        '''
        project_dict = db.Model.asdict(self)

        del project_dict['keep']
        project_dict['api_url'] = self.api_url()

        if include_organization:
            project_dict['organization'] = self.organization.asdict()

        if include_issues:
            project_dict['issues'] = [o.asdict() for o in db.session.query(Issue).filter(Issue.project_id == project_dict['id']).all()]

        return project_dict

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
    project = db.relationship('Project', single_parent=True, cascade='all, delete-orphan', backref=backref("issues", cascade="save-update, delete")) #child
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
    issue = db.relationship('Issue', single_parent=True, cascade='all, delete-orphan', backref=backref("labels", cascade="save-update, delete")) #child
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

        del label_dict['id']
        del label_dict['issue_id']

        return label_dict

class Event(db.Model):
    '''
        Organizations events from Meetup
    '''
    # Columns
    id  = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode())
    description = db.Column(db.Unicode())
    event_url = db.Column(db.Unicode())
    location = db.Column(db.Unicode())
    created_at = db.Column(db.Unicode())
    start_time_notz = db.Column(db.DateTime(False))
    end_time_notz = db.Column(db.DateTime(False))
    utc_offset = db.Column(db.Integer())
    keep = db.Column(db.Boolean())

    # Relationships
    organization = db.relationship('Organization', single_parent=True, cascade='all, delete-orphan', backref=backref("events", cascade="save-update, delete")) #child
    organization_name = db.Column(db.Unicode(), db.ForeignKey('organization.name', ondelete='CASCADE'), nullable=False)

    def __init__(self, name, event_url, start_time_notz, created_at, utc_offset,
                 organization_name, location=None, end_time_notz=None, description=None):
        self.name = name
        self.description = description
        self.location = location
        self.event_url = event_url
        self.start_time_notz = start_time_notz
        self.utc_offset = utc_offset
        self.end_time_notz = end_time_notz
        self.organization_name = organization_name
        self.created_at = created_at
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

        for key in ('keep', 'start_time_notz', 'end_time_notz', 'utc_offset'):
            del event_dict[key]

        for key in ('start_time', 'end_time', 'api_url'):
            event_dict[key] = getattr(self, key)()

        if include_organization:
            event_dict['organization'] = self.organization.asdict()

        return event_dict

class Error(db.Model):
    '''
        Errors from run_update.py
    '''
    # Columns
    id  = db.Column(db.Integer(), primary_key=True)
    error = db.Column(db.Unicode())
    time = db.Column(db.DateTime(False))

# -------------------
# API
# -------------------

def page_info(query, page, limit):
    ''' Return last page and offset for a query.
    '''
    # Get a bunch of projects.
    total = query.count()
    last = int(ceil(total / limit))
    offset = (page - 1) * limit

    return last, offset

def pages_dict(page, last, querystring):
    ''' Return a dictionary of pages to return in API responses.
    '''
    url = '%s://%s%s' % (request.scheme, request.host, request.path)

    pages = dict()

    if page > 1:
        pages['first'] = dict()
        pages['prev'] = dict()
        if 'per_page' in request.args:
            pages['first']['per_page'] = request.args['per_page']
            pages['prev']['per_page'] = request.args['per_page']

    if page > 2:
        pages['prev']['page'] = page - 1

    if page < last:
        pages['next'] = {'page': page + 1}
        pages['last'] = {'page': last}
        if 'per_page' in request.args:
            pages['next']['per_page'] = request.args['per_page']
            pages['last']['per_page'] = request.args['per_page']

    for key in pages:
        if querystring != '':
            pages[key] = '%s?%s&%s' % (url, urlencode(pages[key]), querystring) if pages[key] else url
        else:
            pages[key] = '%s?%s' % (url, urlencode(pages[key])) if pages[key] else url

    return pages

def paged_results(query, page, per_page, querystring=''):
    '''
    '''
    total = query.count()
    last, offset = page_info(query, page, per_page)
    model_dicts = [o.asdict(True) for o in query.limit(per_page).offset(offset)]

    return dict(total=total, pages=pages_dict(page, last, querystring), objects=model_dicts)

def is_safe_name(name):
    ''' Return True if the string is a safe name.
    '''
    return raw_name(safe_name(name)) == name

def safe_name(name):
    ''' Return URL-safe organization name with spaces replaced by dashes.

        Slashes will be removed, which is incompatible with raw_name().
    '''
    return name.replace(' ', '-').replace('/', '-').replace('?','-').replace('#','-')

def raw_name(name):
    ''' Return raw organization name with dashes replaced by spaces.

        Also replace old-style underscores with spaces.
    '''
    return name.replace('_', ' ').replace('-', ' ')

def get_query_params(args):
    filters = {}
    for key,value in args.iteritems():
        if 'page' not in key:
            filters[key] = value
    return filters, urlencode(filters)

@app.route('/api/organizations')
@app.route('/api/organizations/<name>')
def get_organizations(name=None):
    ''' Regular response option for organizations.
    '''

    filters = request.args
    filters, querystring = get_query_params(request.args)

    if name:
        # Get one named organization.
        filter = Organization.name == raw_name(name)
        org = db.session.query(Organization).filter(filter).first()
        if org:
            return jsonify(org.asdict(True))
        else:
            # If no org found
            return jsonify({"status":"Resource Not Found"}), 404

    # Get a bunch of organizations.
    query = db.session.query(Organization)

    for attr, value in filters.iteritems():
        query = query.filter(getattr(Organization, attr).ilike('%%%s%%' % value))

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 10)), querystring)

    return jsonify(response)

@app.route('/api/organizations.geojson')
def get_organizations_geojson():
    ''' GeoJSON response option for organizations.
    '''
    geojson = dict(type='FeatureCollection', features=[])

    for org in db.session.query(Organization):
        # The unique identifier of an organization.
        id = org.api_id()

        # Pick out all the properties that aren't part of the location.
        props = org.asdict()

        # GeoJSON Point geometry, http://geojson.org/geojson-spec.html#point
        geom = dict(type='Point', coordinates=[org.longitude, org.latitude])

        feature = dict(type='Feature', id=id, properties=props, geometry=geom)
        geojson['features'].append(feature)

    return jsonify(geojson)

@app.route("/api/organizations/<organization_name>/events")
def get_orgs_events(organization_name):
    '''
        A cleaner url for getting an organizations events
        Better than /api/events?q={"filters":[{"name":"organization_name","op":"eq","val":"Code for San Francisco"}]}
    '''
    # Check org name
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404

    # Get event objects
    query = Event.query.filter_by(organization_name=organization.name)
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)))
    return jsonify(response)

@app.route("/api/organizations/<organization_name>/upcoming_events")
def get_upcoming_events(organization_name):
    '''
        Get events that occur in the future. Order asc.
    '''
    # Check org name
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404
    # Get upcoming event objects
    query = Event.query.filter(Event.organization_name == organization.name, Event.start_time_notz >= datetime.utcnow())
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)))
    return jsonify(response)

@app.route("/api/organizations/<organization_name>/past_events")
def get_past_events(organization_name):
    '''
        Get events that occur in the past. Order desc.
    '''
    # Check org name
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404
    # Get past event objects
    query = Event.query.filter(Event.organization_name == organization.name, Event.start_time_notz < datetime.utcnow()).\
            order_by(desc(Event.start_time_notz))
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)))
    return jsonify(response)

@app.route("/api/organizations/<organization_name>/stories")
def get_orgs_stories(organization_name):
    '''
        A cleaner url for getting an organizations stories
    '''
    # Check org name
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404

    # Get story objects
    query = Story.query.filter_by(organization_name=organization.name).order_by(desc(Story.id))
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)))
    return jsonify(response)

@app.route("/api/organizations/<organization_name>/projects")
def get_orgs_projects(organization_name):
    '''
        A cleaner url for getting an organizations projects
    '''
    # Check org name
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404

    # Get project objects
    query = Project.query.filter_by(organization_name=organization.name).order_by(desc(Project.last_updated))
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 10)))
    return jsonify(response)

@app.route("/api/organizations/<organization_name>/issues")
@app.route("/api/organizations/<organization_name>/issues/labels/<labels>")
def get_orgs_issues(organization_name, labels=None):
    ''' A clean url to get an organizations issues
    '''

    # Get one named organization.
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404

    # Get that organization's projects
    projects = Project.query.filter_by(organization_name=organization.name).all()
    project_ids = [project.id for project in projects]

    # Get all issues belonging to these projects
    query = Issue.query.filter(Issue.project_id.in_(project_ids))

    if labels:
        # Create a labels list by comma separating the argument
        labels = [label.strip() for label in labels.split(',')]

        # Create the filter for each label
        labels = [Label.name.ilike('%%%s%%' % label) for label in labels]

        # Create the base query object by joining on Issue.labels
        query = query.join(Issue.labels)

        # Filter for issues with each individual label
        label_queries = [query.filter(L) for L in labels]

        # Intersect filters to find issues with all labels
        query = query.intersect(*label_queries)

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 10)))
    return jsonify(response)

@app.route('/api/projects')
@app.route('/api/projects/<int:id>')
def get_projects(id=None):
    ''' Regular response option for projects.
    '''

    filters, querystring = get_query_params(request.args)

    if id:
        # Get one named project.
        filter = Project.id == id
        proj = db.session.query(Project).filter(filter).first()
        if proj:
            return jsonify(proj.asdict(True))
        else:
            # If no project found
            return jsonify({"status":"Resource Not Found"}), 404

    # Get a bunch of projects.
    query = db.session.query(Project)

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Project.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            query = query.filter(getattr(Project, attr).ilike('%%%s%%' % value))

    query = query.order_by(desc(Project.last_updated))
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 10)), querystring)
    return jsonify(response)

@app.route('/api/issues')
@app.route('/api/issues/<int:id>')
def get_issues(id=None):
    '''Regular response option for issues.
    '''

    filters = request.args
    filters, querystring = get_query_params(request.args)

    if id:
        # Get one issue
        filter = Issue.id == id
        issue = db.session.query(Issue).filter(filter).first()
        if issue:
            return jsonify(issue.asdict(True))
        else:
            # If no issue found
            return jsonify({"status":"Resource Not Found"}), 404

    # Get a bunch of issues
    query = db.session.query(Issue).order_by(func.random())

    for attr, value in filters.iteritems():
        if 'project' in attr:
            proj_attr = attr.split('_')[1]
            query = query.join(Issue.project).filter(getattr(Project, proj_attr).ilike('%%%s%%' % value))
        elif 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Issue.project).join(Project.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            query = query.filter(getattr(Issue, attr).ilike('%%%s%%' % value))

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 10)), querystring)
    return jsonify(response)

@app.route('/api/issues/labels/<labels>')
def get_issues_by_labels(labels):
    '''
    A clean url to filter issues by a comma-separated list of labels
    '''

    # Create a labels list by comma separating the argument
    labels = [label.strip() for label in labels.split(',')]

    # Create the filter for each label
    labels = [Label.name.ilike('%%%s%%' % label) for label in labels]

    # Create the base query object by joining on Issue.labels
    base_query = db.session.query(Issue).join(Issue.labels)

    # Check for parameters
    filters = request.args
    filters, querystring = get_query_params(request.args)
    for attr, value in filters.iteritems():
        if 'project' in attr:
            proj_attr = attr.split('_')[1]
            base_query = base_query.join(Issue.project).filter(getattr(Project, proj_attr).ilike('%%%s%%' % value))
        elif 'organization' in attr:
            org_attr = attr.split('_')[1]
            base_query = base_query.join(Issue.project).join(Project.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            base_query = base_query.filter(getattr(Issue, attr).ilike('%%%s%%' % value))

    # Filter for issues with each individual label
    label_queries = [base_query.filter(L) for L in labels]

    # Intersect filters to find issues with all labels
    query = base_query.intersect(*label_queries).order_by(func.random())

    # Return the paginated reponse
    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 10)))
    return jsonify(response)

@app.route('/api/events')
@app.route('/api/events/<int:id>')
def get_events(id=None):
    ''' Regular response option for events.
    '''

    filters = request.args
    filters, querystring = get_query_params(request.args)

    if id:
        # Get one named event.
        filter = Event.id == id
        event = db.session.query(Event).filter(filter).first()
        if event:
            return jsonify(event.asdict(True))
        else:
            # If no event found
            return jsonify({"status":"Resource Not Found"}), 404

    # Get a bunch of events.
    query = db.session.query(Event)

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Event.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            query = query.filter(getattr(Event, attr).ilike('%%%s%%' % value))

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)), querystring)
    return jsonify(response)

@app.route('/api/events/upcoming_events')
def get_all_upcoming_events():
    ''' Show all upcoming events.
        Return them in chronological order.
    '''
    filters = request.args
    filters, querystring = get_query_params(request.args)

    query = db.session.query(Event).filter(Event.start_time_notz >= datetime.utcnow()).order_by(Event.start_time_notz)

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Event.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            query = query.filter(getattr(Event, attr).ilike('%%%s%%' % value))

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)))
    return jsonify(response)


@app.route('/api/events/past_events')
def get_all_past_events():
    ''' Show all past events.
        Return them in reverse chronological order.
    '''
    filters = request.args
    filters, querystring = get_query_params(request.args)

    query = db.session.query(Event).filter(Event.start_time_notz <= datetime.utcnow()).order_by(desc(Event.start_time_notz))

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Event.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            query = query.filter(getattr(Event, attr).ilike('%%%s%%' % value))

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)))
    return jsonify(response)

@app.route('/api/stories')
@app.route('/api/stories/<int:id>')
def get_stories(id=None):
    ''' Regular response option for stories.
    '''

    filters = request.args
    filters, querystring = get_query_params(request.args)

    if id:
        # Get one named story.
        filter = Story.id == id
        story = db.session.query(Story).filter(filter).first()
        if story:
            return jsonify(story.asdict(True))
        else:
            # If no story found
            return jsonify({"status":"Resource Not Found"}), 404

    # Get a bunch of stories.
    query = db.session.query(Story).order_by(desc(Story.id))

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Story.organization).filter(getattr(Organization, org_attr).ilike('%%%s%%' % value))
        else:
            query = query.filter(getattr(Story, attr).ilike('%%%s%%' % value))

    response = paged_results(query, int(request.args.get('page', 1)), int(request.args.get('per_page', 25)), querystring)
    return jsonify(response)

# -------------------
# Routes
# -------------------

@app.route('/api/.well-known/status')
def well_known_status():
    ''' Return status information for Engine Light.

        http://engine-light.codeforamerica.org
    '''
    if 'GITHUB_TOKEN' in os.environ:
        github_auth = (os.environ['GITHUB_TOKEN'], '')
    else:
        github_auth = None

    if 'MEETUP_KEY' in os.environ:
        meetup_key = os.environ['MEETUP_KEY']
    else:
        meetup_key = None

    try:
        org = db.session.query(Organization).order_by(Organization.last_updated).limit(1).first()
        project = db.session.query(Project).limit(1).first()
        rate_limit = requests.get('https://api.github.com/rate_limit', auth=github_auth)
        remaining_github = rate_limit.json()['resources']['core']['remaining']
        recent_error = db.session.query(Error).order_by(desc(Error.time)).limit(1).first()

        meetup_status = "No Meetup key set"
        if meetup_key:
            meetup_url = 'https://api.meetup.com/status?format=json&key='+meetup_key
            meetup_status = requests.get(meetup_url).json().get('status')

        time_since_updated = time.time() - getattr(org, 'last_updated', -1)

        if not hasattr(project, 'name'):
            status = 'Sample project is missing a name'

        elif not hasattr(org, 'name'):
            status = 'Sample project is missing a name'

        elif recent_error:
            if recent_error.time.date() == date.today():
                status = recent_error.error
            else:
                status = 'ok' # is this really okay?

        elif time_since_updated > 16 * 60 * 60:
            status = 'Oldest organization (%s) updated more than 16 hours ago' % org.name

        elif remaining_github < 1000:
            status = 'Only %d remaining Github requests' % remaining_github

        elif meetup_status != 'ok':
            status = 'Meetup status is "%s"' % meetup_status

        else:
            status = 'ok'

    except Exception, e:
        status = 'Error: ' + str(e)

    state = dict(status=status, updated=int(time.time()), resources=[])
    state.update(dict(dependencies=['Meetup', 'Github', 'PostgreSQL']))

    return jsonify(state)

@app.route("/")
def index():
    response = make_response('Look in /api', 302)
    response.headers['Location'] = '/api'
    return response

@app.route("/api")
@app.route("/api/")
def api_index():
    return render_template('index.html', api_base='%s://%s' % (request.scheme, request.host))

@app.route("/api/static/<path:path>")
def api_static_file(path):
    local_path = join('static', path)
    mime_type, _ = guess_type(path)
    response = make_response(open(local_path).read())
    response.headers['Content-Type'] = mime_type
    return response

@app.errorhandler(404)
def page_not_found(error):
    return jsonify({"status":"Resource Not Found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status":"Resource Not Found"}), 500

if __name__ == "__main__":
    manager.run()
