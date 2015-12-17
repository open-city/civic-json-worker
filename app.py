# -------------------
# Imports
# -------------------

from __future__ import division

from datetime import datetime, date
import os
import time
import re
from mimetypes import guess_type
from os.path import join
from math import ceil
from urllib import urlencode

from flask import Flask, make_response, request, jsonify, render_template
import requests
from flask.ext.heroku import Heroku
from sqlalchemy import desc
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import defer
from dictalchemy import make_class_dictable
from flask.ext.script import Manager, Server, prompt_bool
from flask.ext.migrate import Migrate, MigrateCommand
from werkzeug.contrib.fixers import ProxyFix
from models import initialize_database, Organization, Event, Issue, Project, Story, Label, Error, Attendance
from utils import raw_name

# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# -------------------
# Init
# -------------------

app = Flask(__name__)
heroku = Heroku(app)
db = initialize_database(app)

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('runserver', Server(use_debugger=True))

@manager.command
def dropdb():
    if prompt_bool("Are you sure you want to lose all your data?"):
        db.drop_all()


@manager.command
def createdb():
    db.create_all()

make_class_dictable(db.Model)

app.wsgi_app = ProxyFix(app.wsgi_app)

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
# API
# -------------------

def page_info(total, page, limit):
    ''' Return last page and offset for a query total.
    '''
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


def paged_results(query, include_args=None, page=1, per_page=10, querystring=''):
    ''' Return a dict representing one page-worth of results
    '''
    items = [item for item in query]
    total = len(items)

    last, offset = page_info(total, page, per_page)
    page_of_items = items[offset:offset + per_page]
    if 'only_ids' in querystring:
        model_dicts = [o.id for o in page_of_items]
    else:
        model_dicts = []
        for o in page_of_items:
            obj = o.asdict(**include_args) if include_args else o.asdict()
            model_dicts.append(obj)
    return dict(total=total, pages=pages_dict(page, last, querystring), objects=model_dicts)


def get_query_params(args):
    filters = {}
    for key, value in args.iteritems():
        if 'page' not in key:
            filters[key] = value.encode('utf8')
    return filters, urlencode(filters)

def format_ilike_term(term):
    ''' Format the passed term for use in an ilike query.
    '''
    # strip pattern-matching metacharacters from the term
    stripped_term = re.sub(ur'\||_|%|\*|\+|\?|\{|\}|\(|\)|\[|\]', '', term)
    return u'%{}%'.format(stripped_term)

def build_rsvps_response(events):
    ''' Arrange and organize rsvps from a list of event objects '''
    rsvps = {
        "total": 0,
        "weekly": {}
    }
    for fetched_event in events:
        event_dict = fetched_event.asdict()
        if event_dict["rsvps"]:
            # 2014-04-30 18:30:00 -0700
            # Just compare dates
            event_date = event_dict["start_time"][:10]
            event_date = datetime.strptime(event_date, "%Y-%m-%d")
            if datetime.today() > event_date:
                week = datetime.strftime(event_date, "%Y %W")
                rsvps["total"] += event_dict["rsvps"]
                if rsvps["weekly"].get(week):
                    rsvps["weekly"][week] += event_dict["rsvps"]
                else:
                    rsvps["weekly"][week] = event_dict["rsvps"]

    return rsvps


@app.route('/api/organizations')
@app.route('/api/organizations/<name>')
def get_organizations(name=None):
    ''' Regular response option for organizations.
    '''

    filters, querystring = get_query_params(request.args)

    if name:
        # Get one named organization.
        org_filter = Organization.name == raw_name(name)
        org = db.session.query(Organization).filter(org_filter).first()
        if org:
            return jsonify(org.asdict(True))
        else:
            # If no org found
            return jsonify({"status": "Resource Not Found"}), 404

    # Get a bunch of organizations.
    query = db.session.query(Organization)
    # Default ordering of results
    ordering = desc(Organization.last_updated)

    for attr, value in filters.iteritems():
        if 'q' in attr:
            query = query.filter('organization.tsv_body @@ plainto_tsquery(:search_query)').params(search_query=value)
            ordering = desc(func.ts_rank(Organization.tsv_body, func.plainto_tsquery(value)))
        else:
            query = query.filter(getattr(Organization, attr).ilike(format_ilike_term(value)))

    query = query.order_by(ordering)
    response = paged_results(query=query, include_args=dict(include_extras=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 10)), querystring=querystring)

    return jsonify(response)


