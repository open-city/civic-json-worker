[![Stories in Ready](https://badge.waffle.io/codeforamerica/cfapi.png?label=ready&title=Ready)](https://waffle.io/codeforamerica/cfapi)
[![Build Status](https://travis-ci.org/codeforamerica/cfapi.svg?branch=master)](https://travis-ci.org/codeforamerica/cfapi)

# The Code for America API

### What the CFAPI is
Code for America has developed this API to track all the activity across the civic technology movement. Our goal is to measure and motivate the movement by recognizing participation. The CFAPI describes an organization's projects, stories, and events.

The tools that the Brigades and other groups use to do their fine deeds are all different. The CFAPI does the difficult job of being able to track these activities no matter what tools an organization is using. The participants don't need to change their activities to be included.

### How it works
To get the information for the CfAPI, Code for America maintains a [list of civic tech organizations](https://docs.google.com/a/codeforamerica.org/spreadsheet/ccc?key=0ArHmv-6U1drqdGNCLWV5Q0d5YmllUzE5WGlUY3hhT2c&usp=drive_web#gid=0) and once an hour checks their activity on Meetup.com, their blog, and their GitHub projects. Other services and support for noncode projects are slowly being added. More technical details [below](https://github.com/codeforamerica/cfapi#installation).

### Projects powered by the CFAPI
* The Code for America <a href="http://codeforamerica.org/brigade">Brigade</a> website
<br/><a href="http://codeforamerica.org/brigade"><img src="http://i.imgur.com/C96yBLE.png" width="500px"></a>

* The Brigade <a href="http://codeforamerica.org/brigade/projects">Projects</a> Page
<br/><a href="http://codeforamerica.org/brigade/projects"><img src="http://i.imgur.com/Zv2zKvp.png" width="500px"/></a>

* <a href="http://www.codeforamerica.org/geeks/civicissues">The Civic Tech Issue Finder
<br/><img src="http://i.imgur.com/9aWV25e.png" width="400px"/></a>

* <a href="https://twitter.com/civicissues">The Civic Issue Twitter Bot
<br/><img src="http://i.imgur.com/Du9pLsu.png" width="400px"/></a>

* Lots of different Brigades websites


### Example Response
See the full documentation at http://codeforamerica.org/api

Response for `http://codeforamerica.org/api/organizations/Code-for-San-Francisco`
```
{
  "all_events": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco/events",
  "all_issues": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco/issues",
  "all_projects": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco/projects",
  "all_stories": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco/stories",
  "api_url": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco",
  "city": "San Francisco, CA",
  "current_events": [
    {
      "api_url": "http://codeforamerica.org/api/events/710",
      "created_at": "2014-02-26 21:05:21",
      "description": null,
      "end_time": null,
      "event_url": "http://www.meetup.com/Code-for-San-Francisco-Civic-Hack-Night/events/193535742/",
      "id": 710,
      "location": null,
      "name": "Weekly Civic Hack Night",
      "organization_name": "Code for San Francisco",
      "start_time": "2014-08-27 18:30:00 -0700"
    },
    ...
  ],
  "current_projects": [
    {
      api_url: "http://codeforamerica.org/api/projects/122",
      categories: null,
      code_url: "https://github.com/sfbrigade/localfreeweb.org",
      description: "Front end for the Local Free Web project",
      github_details: { ... },
      id: 122,
      issues: [ ... ],
      last_updated: "Thu, 24 Jul 2014 22:01:17 GMT",
      link_url: null,
      name: "localfreeweb.org",
      organization: {},
      organization_name: "Code for San Francisco",
      tags: ["digital access","bus stops"],
      type: null,
      status: "Official"
    },
    ...
  ],
  "current_stories": [
    {
      "api_url": "http://codeforamerica.org/api/stories/10",
      "id": 10,
      "link": "https://groups.google.com/d/msg/code-for-san-francisco/9OewkHV-D1M/0UW_ye9UXc8J",
      "organization_name": "Code for San Francisco",
      "title": "Hack Night Project Pick List",
      "type": "blog"
    },
    ...
  ],
  "id" : "Code-for-San-Francisco",
  "events_url": "http://www.meetup.com/Code-for-San-Francisco-Civic-Hack-Night/",
  "last_updated": 1409087294,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "name": "Code for San Francisco",
  "past_events": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco/past_events",
  "projects_list_url": "https://docs.google.com/spreadsheet/pub?key=0ArHmv-6U1drqdDVGZzdiMVlkMnRJLXp2cm1ZTUhMOFE&output=csv",
  "rss": "",
  "started_on": "2014-07-30",
  "type": "Brigade",
  "upcoming_events": "http://codeforamerica.org/api/organizations/Code-for-San-Francisco/upcoming_events",
  "website": "http://codeforsanfrancisco.org/"
}
```

### History
The need for a way to show off good civic tech projects was apparent. Several Brigades had all started working on ways to track their projects. They were working separately on the same idea at the same time. The CFAPI is a generalization of the great work done by:

<a href="http://opencityapps.org"><img src="http://chihacknight.org/images/sponsors/open-city-sm.jpg" alt="Open City"> Open City </a>

<a href="http://betanyc.org"><img src="http://betanyc.us/images/apple70Gray.png" alt="Beta NYC"> Beta NYC </a>

<a href="http://www.meetup.com/Code-for-Boston/"><img src="http://i.imgur.com/HlsvNQY.png" alt="Code for Boston"> Code for Boston </a>

*For the full story behind this API, [read this](https://hackpad.com/Civic.json-planning-meeting-EusFEMPgMio#:h=Chicago's-Open-Gov-Hack-Night-).

This repository is forked from [Open City's Civic Json Worker](https://github.com/open-city/civic-json-worker)

### Future
We hope that this experiment of tracking activity within a community is useful for other groups besides the civic technology movement. We will begin working with other groups to see if an instance of the CfAPI is useful for them.

We also want to add support for many more services to be included, such as events from Eventbrite. Our goal is for any organization to use any tool to do their work and we will integrate with them.

### How to add your Brigade to the API

Submit a Pull Request with your brigade's information to the [Brigade Information repository](https://github.com/codeforamerica/brigade-information). Instructions are included in that repo's [README](https://github.com/codeforamerica/brigade-information/blob/master/README.md).

### Civic.json
To add extra data about your projects to the CfAPI, include a `civic.json` file in the top level of your repo.

Currently we accept `status` and `tags` as fields in the civic.json.

An example civic.json file
```
{
    "status": "Production",
    "tags": ["slack", "bot", "integration", "python", "flask", "glossary", "dictionary"]
}
```

This project could then be easily found by searching the CfAPI like
[http://codeforamerica.org/api/projects?q=production,slack,bot](http://codeforamerica.org/api/projects?q=production,slack,bot)

The `civic.json` idea comes from BetaNYC and still has an [active discussion](https://github.com/BetaNYC/civic.json/issues) about its spec.


### Civic Tech Issue Finder
Once you've got your organization's GitHub projects on the API, all of your groups open GitHub Issues will be seen in the [Civic Tech Issue Finder](http://www.codeforamerica.org/geeks/civicissues). Use the label "help wanted" to get the most exposure. More info on that [project's README](https://github.com/codeforamerica/civic-issue-finder#civic-issue-finder).

## Installation

The CFAPI is built on [Flask](http://flask.pocoo.org/) and Python. The `app.py` file describes the models and routes. The `run_update.py` file runs once an hour and collects all the data about the different Brigades. Both `tests.py` and `run_update_test.py` are automatically run by [Travis-CI](https://travis-ci.org/codeforamerica/cfapi) whenever a new commit is made. The production service lives on Heroku. Please contact [us](https://github.com/codeforamerica/cfapi#contacts) with any questions.

### Development setup

#### Requirements

* PostgreSQL Database - [How To](https://github.com/codeforamerica/howto/blob/master/PostgreSQL.md)

#### Environmental variables

* `DATABASE_URL=[db connection string]` — My local example is `postgres:///cfapi`
* `GITHUB_TOKEN=[GitHub API token]` — Read about setting that up here: http://developer.github.com/v3/oauth/
* `MEETUP_KEY=[Meetup API Key]` — Read about setting that up here: https://secure.meetup.com/meetup_api/key/

Set these up in a local `.env` file.

#### Project setup

* Set up a [virtual environment](https://github.com/codeforamerica/howto/blob/master/Python-Virtualenv.md)

* Install the required libraries

```
$ pip install -r requirements.txt
```

* Set up a new database

```
createdb cfapi
python app.py createdb
```

* Run the updater

The `run_update.py` script will be run on Heroku once an hour and populate the database. To run locally, try:

```
python run_update.py
```

You can update just one organization if you need by using:

```
python run_update.py --name "Beta NYC"
```

For quicker update testing, use a shorter list of orgs by calling run_update.py with the `--test` flag:

```
python run_update.py --test
```

* Start the API

```
env `cat .env` python app.py runserver
```

* or use [foreman](http://theforeman.org/) to mimic how the CfAPI runs on Heroku.

```
foreman start
```

* Visit `localhost:5000` in your browser to see the results
```
http://localhost:5000/api/organizations/Code-for-America
```

### Deployment

Deployment is typically on Heroku. Follow [this tutorial](https://devcenter.heroku.com/articles/getting-started-with-python) for basic information on how to setup the project.

#### Environmental variables

These must be set:

* `GITHUB_TOKEN`
* `MEETUP_KEY` (if used)

`DATABASE_URL` will be handled by Heroku.

#### Project setup

* Initialize the database

```
heroku run bash
python -c 'from app import db; db.create_all()'
```

### Tests
* Set up a new database

```
createdb civic_json_worker_test
python -c 'from app import db; db.create_all()'

createdb peopledbtest
psql peopledbtest < test/peopledbtest.pgsql
```

`green -vvv --run-coverage` to run everything at once.

`green test/updater -vvv` to test the run_update process.

`green test/updater -vvv --run-coverage` to test the run_update process with coverage.

`green test/integration -vvv` to test the API.

`green test/integration -vvv --run-coverage` to test the API with code coverage.


### Codestyle (PEP8 and co.)

The project ships with flake8 to track style, perform a flake8 check by calling

`flake8 . --exclude=migrations,test --ignore=E501,E711,E712`




### Migrations
Migrations are handled through [flask-migrate](https://github.com/miguelgrinberg/Flask-Migrate#flask-migrate)

Contacts
--------

* Andrew Hyder ([ondrae](https://github.com/ondrae))
* Michal Migurski ([migurski](https://github.com/migurski))
* Tomas Apodaca ([tmaybe](https://github.com/tmaybe))

Contributing
------------

Here are some ways *you* can contribute:

* by reporting bugs
* by suggesting new features
* by translating to a new language
* by writing or editing documentation
* by writing code (**no patch is too small**: fix typos, add comments, clean up
  inconsistent whitespace)
* by refactoring code
* by closing [issues][]
* by reviewing patches
* [financially][]

[issues]: https://github.com/codeforamerica/cfapi/issues
[financially]: https://secure.codeforamerica.org/page/contribute


Submitting an Issue
-------------------

We use the [GitHub issue tracker][issues] to track bugs and features. Before
submitting a bug report or feature request, check to make sure it hasn't
already been submitted. You can indicate support for an existing issue by
voting it up. When submitting a bug report, please include a [Gist][] that
includes a stack trace and any details that may be necessary to reproduce the
bug.

[gist]: https://gist.github.com/

Submitting a Pull Request
-------------------------

1. Fork the project.
2. Create a topic branch.
3. Implement your feature or bug fix.
4. Write tests!
5. Run a migration if needed.
6. Commit and push your changes.
7. Submit a pull request.


Copyright
---------

Copyright (c) 2015 Code for America.
