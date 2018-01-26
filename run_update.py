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


from dateutil.tz import tzoffset
import feedparser
import json
from raven import Client as SentryClient
from requests import get, exceptions


from app import db, Project, Organization, Story, Event, Error, Issue, Label, Attendance
from feeds import get_first_working_feed_link
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
# TODO: use a Meetup client library with pagination
MEETUP_API_URL = "https://api.meetup.com/2/events?status=past,upcoming&format=json&group_urlname={group_urlname}&key={key}&desc=true&page=200"
MEETUP_COUNT_API_URL = "https://api.meetup.com/2/groups?group_urlname={group_urlname}&key={key}"
GITHUB_USER_API_URL = 'https://api.github.com/users/{username}'
GITHUB_USER_REPOS_API_URL = 'https://api.github.com/users/{username}/repos'
GITHUB_REPOS_API_URL = 'https://api.github.com/repos{repo_path}'
GITHUB_ISSUES_API_URL = 'https://api.github.com/repos{repo_path}/issues'
GITHUB_CONTENT_API_URL = 'https://api.github.com/repos{repo_path}/contents/{file_path}'
GITHUB_COMMIT_STATUS_URL = 'https://api.github.com/repos{repo_path}/commits/{default_branch}/status'

GITHUB_AUTH = None
if 'GITHUB_TOKEN' in os.environ:
    GITHUB_AUTH = (os.environ['GITHUB_TOKEN'], '')

MEETUP_KEY = None
if 'MEETUP_KEY' in os.environ:
    MEETUP_KEY = os.environ['MEETUP_KEY']

SENTRY = None
if 'SENTRY_DSN' in os.environ:
    SENTRY = SentryClient(os.environ['SENTRY_DSN'])


GITHUB_THROTTLING = False


def get_github_api(url, headers=None):
    '''
        Make authenticated GitHub requests.
    '''
    global GITHUB_THROTTLING
    got = get(url, auth=GITHUB_AUTH, headers=headers)

    limit_hit, remaining = get_hit_github_ratelimit(got.headers)
    logging.info(u'-{}- Asked Github for {}{}'.format(remaining, url, u' ({})'.format(headers) if headers and headers != {} else u''))

    # check for throttling
    if got.status_code == 403 and limit_hit:
        # we've been throttled
        GITHUB_THROTTLING = True

        # log the error
        logging.error(u"GitHub Rate Limit Remaining: {}".format(got.headers["X-Ratelimit-Remaining"]))

        # save the error in the db
        error_dict = {
            "error": u'IOError: We done got throttled by GitHub',
            "time": datetime.now()
        }
        new_error = Error(**error_dict)
        # commit the error
        db.session.add(new_error)
        db.session.commit()

    return got

def get_hit_github_ratelimit(headers):
    ''' Return True if we've hit the GitHub rate limit,
        False if we haven't or if we can't figure it out.
        Also return the remaining requests reported by GitHub.
    '''
    try:
        remaining_str = headers['X-Ratelimit-Remaining']
    except KeyError:
        # no header by that name
        return False, 0

    try:
        remaining_int = int(remaining_str)
    except ValueError:
        # value can't be converted into an integer
        return False, 0

    # return True if we've hit the limit
    return remaining_int <= 0, remaining_int

def format_date(time_in_milliseconds, utc_offset_msec):
    '''
        Create a datetime object from a time in milliseconds from the epoch
    '''
    tz = tzoffset(None, utc_offset_msec / 1000.0)
    dt = datetime.fromtimestamp(time_in_milliseconds / 1000.0, tz)
    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def format_location(venue):
    address = venue['address_1']
    if 'address_2' in venue and venue['address_2'] != '':
        address = address + ', ' + venue['address_2']

    return u'{name}\n{address}'.format(name=venue['name'], address=address)


def get_meetup_events(organization, group_urlname):
    ''' Get events associated with a group
    '''
    events = []

    if not MEETUP_KEY:
        logging.error("No meetup.com key set.")
        return events

    meetup_url = MEETUP_API_URL.format(group_urlname=group_urlname, key=MEETUP_KEY)

    got = get(meetup_url)
    if got.status_code in range(400, 499):
        logging.error(u"{}'s meetup page cannot be found".format(organization.name))
        return events
    else:
        try:
            results = got.json()['results']
            for event in results:
                eventdict = dict(
                    organization_name=organization.name,
                    name=event['name'],
                    event_url=event['event_url'],
                    start_time_notz=format_date(event['time'], event['utc_offset']),
                    created_at=format_date(event['created'], event['utc_offset']),
                    utc_offset=event['utc_offset'] / 1000.0,
                    rsvps=event['yes_rsvp_count'],
                    description=event.get('description')
                )

                # Some events don't have locations.
                if 'venue' in event:
                    eventdict['location'] = format_location(event['venue'])
                    eventdict['lat'] = event['venue']['lat']
                    eventdict['lon'] = event['venue']['lon']

                events.append(eventdict)
            return events
        except (TypeError, ValueError):
            return events