@app.route('/api/organizations.geojson')
def get_organizations_geojson():
    ''' GeoJSON response option for organizations.
    '''
    geojson = dict(type='FeatureCollection', features=[])

    for org in db.session.query(Organization):

        # geojson should only return orgs with location data
        if org.latitude and org.longitude:

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
    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)))
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
    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)))
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
    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)))
    return jsonify(response)


@app.route("/api/organizations/<organization_name>/events/rsvps")
def gather_orgs_rsvps(organization_name=None):
    ''' Orgs rsvps summarized '''
    # Check org name
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404
    orgs_events = Event.query.filter(Event.organization_name == organization.name).all()
    rsvps = build_rsvps_response(orgs_events)

    return jsonify(rsvps)


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
    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)))
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

    filters, querystring = get_query_params(request.args)

    # Get project objects
    query = db.session.query(Project).filter_by(organization_name=organization.name).options(defer('tsv_body'))

    # Default ordering of results
    last_updated_ordering_filter = Project.last_updated
    relevance_ordering_filter = None
    ordering_filter_name = 'last_updated'
    ordering_filter = last_updated_ordering_filter
    ordering_dir = 'desc'
    ordering = None

    for attr, value in filters.iteritems():
        if 'q' in attr:
            # Returns all results if the value is empty
            if value:
                query = query.filter('project.tsv_body @@ plainto_tsquery(:search_query)').params(search_query=value)
                relevance_ordering_filter = func.ts_rank(Project.tsv_body, func.plainto_tsquery(value))
                ordering_filter_name = 'relevance'
        elif 'only_ids' in attr:
            query = query.with_entities(Project.id)
        elif 'sort_by' in attr:
            if value == 'relevance':
                ordering_filter_name = 'relevance'
            else:
                ordering_filter_name = 'last_updated'
        elif 'sort_dir' in attr:
            if value == 'asc':
                ordering_dir = 'asc'
            else:
                ordering_dir = 'desc'
        else:
            query = query.filter(getattr(Project, attr).ilike(format_ilike_term(value)))

    if ordering_filter_name == 'last_updated':
        ordering_filter = last_updated_ordering_filter
    elif ordering_filter_name == 'relevance' and dir(relevance_ordering_filter) != dir(None):
        ordering_filter = relevance_ordering_filter

    if ordering_dir == 'desc':
        ordering = ordering_filter.desc()
    else:
        ordering = ordering_filter.asc()
    query = query.order_by(ordering)

    response = paged_results(query=query, include_args=dict(include_organization=True, include_issues=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 10)), querystring=querystring)
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

    if labels:
        # Get all issues belonging to these projects
        query = Issue.query.filter(Issue.project_id.in_(project_ids))

        # Create a labels list by comma separating the argument
        labels = [label.strip() for label in labels.split(',')]

        # Create the filter for each label
        labels = [Label.name.ilike(format_ilike_term(label)) for label in labels]

        # Create the base query object by joining on Issue.labels
        query = query.join(Issue.labels)

        # Filter for issues with each individual label
        label_queries = [query.filter(L) for L in labels]

        # Intersect filters to find issues with all labels
        query = query.intersect(*label_queries).order_by(func.random())

    else:
        # Get all issues belonging to these projects
        query = Issue.query.filter(Issue.project_id.in_(project_ids)).order_by(func.random())

    filters, querystring = get_query_params(request.args)
    response = paged_results(query=query, include_args=dict(include_project=True, include_labels=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 10)), querystring=querystring)
    return jsonify(response)


