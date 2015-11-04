import os
import logging
from csv import DictReader
from itertools import groupby
from operator import itemgetter
from StringIO import StringIO
from datetime import datetime
from urllib2 import HTTPError, URLError
from urlparse import urlparse
from random import shuffle
from argparse import ArgumentParser
from time import time
from re import match, sub
from psycopg2 import connect, extras

from requests import get, exceptions
from dateutil.tz import tzoffset
import feedparser

from feeds import get_first_working_feed_link

from app import db, Project, Organization, Story, Event, Error, Issue, Label, Attendance
from utils import is_safe_name, safe_name, raw_name


# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

# :NOTE: debug
# import warnings
# warnings.filterwarnings('error')

# org sources filenames
ORG_SOURCES_FILENAME = 'org_sources.csv'
TEST_ORG_SOURCES_FILENAME = 'test_org_sources.csv'

# API URL templates
MEETUP_API_URL = "https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname={group_urlname}&key={key}"
GITHUB_USER_REPOS_API_URL = 'https://api.github.com/users/{username}/repos'
GITHUB_REPOS_API_URL = 'https://api.github.com/repos{repo_path}'
GITHUB_ISSUES_API_URL = 'https://api.github.com/repos{repo_path}/issues'
GITHUB_CONTENT_API_URL = 'https://api.github.com/repos{repo_path}/contents/{file_path}'

if 'GITHUB_TOKEN' in os.environ:
    github_auth = (os.environ['GITHUB_TOKEN'], '')
else:
    github_auth = None

if 'MEETUP_KEY' in os.environ:
    meetup_key = os.environ['MEETUP_KEY']
else:
    meetup_key = None

if 'PEOPLEDB' in os.environ:
    PEOPLEDB = os.environ["PEOPLEDB"]
else:
    PEOPLEDB = None

github_throttling = False

def get_github_api(url, headers=None):
    '''
        Make authenticated GitHub requests.
    '''
    logging.info('Asking Github for {}{}'.format(url, ' ({})'.format(headers) if headers and headers != {} else ''))

    got = get(url, auth=github_auth, headers=headers)

    return got

def format_date(time_in_milliseconds, utc_offset_msec):
    '''
        Create a datetime object from a time in milliseconds from the epoch
    '''
    tz = tzoffset(None, utc_offset_msec / 1000.0)
    dt = datetime.fromtimestamp(time_in_milliseconds / 1000.0, tz)
    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def format_location(venue):
    address = venue['address_1']
    if('address_2' in venue and venue['address_2'] != ''):
        address = address + ', ' + venue['address_2']

    if 'state' in venue:
        return "{address}, {city}, {state}, {country}".format(address=address, city=venue['city'], state=venue['state'], country=venue['country'])
    else:
        return "{address}, {city}, {country}".format(address=address, city=venue['city'], country=venue['country'])

def get_meetup_events(organization, group_urlname):
    '''
        Get events associated with a group
    '''
    meetup_url = MEETUP_API_URL.format(group_urlname=group_urlname, key=meetup_key)

    got = get(meetup_url)
    if got.status_code in range(400, 499):
        logging.error("%s's meetup page cannot be found" % organization.name)
        return []
    else:
        try:
            results = got.json()['results']
            events = []
            for event in results:
                event = dict(organization_name=organization.name,
                             name=event['name'],
                             event_url=event['event_url'],
                             start_time_notz=format_date(event['time'], event['utc_offset']),
                             created_at=format_date(event['created'], event['utc_offset']),
                             utc_offset=event['utc_offset'] / 1000.0,
                             rsvps=event['yes_rsvp_count'])

                # Some events don't have locations.
                if 'venue' in event:
                    event['location'] = format_location(event['venue'])

                events.append(event)
            return events
        except (TypeError, ValueError):
            return []


def get_meetup_count(organization, identifier):
    ''' Get the count of meetup members '''
    MEETUP_COUNT_API_URL = "https://api.meetup.com/2/groups?group_urlname={group_urlname}&key={key}"
    meetup_url = MEETUP_COUNT_API_URL.format(group_urlname=identifier, key=meetup_key)
    got = get(meetup_url)
    if got:
        response = got.json()
        if response:
            members = response["results"][0]["members"]
            organization.member_count = members
            db.session.commit()

def get_organizations(org_sources):
    ''' Collate all organizations from different sources.
    '''
    organizations = []
    with open(org_sources) as file:
        for org_source in file.read().splitlines():
            if 'docs.google.com' in org_source:
                organizations.extend(get_organizations_from_spreadsheet(org_source))

    return organizations