def get_meetup_count(organization, identifier):
    ''' Get the count of meetup members
    '''
    meetup_url = MEETUP_COUNT_API_URL.format(group_urlname=identifier, key=MEETUP_KEY)
    got = get(meetup_url)
    members = None
    if got and got.status_code // 100 == 2:
        try:
            response = got.json()
            if response:
                if response["results"]:
                    members = response["results"][0]["members"]
        except ValueError:  # meetup API returned non-JSON response
            return None

    return members


def get_organizations(org_sources):
    ''' Collate all organizations from different sources.
    '''
    organizations = []
    with open(org_sources) as file:
        for org_source in file.read().splitlines():
            scheme, netloc, path, _, _, _ = urlparse(org_source)
            is_json = os.path.splitext(path)[1] == '.json'
            # if it's a local file...
            if not scheme and not netloc:
                if is_json:
                    organizations.extend(get_organizations_from_local_json(org_source))
                else:
                    organizations.extend(get_organizations_from_local_csv(org_source))
            elif is_json:
                organizations.extend(get_organizations_from_json(org_source))
            elif 'docs.google.com' in org_source:
                organizations.extend(get_organizations_from_spreadsheet(org_source))

    return organizations


def get_organizations_from_json(org_source):
    ''' Get a row for each organization from a remote JSON file.
    '''
    got = get(org_source)
    return got.json()


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
    return decode_organizations_list(organizations)


def get_organizations_from_local_csv(org_source):
    ''' Get a row for each organization from a local CSV file.
        Return a list of dictionaries, one for each row past the header.
    '''
    organizations = list(DictReader(open(org_source, 'rb')))
    return decode_organizations_list(organizations)


def get_organizations_from_local_json(org_source):
    ''' Get a row for each organization from a local JSON file.
        Return a list of dictionaries, one for each row past the header.
    '''
    with open(org_source, 'rb') as org_data:
        organizations = json.load(org_data)
    return organizations

def decode_organizations_list(organizations):
    '''
        Decode keys and values in a list of organizations
    '''
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

    stories = []

    # Extract a valid RSS feed from the URL
    try:
        url = get_first_working_feed_link(rss)

        # If no feed found then give up
        if not url:
            return stories

    except (HTTPError, ValueError, URLError):
        return stories

    try:
        logging.info('Asking cyberspace for ' + url)
        d = feedparser.parse(get(url).text)

    except (HTTPError, URLError, exceptions.SSLError):
        return stories

    #
    # Return dictionaries for the two most recent entries.
    #
    stories = [dict(title=e.title, link=e.link, type=u'blog', organization_name=organization.name) for e in d.entries[:2]]
    return stories


def get_adjoined_json_lists(response, headers=None):
    ''' Github uses the Link header (RFC 5988) to do pagination.

        If we see a Link header, assume we're dealing with lists
        and concat them all together.
    '''
    result = response.json()

    status_code = response.status_code
    if type(result) is list:
        while 'next' in response.links:
            response = get_github_api(response.links['next']['url'], headers=headers)
            status_code = response.status_code
            # Consider any status other than 2xx an error
            if not status_code // 100 == 2:
                break
            result += response.json()

    return result, status_code


def parse_github_user(url):
    ''' given a URL, returns the github username or None if it is not a Github URL '''
    _, host, path, _, _, _ = urlparse(url)
    matched = match(r'(/orgs)?/(?P<name>[^/]+)/?$', path)
    if host in ('www.github.com', 'github.com') and matched:
        return matched.group('name')


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
    github_username = parse_github_user(organization.projects_list_url)
    if github_username:
        projects_url = GITHUB_USER_REPOS_API_URL.format(username=github_username)

        try:
            got = get_github_api(projects_url)

            # Consider any status other than 2xx an error
            if not got.status_code // 100 == 2:
                return []

            projects, _ = get_adjoined_json_lists(got)

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
                        # we want tags to be a list with no whitespace
                        elif project_key == 'tags':
                            project_value = unicode(project_value.decode('utf8'))
                            project[project_key] = [tag.strip() for tag in project_value.split(',')]
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