@app.route("/api/organizations/<organization_name>/attendance")
def get_orgs_attendance(organization_name):
    ''' A clean url to get an organizations attendance '''

    # Get one named organization.
    organization = Organization.query.filter_by(name=raw_name(organization_name)).first()
    if not organization:
        return "Organization not found", 404

    attendance_response = {
        "organization_name": organization.name,
        "cfapi_url": organization.api_url(),
        "total": 0,
        "weekly": {}
    }

    # Get that organization's attendance
    attendance = Attendance.query.filter_by(organization_name=organization.name).first()

    if attendance:
        weekly = {}
        for week in attendance.weekly.keys():
            if week in weekly.keys():
                weekly[week] += attendance.weekly[week]
            else:
                weekly[week] = attendance.weekly[week]
        attendance.weekly = weekly

        attendance_response['total'] = attendance.total
        attendance_response['weekly'] = attendance.weekly

    return jsonify(attendance_response)


def find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return False


@app.route("/api/organizations/attendance")
def get_all_orgs_attendance():
    ''' A list of all organizations attendance '''
    all_attendance = Attendance.query.all()
    response = []

    for org_attendance in all_attendance:
        weekly = {}
        for week in org_attendance.weekly.keys():
            if week in weekly.keys():
                weekly[week] += org_attendance.weekly[week]
            else:
                weekly[week] = org_attendance.weekly[week]
        attendance_response = {
            "organization_name": org_attendance.organization_name,
            "cfapi_url": org_attendance.organization_url,
            "total": org_attendance.total,
            "weekly": weekly
        }
        response.append(attendance_response)

    return jsonify(dict(organizations=response, total=len(response)))


@app.route("/api/attendance")
def get_all_attendance():
    ''' All attendance summarized '''
    all_attendance = Attendance.query.all()
    total = 0
    weekly = {}
    for org_attendance in all_attendance:
        total += org_attendance.total
        for week in org_attendance.weekly.keys():
            if week in weekly.keys():
                weekly[week] += org_attendance.weekly[week]
            else:
                weekly[week] = org_attendance.weekly[week]

    response = {
        "total": total,
        "weekly": weekly
    }

    return jsonify(response)


@app.route("/api/member_count")
def all_member_count():
    ''' The total Meetup.com member count '''
    member_count = 0
    orgs = Organization.query.all()
    for org in orgs:
        if org.member_count:
            member_count += org.member_count

    return jsonify({"total": member_count})


@app.route("/api/organizations/member_count")
def orgs_member_count():
    ''' The Meetup.com member count for each group '''
    total_member_count = 0
    orgs_members = {}
    orgs = Organization.query.all()
    for org in orgs:
        if org.member_count:
            total_member_count += org.member_count
            orgs_members[org.id] = org.member_count

    response = {
        "total": total_member_count,
        "organizations": orgs_members
    }

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
            return jsonify({"status": "Resource Not Found"}), 404

    # Get a bunch of projects.
    query = db.session.query(Project).options(defer('tsv_body'))
    # Default ordering of results
    last_updated_ordering_filter = Project.last_updated
    relevance_ordering_filter = None
    ordering_filter_name = 'last_updated'
    ordering_filter = last_updated_ordering_filter
    ordering_dir = 'desc'
    ordering = None

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            # Support searching for multiple org_types
            if "," in value:
                values = value.split(",")
                query = query.join(Project.organization).filter(getattr(Organization, org_attr).in_(values))
            else:
                query = query.join(Project.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        elif 'q' in attr:
            # Returns all results if the value is empty
            if value:
                query = query.filter('project.tsv_body @@ plainto_tsquery(:search_query)').params(search_query=value)
                relevance_ordering_filter = func.ts_rank(Project.tsv_body, func.plainto_tsquery(value))
                ordering_filter_name = 'relevance'
        elif 'only_ids' in attr:
            query = query.with_entities(Project.id)
        elif 'sort_by' in attr:
            if value == 'relevance':
                ordering_filter_name = 'relevance'
            else:
                ordering_filter_name = 'last_updated'
        elif 'sort_dir' in attr:
            if value == 'asc':
                ordering_dir = 'asc'
            else:
                ordering_dir = 'desc'
        else:
            query = query.filter(getattr(Project, attr).ilike(format_ilike_term(value)))

    if ordering_filter_name == 'last_updated':
        ordering_filter = last_updated_ordering_filter
    elif ordering_filter_name == 'relevance' and dir(relevance_ordering_filter) != dir(None):
        ordering_filter = relevance_ordering_filter

    if ordering_dir == 'desc':
        ordering = ordering_filter.desc()
    else:
        ordering = ordering_filter.asc()
    query = query.order_by(ordering)

    response = paged_results(query=query, include_args=dict(include_organization=True, include_issues=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 10)), querystring=querystring)
    return jsonify(response)