def get_organizations_from_spreadsheet(org_source):
    '''
        Get a row for each organization from the Brigade Info spreadsheet.
        Return a list of dictionaries, one for each row past the header.
    '''
    got = get(org_source)

    #
    # Requests response.text is a lying liar, with its UTF8 bytes as unicode()?
    # Use response.content to plain bytes, then decode everything.
    #
    organizations = list(DictReader(StringIO(got.content)))

    for (index, org) in enumerate(organizations):
        organizations[index] = dict([(k.decode('utf8'), v.decode('utf8'))
                                     for (k, v) in org.items()])

    return organizations

def get_stories(organization):
    ''' Get two recent stories from an rss feed.
    '''
    # If there is no given rss link, try the website url.
    if organization.rss:
        rss = organization.rss
    else:
        rss = organization.website

    # Extract a valid RSS feed from the URL
    try:
        url = get_first_working_feed_link(rss)

        # If no feed found then give up
        if not url:
            url = None
            return None
    except (HTTPError, ValueError, URLError):
        url = None
        return None

    try:
        logging.info('Asking cyberspace for ' + url)
        d = feedparser.parse(get(url).text)
    except (HTTPError, URLError, exceptions.SSLError):
        url = None
        return None

    #
    # Return dictionaries for the two most recent entries.
    #
    return [dict(title=e.title, link=e.link, type=u'blog', organization_name=organization.name)
            for e in d.entries[:2]]

def get_adjoined_json_lists(response, headers=None):
    ''' Github uses the Link header (RFC 5988) to do pagination.

        If we see a Link header, assume we're dealing with lists
        and concat them all together.
    '''
    result = response.json()

    if type(result) is list:
        while 'next' in response.links:
            response = get_github_api(response.links['next']['url'], headers=headers)
            result += response.json()

    return result


def get_projects(organization):
    '''
        Get a list of projects from CSV, TSV, JSON, or Github URL.
        Convert to a dict.
        TODO: Have this work for GDocs.
    '''

    # don't try to process an empty projects_list_url
    if not organization.projects_list_url:
        return []

    # If projects_list is a GitHub organization
    # Use the GitHub auth to request all the included repos.
    # Follow next page links
    _, host, path, _, _, _ = urlparse(organization.projects_list_url)
    matched = match(r'(/orgs)?/(?P<name>[^/]+)/?$', path)
    if host in ('www.github.com', 'github.com') and matched:
        projects_url = GITHUB_USER_REPOS_API_URL.format(username=matched.group('name'))

        try:
            response = get_github_api(projects_url)

            # Consider any status other than 2xx an error
            if not response.status_code // 100 == 2:
                return []

            projects = get_adjoined_json_lists(response)

        except exceptions.RequestException:
            # Something has gone wrong, probably a bad URL or site is down.
            return []

    # Else its a csv or json of projects
    else:
        projects_url = organization.projects_list_url
        logging.info('Asking for ' + projects_url)

        try:
            response = get(projects_url)

            # Consider any status other than 2xx an error
            if not response.status_code // 100 == 2:
                return []

            # If its a csv
            if "csv" in projects_url and (('content-type' in response.headers and 'text/csv' in response.headers['content-type']) or 'content-type' not in response.headers):
                data = response.content.splitlines()
                projects = list(DictReader(data, dialect='excel'))
                # convert all the values to unicode
                for project in projects:
                    for project_key, project_value in project.items():
                        if project_key:
                            project_key = project_key.lower()
                        # some values might be lists
                        if type(project_value) is list:
                            project_value = [unicode(item.decode('utf8')) for item in project_value]
                            project[project_key] = project_value
                        # some values might be empty strings
                        elif type(project_value) in (str, unicode) and unicode(project_value.decode('utf8')) == u'':
                            project[project_key] = None
                        else:
                            project[project_key] = unicode(project_value.decode('utf8'))

            # Else just grab it as json
            else:
                try:
                    projects = response.json()
                except ValueError:
                    # Not a json file.
                    return []

        except exceptions.RequestException:
            # Something has gone wrong, probably a bad URL or site is down.
            return []

    # If projects is just a list of GitHub urls, like Open Gov Hack Night
    # turn it into a list of dicts with minimal project information
    if len(projects) and type(projects[0]) in (str, unicode):
        projects = [dict(code_url=item, organization_name=organization.name) for item in projects]

    # If data is list of dicts, like BetaNYC or a GitHub org
    elif len(projects) and type(projects[0]) is dict:
        for project in projects:
            project['organization_name'] = organization.name
            if "homepage" in project:
                project["link_url"] = project["homepage"]
            if "html_url" in project:
                project["code_url"] = project["html_url"]
            for key in project.keys():
                if key not in ['name', 'description', 'link_url', 'code_url', 'type', 'categories', 'tags', 'organization_name', 'status']:
                    del project[key]

    # Get any updates on the projects
    projects = [update_project_info(proj) for proj in projects]

    # Drop projects with no updates
    projects = filter(None, projects)

    # Add organization names along the way.
    for project in projects:
            project['organization_name'] = organization.name

    return projects