def make_root_github_project_path(path):
    ''' Strip anything extra off the end of a github path
    '''
    path_split = path.split('/')
    path = '/'.join(path_split[0:3])
    # some URLs have been passed to us with '.git' at the end
    path = sub(ur'\.git$', '', path)
    return path


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
        path = sub(r"[\s\/]+?$", "", path)
        # make sure we're working with the main github URL
        path = make_root_github_project_path(path)
        repo_url = GITHUB_REPOS_API_URL.format(repo_path=path)

        # find an existing project, filtering on code_url, organization_name, and project name (if we know it)
        existing_filter = [Project.code_url == project['code_url'], Project.organization_name == project['organization_name']]
        if 'name' in project and project['name']:
            existing_filter.append(Project.name == project['name'])

        existing_project = db.session.query(Project).filter(*existing_filter).first()

        # if we're throttled, make sure an existing project is kept and return none
        if GITHUB_THROTTLING:
            if existing_project:
                # :::here (project/true)
                existing_project.keep = True
                # commit the project
                db.session.commit()
            return None

        # keep track of org spreadsheet values
        spreadsheet_is_updated = False

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
                    project[project_key] = check_value
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
                # It's a bad GitHub link
                logging.error(u"{} doesn't exist.".format(repo_url))
                # If there's an existing project in the database, get rid of it
                if existing_project:
                    # this is redundant, but let's make sure
                    # :::here (project/false)
                    existing_project.keep = False
                    db.session.commit()
                # Take the project out of the loop by returning None
                return None

            elif got.status_code == 403:
                # Throttled by GitHub
                if existing_project:
                    # :::here (project/true)
                    existing_project.keep = True
                    # commit the project
                    db.session.commit()
                return None

            else:
                raise IOError

        # If the project has not been modified...
        elif got.status_code == 304:
            logging.info(u'Project {} has not been modified since last update'.format(repo_url))

            # if values have changed, copy untouched values from the existing project object and return it
            if spreadsheet_is_updated:
                logging.info('Project %s has been modified via spreadsheet.', repo_url)
                project['github_details'] = existing_project.github_details
                return project

            # nothing was updated, but make sure we keep the project
            # :::here (project/true)
            existing_project.keep = True
            # commit the project
            db.session.commit()
            return None

        # the project has been modified
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
        languages_json = got.json()
        if got.status_code // 100 == 2 and languages_json.keys():
            project['languages'] = languages_json.keys()
        else:
            project['languages'] = None

        #
        # Populate project contributors from github_details[contributors_url]
        #
        project['github_details']['contributors'] = []
        got = get_github_api(all_github_attributes['contributors_url'])
        try:
            contributors_json = got.json()
            for contributor in contributors_json:
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
            participation_json = got.json()
            project['github_details']['participation'] = participation_json['all']
        except:
            project['github_details']['participation'] = [0] * 50

        #
        # Populate values from the civic.json if it exists/is updated
        #
        project, civic_json_is_updated = update_project_from_civic_json(project_dict=project, force=spreadsheet_is_updated)

        # Get the lastest commit status
        # First build up the url to use
        if "default_branch" in all_github_attributes:
            commit_status_url = GITHUB_COMMIT_STATUS_URL.format(repo_path=path, default_branch=all_github_attributes['default_branch'])
            got = get_github_api(commit_status_url)
            project["commit_status"] = got.json().get('state', None)

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
    # strip None values and return as a list
    return [item for item in extracted if item is not None]


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
    path = sub(r"[\s\/]+?$", "", path)
    # make sure we're working with the main github URL
    path = make_root_github_project_path(path)
    issues_url = GITHUB_ISSUES_API_URL.format(repo_path=path)

    # Ping github's api for project issues
    got = get_github_api(issues_url, headers={'If-None-Match': project.last_updated_issues})
    if got.status_code // 100 != 2:
        return issues

    # Save each issue in response
    responses, _ = get_adjoined_json_lists(got, headers={'If-None-Match': project.last_updated_issues})
    for issue in responses:
        # Type check the issue, we are expecting a dictionary
        if isinstance(issue, dict):
            # Pull requests are returned along with issues. Skip them.
            if "/pull/" in issue['html_url']:
                continue

            issue_dict = dict(project_id=project.id)
            for field in (
                    'title', 'html_url', 'body',
                    'labels', 'created_at', 'updated_at'):
                issue_dict[field] = issue.get(field, None)

            issues.append(issue_dict)
        else:
            logging.error('Issue for project %s is not a dictionary', project.name)

    return issues