@app.route('/api/issues')
@app.route('/api/issues/<int:id>')
def get_issues(id=None):
    '''Regular response option for issues.
    '''
    filters, querystring = get_query_params(request.args)

    if id:
        # Get one issue
        filter = Issue.id == id
        issue = db.session.query(Issue).filter(filter).first()
        if issue:
            return jsonify(issue.asdict(True))
        else:
            # If no issue found
            return jsonify({"status": "Resource Not Found"}), 404

    # Get a bunch of issues
    query = db.session.query(Issue).order_by(func.random())

    for attr, value in filters.iteritems():
        if 'project' in attr:
            proj_attr = attr.split('_')[1]
            query = query.join(Issue.project).filter(getattr(Project, proj_attr).ilike(format_ilike_term(value)))
        elif 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Issue.project).join(Project.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        else:
            query = query.filter(getattr(Issue, attr).ilike(format_ilike_term(value)))

    response = paged_results(query=query, include_args=dict(include_project=True, include_labels=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 10)), querystring=querystring)
    return jsonify(response)


@app.route('/api/issues/labels/<labels>')
def get_issues_by_labels(labels):
    '''
    A clean url to filter issues by a comma-separated list of labels
    '''
    # Create a labels list by comma separating the argument
    labels = [label.strip() for label in labels.split(',')]

    # Create the filter for each label
    labels = [Label.name.ilike(format_ilike_term(label)) for label in labels]

    # Create the base query object by joining on Issue.labels
    base_query = db.session.query(Issue).join(Issue.labels)

    # Check for parameters
    filters, querystring = get_query_params(request.args)
    for attr, value in filters.iteritems():
        if 'project' in attr:
            proj_attr = attr.split('_')[1]
            base_query = base_query.join(Issue.project).filter(getattr(Project, proj_attr).ilike(format_ilike_term(value)))
        elif 'organization' in attr:
            org_attr = attr.split('_')[1]
            base_query = base_query.join(Issue.project).join(Project.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        else:
            try:
                filter_attr = getattr(Issue, attr)
                base_query = base_query.filter(filter_attr.ilike(format_ilike_term(value)))
            except AttributeError:
                pass

    # Filter for issues with each individual label
    label_queries = [base_query.filter(L) for L in labels]

    # Intersect filters to find issues with all labels
    query = base_query.intersect(*label_queries).order_by(func.random())

    # Return the paginated reponse
    filters, querystring = get_query_params(request.args)
    response = paged_results(query=query, include_args=dict(include_project=True, include_labels=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 10)), querystring=querystring)
    return jsonify(response)


@app.route('/api/events')
@app.route('/api/events/<int:id>')
def get_events(id=None):
    ''' Regular response option for events.
    '''
    filters, querystring = get_query_params(request.args)

    if id:
        # Get one named event.
        filter = Event.id == id
        event = db.session.query(Event).filter(filter).first()
        if event:
            return jsonify(event.asdict(True))
        else:
            # If no event found
            return jsonify({"status": "Resource Not Found"}), 404

    # Get a bunch of events.
    query = db.session.query(Event)

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Event.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        else:
            query = query.filter(getattr(Event, attr).ilike(format_ilike_term(value)))

    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)), querystring=querystring)
    return jsonify(response)