def github_latest_update_time(github_details):
    ''' Issue 245 Choose most recent time for last_update from GitHub
        * pushed_at: time of last commit
        * updated_at: time of last repo object update
        * If neither of the above exists log an error and use current time
    '''
    import dateutil.parser

    datetime_format = '%a, %d %b %Y %H:%M:%S %Z'

    pushed_at = github_details['pushed_at'] if 'pushed_at' in github_details else None
    updated_at = github_details['updated_at'] if 'updated_at' in github_details else None

    latest_date = max(pushed_at, updated_at)

    if (latest_date):
        return dateutil.parser.parse(latest_date).strftime(datetime_format)
    else:
        logger.error("GitHub Project details has neither pushed_at or updated_at, using current time.")
        return datetime.now().strftime(datetime_format)

def non_github_project_update_time(project):
    ''' If its a non-github project, we should check if any of the fields
        have been updated, such as the description.

        Set the last_updated timestamp.
    '''
    filters = [Project.name == project['name'], Project.organization_name == project['organization_name']]
    existing_project = db.session.query(Project).filter(*filters).first()

    if existing_project:
        # project gets existing last_updated
        project['last_updated'] = existing_project.last_updated

        # unless one of the fields has been updated
        for key, value in project.iteritems():
            if project[key] != existing_project.__dict__[key]:
                project['last_updated'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z")

    else:
        # Set a date when we first see a non-github project
        project['last_updated'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z")

    return project

def update_project_info(project):
    ''' Update info from Github, if it's missing.

        Modify the project in-place and return nothing.

        Complete repository project details go into extras, for example
        project details from Github can be found under "github_details".

        Github_details is specifically expected to be used on this page:
        http://opengovhacknight.org/projects.html
    '''
    if 'code_url' not in project or not project['code_url']:
        project = non_github_project_update_time(project)
        return project

    _, host, path, _, _, _ = urlparse(project['code_url'])

    if host != 'github.com':
        project = non_github_project_update_time(project)
        return project

    # Get the Github attributes
    if host == 'github.com':
        path = sub(r"[\ /]+\s*$", "", path)
        repo_url = GITHUB_REPOS_API_URL.format(repo_path=path)

        # If we've hit the GitHub rate limit, skip updating projects.
        global github_throttling
        if github_throttling:
            return project

        # find an existing project, filtering on code_url, organization_name, and project name (if we know it)
        existing_filter = [Project.code_url == project['code_url'], Project.organization_name == project['organization_name']]
        if 'name' in project and project['name']:
            existing_filter.append(Project.name == project['name'])

        spreadsheet_is_updated = False

        existing_project = db.session.query(Project).filter(*existing_filter).first()
        if existing_project:
            # copy 'last_updated' values from the existing project to the project dict
            project['last_updated'] = existing_project.last_updated
            project['last_updated_issues'] = existing_project.last_updated_issues
            project['last_updated_civic_json'] = existing_project.last_updated_civic_json
            project['last_updated_root_files'] = existing_project.last_updated_root_files

            # check whether any of the org spreadsheet values for the project have changed
            for project_key in project:
                check_value = project[project_key]
                existing_value = existing_project.__dict__[project_key]
                if check_value and check_value != existing_value:
                    spreadsheet_is_updated = True
                elif not check_value and existing_value:
                    project[project_key] = existing_value

            # request project info from GitHub with the If-Modified-Since header
            if existing_project.last_updated:
                last_updated = datetime.strftime(existing_project.last_updated, "%a, %d %b %Y %H:%M:%S GMT")
                got = get_github_api(repo_url, headers={"If-Modified-Since": last_updated})

            # In rare cases, a project can be saved without a last_updated.
            else:
                got = get_github_api(repo_url)

        else:
            got = get_github_api(repo_url)

        if got.status_code in range(400, 499):
            if got.status_code == 404:
                logging.error(repo_url + ' doesn\'t exist.')
                # If its a bad GitHub link, don't return it at all.
                return None
            elif got.status_code == 403:
                logging.error("GitHub Rate Limit Remaining: " + str(got.headers["x-ratelimit-remaining"]))
                error_dict = {
                    "error": u'IOError: We done got throttled by GitHub',
                    "time": datetime.now()
                }
                new_error = Error(**error_dict)
                db.session.add(new_error)
                # commit the error
                db.session.commit()
                github_throttling = True
                return project

            else:
                raise IOError

        # If the project has not been modified...
        elif got.status_code == 304:
            logging.info('Project {} has not been modified since last update'.format(repo_url))

            # Populate values from the civic.json if it exists/is updated
            project, civic_json_is_updated = update_project_from_civic_json(project_dict=project, force=spreadsheet_is_updated)

            # if values have changed, copy untouched values from the existing project object and return it
            if spreadsheet_is_updated or civic_json_is_updated:
                logging.info('Project %s has been modified via spreadsheet or civic.json.', repo_url)
                project['last_updated'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z")
                project['github_details'] = existing_project.github_details
                return project

            # nothing was updated, but make sure we keep the project
            # :::here (project/true)
            existing_project.keep = True
            db.session.add(existing_project)
            # commit the project
            db.session.commit()
            return None

        all_github_attributes = got.json()
        github_details = {}
        for field in ('contributors_url', 'created_at', 'forks_count', 'homepage',
                      'html_url', 'id', 'open_issues', 'pushed_at',
                      'updated_at', 'watchers_count', 'name', 'description',
                      'stargazers_count', 'subscribers_count'):
            github_details[field] = all_github_attributes[field]

        github_details['owner'] = dict()

        for field in ('avatar_url', 'html_url', 'login', 'type'):
            github_details['owner'][field] = all_github_attributes['owner'][field]

        project['github_details'] = github_details

        if 'name' not in project or not project['name']:
            project['name'] = all_github_attributes['name']

        if 'description' not in project or not project['description']:
            project['description'] = all_github_attributes['description']

        if 'link_url' not in project or not project['link_url']:
            project['link_url'] = all_github_attributes['homepage']

        project['last_updated'] = github_latest_update_time(github_details)

        # Grab the list of project languages
        got = get_github_api(all_github_attributes['languages_url'])
        got = got.json()
        if got.keys():
            project['languages'] = got.keys()
        else:
            project['languages'] = None

        #
        # Populate project contributors from github_details[contributors_url]
        #
        project['github_details']['contributors'] = []
        got = get_github_api(all_github_attributes['contributors_url'])

        # Check if there are contributors
        try:
            for contributor in got.json():
                # we don't want people without email addresses?
                if contributor['login'] == 'invalid-email-address':
                    break

                project['github_details']['contributors'].append(dict())

                for field in ('login', 'url', 'avatar_url', 'html_url', 'contributions'):
                    project['github_details']['contributors'][-1][field] = contributor[field]

                # flag the owner with a boolean value
                project['github_details']['contributors'][-1]['owner'] \
                    = bool(contributor['login'] == project['github_details']['owner']['login'])
        except:
            pass

        #
        # Populate project participation from github_details[url] + "/stats/participation"
        # Sometimes GitHub returns a blank dict instead of no participation.
        #
        got = get_github_api(all_github_attributes['url'] + '/stats/participation')
        try:
            project['github_details']['participation'] = got.json()['all']
        except:
            project['github_details']['participation'] = [0] * 50

        #
        # Populate values from the civic.json if it exists/is updated
        #
        project, civic_json_is_updated = update_project_from_civic_json(project_dict=project, force=spreadsheet_is_updated)

    return project

def extract_tag_value(tag_candidate):
    ''' Extract the value of a tag from a string or object. tag_candidate must
        be in the form of either u'tag value' or {'tag': u'tag value'}
    '''
    if (type(tag_candidate) is str or type(tag_candidate) is unicode) and len(tag_candidate) > 0:
        # unicodeify
        tag_candidate = unicode(tag_candidate)
        # escape csv characters
        tag_candidate = sub(u'"', u'""', tag_candidate)
        tag_candidate = u'"{}"'.format(tag_candidate) if u',' in tag_candidate or u'"' in tag_candidate else tag_candidate

        return tag_candidate

    if type(tag_candidate) is dict and 'tag' in tag_candidate:
        return extract_tag_value(tag_candidate['tag'])

    return None

def get_tags_from_civic_json_object(tags_in):
    ''' Extract and return tags in the correct format from the passed object
    '''
    # the in object should be a list with something in it
    if type(tags_in) is not list or not len(tags_in):
        return None

    # get the tags
    extracted = [extract_tag_value(item) for item in tags_in]
    # strip None values
    stripped = [item for item in extracted if item is not None]
    # return as a string
    return u','.join(stripped) if len(stripped) else None

def update_project_from_civic_json(project_dict, force=False):
    ''' Update and return the passed project dict with values from civic.json
    '''
    civic_json = get_civic_json_for_project(project_dict, force)

    is_updated = False

    # get status
    existing_status = project_dict['status'] if 'status' in project_dict else None
    if 'status' in civic_json and existing_status != civic_json['status']:
        project_dict['status'] = civic_json['status'] if civic_json['status'].strip() else None
        is_updated = True

    # get tags
    existing_tags = project_dict['tags'] if 'tags' in project_dict else None
    civic_tags = get_tags_from_civic_json_object(civic_json['tags']) if 'tags' in civic_json else None
    if civic_tags and existing_tags != civic_tags:
        project_dict['tags'] = civic_tags
        is_updated = True

    # add other attributes from civic.json here

    return project_dict, is_updated

def get_issues_for_project(project):
    ''' get the issues for a single project in dict format
        without touching the database (used for testing)
    '''
    issues = []

    if not project.code_url:
        return issues

    # Get github issues api url
    _, host, path, _, _, _ = urlparse(project.code_url)
    path = sub(r"[\ /]+\s*$", "", path)
    issues_url = GITHUB_ISSUES_API_URL.format(repo_path=path)

    # Ping github's api for project issues
    got = get_github_api(issues_url, headers={'If-None-Match': project.last_updated_issues})

    # Save each issue in response
    responses = get_adjoined_json_lists(got, headers={'If-None-Match': project.last_updated_issues})
    for issue in responses:
        # Type check the issue, we are expecting a dictionary
        if isinstance(issue, dict):
            # Pull requests are returned along with issues. Skip them.
            if "/pull/" in issue['html_url']:
                continue
            issue_dict = dict(title=issue['title'], html_url=issue['html_url'],
                              body=issue['body'], project_id=project.id, labels=issue['labels'],
                              created_at=issue['created_at'], updated_at=issue['updated_at'])
            issues.append(issue_dict)
        else:
            logging.error('Issue for project %s is not a dictionary', project.name)

    return issues

def get_issues(org_name):
    '''
        Get github issues associated to each Organization's Projects.
    '''
    issues = []

    # Only grab this organization's projects
    projects = db.session.query(Project).filter(Project.organization_name == org_name).all()

    # Populate issues for each project
    for project in projects:
        # Mark this project's issues for deletion
        # :::here (issue/false)
        db.session.execute(db.update(Issue, values={'keep': False}).where(Issue.project_id == project.id))

        # don't try to parse an empty code_url
        if not project.code_url:
            continue

        # Get github issues api url
        _, host, path, _, _, _ = urlparse(project.code_url)

        # Only check issues if its a github project
        if host != 'github.com':
            continue

        path = sub(r"[\ /]+\s*$", "", path)
        issues_url = GITHUB_ISSUES_API_URL.format(repo_path=path)

        # Ping github's api for project issues
        # :TODO: non-github projects are hitting here and shouldn't be!
        got = get_github_api(issues_url, headers={'If-None-Match': project.last_updated_issues})

        # Verify that content has not been modified since last run
        if got.status_code == 304:
            # :::here (issue/true)
            db.session.execute(db.update(Issue, values={'keep': True}).where(Issue.project_id == project.id))
            logging.info('Issues %s have not changed since last update', issues_url)

        elif got.status_code not in range(400, 499):
            # Update project's last_updated_issue field
            project.last_updated_issues = unicode(got.headers['ETag'])
            db.session.add(project)

            responses = get_adjoined_json_lists(got, headers={'If-None-Match': project.last_updated_issues})

            # Save each issue in response
            for issue in responses:
                # Type check the issue, we are expecting a dictionary
                if isinstance(issue, dict):
                    # Pull requests are returned along with issues. Skip them.
                    if "/pull/" in issue['html_url']:
                        continue
                    issue_dict = dict(title=issue['title'], html_url=issue['html_url'],
                                      body=issue['body'], project_id=project.id, labels=issue['labels'],
                                      created_at=issue['created_at'], updated_at=issue['updated_at'])
                    issues.append(issue_dict)
                else:
                    logging.error('Issue for project %s is not a dictionary', project.name)
    return issues

def get_root_directory_listing_for_project(project_dict, force=False):
    ''' Get a listing of the project's github repo root directory. Will return
        an empty list if the listing hasn't changed since the last time we asked
        unless force is True.
    '''
    listing = []

    if 'code_url' not in project_dict or not project_dict['code_url']:
        return listing

    # Get the API URL
    _, host, path, _, _, _ = urlparse(project_dict['code_url'])
    path = sub(r"[\ /]+\s*$", "", path)
    directory_url = GITHUB_CONTENT_API_URL.format(repo_path=path, file_path='')

    # Request the directory listing
    request_headers = {}
    if 'last_updated_root_files' in project_dict and not force:
        request_headers['If-None-Match'] = project_dict['last_updated_root_files']
    got = get_github_api(directory_url, headers=request_headers)

    # Verify that content has not been modified since last run
    if got.status_code == 304:
        logging.info('root directory listing has not changed since last update for {}'.format(directory_url))

    elif got.status_code not in range(400, 499):
        logging.info('root directory listing has changed for {}'.format(directory_url))
        # Update the project's last_updated_root_files field
        project_dict['last_updated_root_files'] = unicode(got.headers['ETag'])
        # get the contents of the file
        listing = got.json()

    else:
        logging.info('NO root directory listing found for {}'.format(directory_url))

    return listing

def get_civic_json_exists_for_project(project_dict, force=False):
    ''' Return True if the passed project has a civic.json file in its root directory.
    '''
    directory_listing = get_root_directory_listing_for_project(project_dict, force)
    exists = 'civic.json' in [item['name'] for item in directory_listing]
    return exists

def get_civic_json_for_project(project_dict, force=False):
    ''' Get the contents of the civic.json at the project's github repo root, if it exists.
    '''
    civic = {}

    # return an empty dict if civic.json doesn't exist (or hasn't been updated)
    if not get_civic_json_exists_for_project(project_dict, force):
        return civic

    # Get the API URL (if 'code_url' wasn't in project_dict, it would've been caught upstream)
    _, host, path, _, _, _ = urlparse(project_dict['code_url'])
    path = sub(r"[\ /]+\s*$", "", path)
    civic_url = GITHUB_CONTENT_API_URL.format(repo_path=path, file_path='civic.json')

    # Request the contents of the civic.json file
    # without the 'Accept' header we'd get information about the
    # file rather than the contents of the file
    request_headers = {'Accept': 'application/vnd.github.v3.raw'}
    if 'last_updated_civic_json' in project_dict and not force:
        request_headers['If-None-Match'] = project_dict['last_updated_civic_json']
    got = get_github_api(civic_url, headers=request_headers)

    # Verify that content has not been modified since last run
    if got.status_code == 304:
        logging.info('Unchanged civic.json at {}'.format(civic_url))

    elif got.status_code not in range(400, 499):
        logging.info('New civic.json at {}'.format(civic_url))
        # Update the project's last_updated_civic_json field
        project_dict['last_updated_civic_json'] = unicode(got.headers['ETag'])
        try:
            # get the contents of the file
            civic = got.json()
        except ValueError:
            logging.error('Malformed civic.json at {}'.format(civic_url))

    else:
        logging.info('No civic.json at {}'.format(civic_url))

    return civic

def count_people_totals(all_projects):
    ''' Create a list of people details based on project details.

        Request additional data from Github API for each person.

        See discussion at
        https://github.com/codeforamerica/civic-json-worker/issues/18
    '''
    users, contributors = [], []
    for project in all_projects:
        contributors.extend(project['contributors'])

    #
    # Sort by login; there will be duplicates!
    #
    contributors.sort(key=itemgetter('login'))

    #
    # Populate users array with groups of contributors.
    #
    for (_, _contributors) in groupby(contributors, key=itemgetter('login')):
        user = dict(contributions=0, repositories=0)

        for contributor in _contributors:
            user['contributions'] += contributor['contributions']
            user['repositories'] += 1

            if 'login' in user:
                continue

            #
            # Populate user hash with Github info, if it hasn't been already.
            #
            got = get_github_api(contributor['url'])
            contributor = got.json()

            for field in (
                    'login', 'avatar_url', 'html_url',
                    'blog', 'company', 'location'):
                user[field] = contributor.get(field, None)

        users.append(user)

    return users

def save_organization_info(session, org_dict):
    ''' Save a dictionary of organization info to the datastore session.

        Return an app.Organization instance.
    '''
    # Select an existing organization by name.
    filter = Organization.name == org_dict['name']
    existing_org = session.query(Organization).filter(filter).first()

    # :::here (organization/true)
    # If this is a new organization, save and return it. The keep parameter is True by default.
    if not existing_org:
        new_organization = Organization(**org_dict)
        session.add(new_organization)
        return new_organization

    # Check that the id exists
    if not existing_org.id:
        existing_org.id = safe_name(raw_name(existing_org.name))

    # Timestamp the existing organization
    existing_org.last_updated = time()
    # :::here (organization/true)
    existing_org.keep = True

    # Update existing organization details.
    for (field, value) in org_dict.items():
        setattr(existing_org, field, value)

    return existing_org

def save_project_info(session, proj_dict):
    ''' Save a dictionary of project info to the datastore session.

        Return an app.Project instance.
    '''
    # Select the current project, filtering on name AND organization.
    filter = Project.name == proj_dict['name'], Project.organization_name == proj_dict['organization_name']
    existing_project = session.query(Project).filter(*filter).first()

    # If this is a new project, save and return it.
    if not existing_project:
        new_project = Project(**proj_dict)
        session.add(new_project)
        return new_project

    # Preserve the existing project
    # :::here (project/true)
    existing_project.keep = True

    # Update existing project details
    for (field, value) in proj_dict.items():
        setattr(existing_project, field, value)

    return existing_project

def save_issue(session, issue):
    '''
        Save a dictionary of issue info to the datastore session.
        Return an app.Issue instance
    '''
    # Select the current issue, filtering on title AND project_id.
    filter = Issue.title == issue['title'], Issue.project_id == issue['project_id']
    existing_issue = session.query(Issue).filter(*filter).first()

    # If this is a new issue save it
    if not existing_issue:
        new_issue = Issue(**issue)
        session.add(new_issue)
    else:
        # Preserve the existing issue.
        # :::here (issue/true)
        existing_issue.keep = True
        # Update existing issue details
        existing_issue.title = issue['title']
        existing_issue.body = issue['body']
        existing_issue.html_url = issue['html_url']
        existing_issue.project_id = issue['project_id']

def save_labels(session, issue):
    '''
        Save labels to issues
    '''
    # Select the current issue, filtering on title AND project_id.
    filter = Issue.title == issue['title'], Issue.project_id == issue['project_id']
    existing_issue = session.query(Issue).filter(*filter).first()

    # Get list of existing and incoming label names (dupes will be filtered out in comparison process)
    existing_label_names = [label.name for label in existing_issue.labels]
    incoming_label_names = [label['name'] for label in issue['labels']]

    # Add labels that are in the incoming list and not the existing list
    add_label_names = list(set(incoming_label_names) - set(existing_label_names))
    for label_dict in issue['labels']:
        if label_dict['name'] in add_label_names:
            # add the issue id to the labels
            label_dict["issue_id"] = existing_issue.id
            new_label = Label(**label_dict)
            session.add(new_label)

    # Delete labels that are not in the incoming list but are in the existing list
    delete_label_names = list(set(existing_label_names) - set(incoming_label_names))
    for label_name in delete_label_names:
        session.query(Label).filter(Label.issue_id == existing_issue.id, Label.name == label_name).delete()

def save_event_info(session, event_dict):
    '''
        Save a dictionary of event into to the datastore session then return
        that event instance
    '''
    # Select the current event, filtering on event_url and organization name.
    filter = Event.event_url == event_dict['event_url'], \
        Event.organization_name == event_dict['organization_name']
    existing_event = session.query(Event).filter(*filter).first()

    # If this is a new event, save and return it.
    if not existing_event:
        new_event = Event(**event_dict)
        session.add(new_event)
        return new_event

    # Preserve the existing event.
    # :::here (event/true)
    existing_event.keep = True

    # Update existing event details
    for (field, value) in event_dict.items():
        setattr(existing_event, field, value)

def save_story_info(session, story_dict):
    '''
        Save a dictionary of story into to the datastore session then return
        that story instance
    '''
    # Select the current story, filtering on link and organization name.
    filter = Story.organization_name == story_dict['organization_name'], \
        Story.link == story_dict['link']

    existing_story = session.query(Story).filter(*filter).first()

    # If this is a new story, save and return it.
    if not existing_story:
        new_story = Story(**story_dict)
        session.add(new_story)
        return new_story

    # Preserve the existing story.
    # :::here (story/true)
    existing_story.keep = True

    # Update existing story details
    for (field, value) in story_dict.items():
        setattr(existing_story, field, value)

def get_event_group_identifier(events_url):
    parse_result = urlparse(events_url)
    url_parts = parse_result.path.split('/')
    identifier = url_parts.pop()
    if not identifier:
        identifier = url_parts.pop()
    if(match('^[A-Za-z0-9-]+$', identifier)):
        return identifier
    else:
        return None


def get_attendance(peopledb, organization_url, organization_name):
    ''' Get the attendance of an org from the peopledb '''

    # Total attendance
    q = ''' SELECT COUNT(*) AS total FROM attendance
            WHERE organization_url = %s '''
    peopledb.execute(q, (organization_url,))
    total = int(peopledb.fetchone()["total"])

    # weekly attendance
    q = ''' SELECT COUNT(*) AS total,
            to_char(datetime, 'YYYY WW') AS week
            FROM attendance
            WHERE organization_url = %s
            GROUP BY week '''
    peopledb.execute(q, (organization_url,))
    weekly = peopledb.fetchall()
    weekly = {week["week"]: int(week["total"]) for week in weekly}

    this_week = datetime.strftime(datetime.now(), "%Y %U")
    if this_week not in weekly.keys():
        weekly[this_week] = 0

    attendance = {
        "organization_name": organization_name,
        "organization_url": organization_url,
        "total": total,
        "weekly": weekly
    }

    return attendance

def update_attendance(db, organization_name, attendance):
    ''' Update exisiting attendance '''
    filter = Attendance.organization_name == organization_name
    existing_attendance = db.session.query(Attendance).filter(filter).first()
    if existing_attendance:
        existing_attendance.total = attendance["total"]
        existing_attendance.weekly = attendance["weekly"]
        db.session.add(existing_attendance)
    else:
        new_att = Attendance(**attendance)
        db.session.add(new_att)
    db.session.commit()


def main(org_name=None, org_sources=None):
    ''' Run update over all organizations. Optionally, update just one.
    '''
    # set org_sources
    org_sources = org_sources or ORG_SOURCES_FILENAME

    # Collect a set of fresh organization names.
    organization_names = set()

    # Retrieve all organizations and shuffle the list in place.
    orgs_info = get_organizations(org_sources)
    shuffle(orgs_info)

    if org_name:
        orgs_info = [org for org in orgs_info if org['name'] == org_name]

    # Iterate over organizations and projects, saving them to db.session.
    for org_info in orgs_info:

        if not is_safe_name(org_info['name']):
            error_dict = {
                "error": unicode('ValueError: Bad organization name: "%s"' % org_info['name']),
                "time": datetime.now()
            }
            new_error = Error(**error_dict)
            db.session.add(new_error)
            # commit the error
            db.session.commit()
            continue

        try:
            filter = Organization.name == org_info['name']
            existing_org = db.session.query(Organization).filter(filter).first()
            organization_names.add(org_info['name'])

            # Mark everything associated with this organization for deletion at first.
            # :::here (event/false, story/false, project/false, organization/false)
            db.session.execute(db.update(Event, values={'keep': False}).where(Event.organization_name == org_info['name']))
            db.session.execute(db.update(Story, values={'keep': False}).where(Story.organization_name == org_info['name']))
            db.session.execute(db.update(Project, values={'keep': False}).where(Project.organization_name == org_info['name']))
            db.session.execute(db.update(Organization, values={'keep': False}).where(Organization.name == org_info['name']))
            # commit the false keeps
            db.session.commit()

            # Empty lat longs are okay.
            if 'latitude' in org_info:
                if not org_info['latitude']:
                    org_info['latitude'] = None
            if 'longitude' in org_info:
                if not org_info['longitude']:
                    org_info['longitude'] = None

            organization = save_organization_info(db.session, org_info)

            organization_names.add(organization.name)
            # flush the organization
            db.session.flush()

            if organization.rss or organization.website:
                logging.info("Gathering all of %s's stories." % organization.name)
                stories = get_stories(organization)
                if stories:
                    for story_info in stories:
                        save_story_info(db.session, story_info)
                    # flush the stories
                    db.session.flush()

            if organization.projects_list_url:
                logging.info("Gathering all of %s's projects." % organization.name)
                projects = get_projects(organization)
                for proj_dict in projects:
                    save_project_info(db.session, proj_dict)
                # flush the projects
                db.session.flush()

            if organization.events_url:
                if not meetup_key:
                    logging.error("No Meetup.com key set.")
                if 'meetup.com' not in organization.events_url:
                    logging.error("Only Meetup.com events work right now.")
                else:
                    logging.info("Gathering all of %s's events." % organization.name)
                    identifier = get_event_group_identifier(organization.events_url)
                    if identifier:
                        for event in get_meetup_events(organization, identifier):
                            save_event_info(db.session, event)
                        # flush the events
                        db.session.flush()

                        # Get Meetup member count
                        get_meetup_count(organization, identifier)

                    else:
                        logging.error("%s does not have a valid events url" % organization.name)

            # Get issues for all of the projects
            logging.info("Gathering all of %s's open GitHub issues." % organization.name)
            issues = get_issues(organization.name)
            for issue in issues:
                save_issue(db.session, issue)

            # flush the issues
            db.session.flush()
            for issue in issues:
                save_labels(db.session, issue)

            # Get attendance data
            with connect(PEOPLEDB) as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as peopledb:
                    cfapi_url = "https://www.codeforamerica.org/api/organizations/"
                    organization_url = cfapi_url + organization.api_id()
                    attendance = get_attendance(peopledb, organization_url, organization.name)

            if attendance:
                update_attendance(db, organization.name, attendance)

            # commit everything
            db.session.commit()

            # Remove everything marked for deletion.
            # :::here (event/delete, story/delete, project/delete, issue/delete, organization/delete)
            db.session.query(Event).filter(Event.keep == False).delete()
            db.session.query(Story).filter(Story.keep == False).delete()
            db.session.query(Issue).filter(Issue.keep == False).delete()
            db.session.query(Project).filter(Project.keep == False).delete()
            db.session.query(Organization).filter(Organization.keep == False).delete()
            # commit objects deleted for keep=False
            db.session.commit()

        except:
            # Raise the error, get out of main(), and don't commit the transaction.
            raise

        else:
            # Commit and move on to the next organization.
            # final commit before moving on to the next organization
            db.session.commit()

    # prune orphaned organizations if no organization name was passed
    if not org_name:
        for bad_org in db.session.query(Organization):
            if bad_org.name in organization_names:
                continue

            # delete orphaned organizations, all other deletions will cascade
            db.session.execute(db.delete(Organization).where(Organization.name == bad_org.name))
            # commit for deleting orphaned organizations
            db.session.commit()

parser = ArgumentParser(description='''Update database from CSV source URL.''')
parser.add_argument('--name', dest='name', help='Single organization name to update.')
parser.add_argument('--test', action='store_const', dest='org_sources', const=TEST_ORG_SOURCES_FILENAME, help='Use the testing list of organizations.')

if __name__ == "__main__":
    args = parser.parse_args()
    org_name = args.name and args.name.decode('utf8') or ''
    main(org_name=org_name, org_sources=args.org_sources)