def get_issues(project):
    ''' Get github issues associated with the passed Project.
    '''
    issues = []

    # don't try to parse an empty code_url
    if not project.code_url:
        return issues

    # Mark this project's issues for deletion
    # :::here (issue/false)
    db.session.execute(db.update(Issue, values={'keep': False}).where(Issue.project_id == project.id))

    # Get github issues api url
    _, host, path, _, _, _ = urlparse(project.code_url)

    # Only check issues if its a github project
    if host != 'github.com':
        return issues

    path = sub(r"[\s\/]+?$", "", path)
    # make sure we're working with the main github URL
    path = make_root_github_project_path(path)
    issues_url = GITHUB_ISSUES_API_URL.format(repo_path=path)

    # Ping github's api for project issues
    # :TODO: non-github projects are hitting here and shouldn't be!
    got = get_github_api(issues_url, headers={'If-None-Match': project.last_updated_issues})

    # A 304 means that issues have not been modified since we last checked
    if got.status_code == 304:
        # :::here (issue/true)
        db.session.execute(db.update(Issue, values={'keep': True}).where(Issue.project_id == project.id))
        logging.info('Issues %s have not changed since last update', issues_url)

    elif got.status_code not in range(400, 499):
        # Update the project's last_updated_issue field
        project.last_updated_issues = unicode(got.headers['ETag'])
        db.session.add(project)

        # Get all the pages of issues
        responses, _ = get_adjoined_json_lists(got)

        # Save each issue in response
        for issue in responses:
            # Type check the issue, we are expecting a dictionary
            if isinstance(issue, dict):
                # Pull requests are returned along with issues. Skip them.
                if "/pull/" in issue['html_url']:
                    continue

                issue_dict = dict(project_id=project.id)
                for field in (
                        'title', 'html_url', 'body',
                        'labels', 'created_at', 'updated_at'):
                    issue_dict[field] = issue.get(field, None)

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
    path = sub(r"[\s\/]+?$", "", path)
    # make sure we're working with the main github URL
    path = make_root_github_project_path(path)
    directory_url = GITHUB_CONTENT_API_URL.format(repo_path=path, file_path='')

    # Request the directory listing
    request_headers = {}
    if 'last_updated_root_files' in project_dict and not force:
        request_headers['If-None-Match'] = project_dict['last_updated_root_files']
    got = get_github_api(directory_url, headers=request_headers)

    # Verify that content has not been modified since last run
    if got.status_code == 304:
        logging.info(u'root directory listing has not changed since last update for {}'.format(directory_url))

    elif got.status_code not in range(400, 499):
        logging.info(u'root directory listing has changed for {}'.format(directory_url))
        # Update the project's last_updated_root_files field
        project_dict['last_updated_root_files'] = unicode(got.headers['ETag'])
        # get the contents of the file
        listing = got.json()

    else:
        logging.info(u'NO root directory listing found for {}'.format(directory_url))

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
    path = sub(r"[\s\/]+?$", "", path)
    # make sure we're working with the main github URL
    path = make_root_github_project_path(path)
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
        logging.info(u'Unchanged civic.json at {}'.format(civic_url))

    elif got.status_code not in range(400, 499):
        logging.info(u'New civic.json at {}'.format(civic_url))
        # Update the project's last_updated_civic_json field
        project_dict['last_updated_civic_json'] = unicode(got.headers['ETag'])
        try:
            # get the contents of the file
            civic = got.json()
        except ValueError:
            logging.error(u'Malformed civic.json at {}'.format(civic_url))

    else:
        logging.info(u'No civic.json at {}'.format(civic_url))

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


def save_organization_info(session, org_info):
    ''' Save a dictionary of organization info to the datastore session.

        Return an app.Organization instance.
    '''
    # Set any empty strings in org_info to None
    org_info = {key: None if not value else value for (key, value) in org_info.iteritems()}

    # Select an existing organization by name.
    filter = Organization.name == org_info['name']
    existing_org = session.query(Organization).filter(filter).first()

    # :::here (organization/true)
    # If this is a new organization, save and return it. The keep parameter is True by default.
    if not existing_org:
        new_organization = Organization(**org_info)
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
    for (field, value) in org_info.items():
        setattr(existing_org, field, value)

    return existing_org