@app.route('/api/events/upcoming_events')
def get_all_upcoming_events():
    ''' Show all upcoming events.
        Return them in chronological order.
    '''
    filters, querystring = get_query_params(request.args)

    query = db.session.query(Event).filter(Event.start_time_notz >= datetime.utcnow()).order_by(Event.start_time_notz)

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Event.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        else:
            query = query.filter(getattr(Event, attr).ilike(format_ilike_term(value)))

    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)))
    return jsonify(response)


@app.route('/api/events/past_events')
def get_all_past_events():
    ''' Show all past events.
        Return them in reverse chronological order.
    '''
    filters, querystring = get_query_params(request.args)

    query = db.session.query(Event).filter(Event.start_time_notz <= datetime.utcnow()).order_by(desc(Event.start_time_notz))

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Event.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        else:
            query = query.filter(getattr(Event, attr).ilike(format_ilike_term(value)))

    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)))
    return jsonify(response)


@app.route("/api/events/rsvps")
def gather_all_rsvps():
    ''' All rsvps summarized '''
    events = Event.query.all()
    rsvps = build_rsvps_response(events)

    return jsonify(rsvps)


@app.route('/api/stories')
@app.route('/api/stories/<int:id>')
def get_stories(id=None):
    ''' Regular response option for stories.
    '''

    filters, querystring = get_query_params(request.args)

    if id:
        # Get one named story.
        filter = Story.id == id
        story = db.session.query(Story).filter(filter).first()
        if story:
            return jsonify(story.asdict(True))
        else:
            # If no story found
            return jsonify({"status": "Resource Not Found"}), 404

    # Get a bunch of stories.
    query = db.session.query(Story).order_by(desc(Story.id))

    for attr, value in filters.iteritems():
        if 'organization' in attr:
            org_attr = attr.split('_')[1]
            query = query.join(Story.organization).filter(getattr(Organization, org_attr).ilike(format_ilike_term(value)))
        else:
            query = query.filter(getattr(Story, attr).ilike(format_ilike_term(value)))

    response = paged_results(query=query, include_args=dict(include_organization=True), page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 25)), querystring=querystring)
    return jsonify(response)

# -------------------
# Routes
# -------------------


@app.route('/api/.well-known/status')
def well_known_status():
    ''' Return status information for Engine Light.

        http://engine-light.codeforamerica.org
    '''
    GITHUB_AUTH = None
    if 'GITHUB_TOKEN' in os.environ:
        GITHUB_AUTH = (os.environ['GITHUB_TOKEN'], '')

    MEETUP_KEY = None
    if 'MEETUP_KEY' in os.environ:
        MEETUP_KEY = os.environ['MEETUP_KEY']

    try:
        org = db.session.query(Organization).order_by(Organization.last_updated).limit(1).first()
        project = db.session.query(Project).limit(1).first()
        rate_limit = requests.get('https://api.github.com/rate_limit', auth=GITHUB_AUTH)
        remaining_github = rate_limit.json()['resources']['core']['remaining']
        recent_error = db.session.query(Error).order_by(desc(Error.time)).limit(1).first()

        meetup_status = "No Meetup key set"
        if MEETUP_KEY:
            meetup_url = 'https://api.meetup.com/status?format=json&key=' + MEETUP_KEY
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
                # is this really okay?
                status = 'ok'

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
    try:
        print "-> %s: %s" % ('request.base_url', request.base_url)
        print "-> %s: %s" % ('request.environ', request.environ)
        print "-> %s: %s" % ('request.headers', request.headers)
        print "-> %s: %s" % ('request.host_url', request.host_url)
        print "-> %s: %s" % ('request.is_secure', request.is_secure)
        print "-> %s: %s" % ('request.scheme', request.scheme)
        print "-> %s: %s" % ('request.url', request.url)
        print "-> %s: %s" % ('request.url_root', request.url_root)
    except:
        pass

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
    return jsonify({"status": "Resource Not Found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "Resource Not Found"}), 500

if __name__ == "__main__":
    manager.run()