def save_project_info(session, proj_dict):
    ''' Save a dictionary of project info to the datastore session.

        Return an app.Project instance.
    '''
    # Select the current project, filtering on name and organization.
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


def save_issue_info(session, issue_dict):
    ''' Save a dictionary of issue info to the datastore session.

        Return an app.Issue instance
    '''
    # Select the current issue, filtering on html_url and project id.
    filter = Issue.html_url == issue_dict['html_url'], Issue.project_id == issue_dict['project_id']
    existing_issue = session.query(Issue).filter(*filter).first()

    # If this is a new issue save and return it.
    if not existing_issue:
        new_issue = Issue(**issue_dict)
        session.add(new_issue)
        return new_issue

    # Preserve the existing issue.
    # :::here (issue/true)
    existing_issue.keep = True

    # Update existing issue details, skipping 'labels'
    for (field, value) in issue_dict.items():
        if field != 'labels':
            setattr(existing_issue, field, value)

    return existing_issue


def save_labels_info(session, issue_dict):
    ''' Save labels to issues
    '''
    # Select the current issue, filtering on html_url and project id.
    filter = Issue.html_url == issue_dict['html_url'], Issue.project_id == issue_dict['project_id']
    existing_issue = session.query(Issue).filter(*filter).first()

    # Get list of existing and incoming label names (dupes will be filtered out in comparison process)
    existing_label_names = [label.name for label in existing_issue.labels]
    incoming_label_names = [label['name'] for label in issue_dict['labels']]

    # Add labels that are in the incoming list and not the existing list
    add_label_names = list(set(incoming_label_names) - set(existing_label_names))
    for label_dict in issue_dict['labels']:
        if label_dict['name'] in add_label_names:
            # add the issue id to the labels
            label_dict["issue_id"] = existing_issue.id
            # remove id and default from some labels
            label_dict.pop("default", None)
            label_dict.pop("id", None)
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
    filter = Event.event_url == event_dict['event_url'], Event.organization_name == event_dict['organization_name']
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

    return existing_event


def save_story_info(session, story_dict):
    '''
        Save a dictionary of story into to the datastore session then return
        that story instance
    '''
    # Select the current story, filtering on link and organization name.
    filter = Story.organization_name == story_dict['organization_name'], Story.link == story_dict['link']

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

    return existing_story


def get_event_group_identifier(events_url):
    ''' Extract a group identifier from a meetup.com event URL
    '''
    if 'meetup.com' not in events_url:
        logging.error("Only Meetup.com events work right now.")
        return None

    parse_result = urlparse(events_url)
    url_parts = parse_result.path.split('/')
    identifier = url_parts.pop()
    if not identifier:
        identifier = url_parts.pop()
    if(match('^[A-Za-z0-9-]+$', identifier)):
        return identifier
    else:
        return None



def update_attendance(session, organization_name, attendance_dict):
    ''' Update exisiting attendance
    '''
    # Select the current attendance, filtering on organization
    filter = Attendance.organization_name == organization_name
    existing_attendance = session.query(Attendance).filter(filter).first()

    # if this is a new attendance, save and return it
    if not existing_attendance:
        new_attendance = Attendance(**attendance_dict)
        session.add(new_attendance)
        return new_attendance

    # Update existing attendance details
    existing_attendance.total = attendance_dict["total"]
    existing_attendance.weekly = attendance_dict["weekly"]

    return existing_attendance


def get_logo(org_info):
    '''
    get an organization's logo, looking first at 'logo_url' in the JSON and
    then Github (project lists url)
    '''
    # allow specifying a logo_url in the json file
    if 'logo_url' in org_info:
        return org_info['logo_url']

    if 'projects_list_url' not in org_info:
        return None

    github_username = parse_github_user(org_info['projects_list_url'])
    if github_username:
        # NOTE: This uses the /users/:id API endpoint to handle both cases
        # where the brigade's profile is a single user account or an
        # organizational account.
        request_url = GITHUB_USER_API_URL.format(username=github_username)
        got = get_github_api(request_url)
        if got.status_code == 404:
            logger.error("Got 404 for GitHub username " + github_username)
            return

        try:
            github_response = got.json()
            return github_response['avatar_url']
        except ValueError:
            logger.error("Malformed GitHub JSON fetching organization URL for " + github_username)
            return


def main(org_name=None, org_sources=None):
    ''' Update the API's database
    '''
    # set org_sources
    org_sources = org_sources or ORG_SOURCES_FILENAME

    # Collect a set of fresh organization names.
    organization_names = set()

    # Retrieve all organizations and shuffle the list in place.
    orgs_info = get_organizations(org_sources)
    shuffle(orgs_info)

    # If an organization name was passed, filter.
    if org_name:
        orgs_info = [org for org in orgs_info if org['name'] == org_name]

    # Retrieve and save all information about the organizations
    for org_info in orgs_info:

        if not is_safe_name(org_info['name']):
            error_dict = {
                "error": unicode('ValueError: Bad organization name: "{}"'.format(org_info['name'])),
                "time": datetime.now()
            }
            new_error = Error(**error_dict)
            db.session.add(new_error)
            # commit the error
            db.session.commit()
            continue

        # don't try to process orgs if we're throttled
        if GITHUB_THROTTLING:
            organization_names.add(org_info['name'])
            continue

        try:
            # Mark everything associated with this organization for deletion
            # :::here (event/false, story/false, project/false, organization/false)
            db.session.execute(db.update(Event, values={'keep': False}).where(Event.organization_name == org_info['name']))
            db.session.execute(db.update(Story, values={'keep': False}).where(Story.organization_name == org_info['name']))
            db.session.execute(db.update(Project, values={'keep': False}).where(Project.organization_name == org_info['name']))
            db.session.execute(db.update(Organization, values={'keep': False}).where(Organization.name == org_info['name']))

            # ORGANIZATION INFO
            # Save or update the organization
            org_info.update({'logo_url': get_logo(org_info)})

            organization = save_organization_info(db.session, org_info)
            organization_names.add(organization.name)

            # commit the organization and the false keeps
            db.session.commit()


            # STORIES
            if organization.rss or organization.website:
                logging.info(u"Gathering all of {}'s stories.".format(organization.name))
                stories = get_stories(organization)
                # build and commit stories
                for story_info in stories:
                    save_story_info(db.session, story_info)
                    db.session.commit()

            # PROJECTS, ISSUES and LABELS
            if organization.projects_list_url:
                logging.info(u"Gathering all of {}'s projects.".format(organization.name))
                projects = get_projects(organization)
                # build and commit projects
                for proj_dict in projects:
                    saved_project = save_project_info(db.session, proj_dict)
                    db.session.commit()

                    logging.info(u'Gathering all issues for this {} project: {}.'.format(organization.name, saved_project.name))
                    issues = get_issues(saved_project)
                    # build and commit issues and labels
                    for issue_dict in issues:
                        save_issue_info(db.session, issue_dict)
                        db.session.commit()
                        save_labels_info(db.session, issue_dict)
                        db.session.commit()

            # EVENTS
            if organization.events_url:
                logging.info(u"Gathering all of {}'s events.".format(organization.name))
                identifier = get_event_group_identifier(organization.events_url)
                if identifier:
                    # build and commit events
                    for event in get_meetup_events(organization, identifier):
                        save_event_info(db.session, event)
                        db.session.commit()

                    # Get and save the meetup.com member count for this organization
                    members = get_meetup_count(organization, identifier)
                    # Don't overwrite the old value if we got None back
                    if members:
                        organization.member_count = members
                        db.session.commit()

                else:
                    logging.error(u'{} does not have a valid events url'.format(organization.name))

            # Remove everything marked for deletion.
            # :::here (event/delete, story/delete, project/delete, issue/delete, organization/delete)
            num_events = db.session.query(Event).filter(Event.keep == False).delete()
            num_stories = db.session.query(Story).filter(Story.keep == False).delete()
            num_issues = db.session.query(Issue).filter(Issue.keep == False).delete()
            num_projects = db.session.query(Project).filter(Project.keep == False).delete()
            num_orgs = db.session.query(Organization).filter(Organization.keep == False).delete()

            logging.info(u'Deleted {} organizations, {} projects, {} issues, {} stories, {} events'.format(num_orgs, num_projects, num_issues, num_stories, num_events))

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
parser.add_argument('--sources', dest='sources', help='URL of an organization sources JSON file.')
parser.add_argument('--test', action='store_const', dest='test_sources', const=TEST_ORG_SOURCES_FILENAME, help='Use the testing list of organizations.')

if __name__ == "__main__":
    args = parser.parse_args()
    org_name = args.name and args.name.decode('utf8') or ''
    org_sources = args.sources and args.sources.decode('utf8') or ''
    if args.test_sources and not org_sources:
        org_sources = args.test_sources

    try:
        main(org_name=org_name, org_sources=org_sources)
    except:
        if SENTRY:
            SENTRY.captureException()
        raise
