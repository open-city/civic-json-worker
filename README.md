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

* The Brigade <a href="http://codeforamerica.org/brigade/events">Events</a> Page
<br/><a href="http://codeforamerica.org/brigade/events"><img src="http://i.imgur.com/p29utjI.png" width="500px"/></a>

* The Code for America <a href="http://codeforamerica.org/geeks">Citizens</a> Page
<br/><a href="http://codeforamerica.org/geeks"><img src="http://i.imgur.com/5PZBBfQ.png" width="500px"/></a>

* <a href="http://www.codeforamerica.org/geeks/civicissues/embed">The Civic Tech Issue Finder
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
      last_updated_issues: ""78589d3f95ad8fb4694d5e3c30550449"",
      link_url: null,
      name: "localfreeweb.org",
      organization: {},
      organization_name: "Code for San Francisco",
      type: null,
      status: "Delivered"
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

<a href="http://opencityapps.org"><img src="http://opengovhacknight.org/images/sponsors/open-city-sm.jpg" alt="Open City"> Open City </a>

<a href="http://betanyc.org"><img src="http://betanyc.us/images/apple70Gray.png" alt="Beta NYC"> Beta NYC </a>

<a href="http://www.meetup.com/Code-for-Boston/"><img src="http://i.imgur.com/HlsvNQY.png" alt="Code for Boston"> Code for Boston </a>

*For the full story behind this API, [read this](https://hackpad.com/Civic.json-planning-meeting-EusFEMPgMio#:h=Chicago's-Open-Gov-Hack-Night-).

This repository is forked from [Open City's Civic Json Worker](https://github.com/open-city/civic-json-worker)

### Future
We hope that this experiment of tracking activity within a community is useful for other groups besides the civic technology movement. We will begin working with other groups to see if an instance of the CfAPI is useful for them.

We also want to add support for many more services to be included, such as events from Eventbrite. Our goal is for any organization to use any tool to do their work and we will integrate with them.

### How to add your Brigade to the API

##### Brigade Information
The new site will be powered by this [Brigade Information](https://docs.google.com/spreadsheet/ccc?key=0ArHmv-6U1drqdGNCLWV5Q0d5YmllUzE5WGlUY3hhT2c&usp=sharing) Google Spreadsheet. This way you don't need yet another account for our Brigade site. Just keep your Brigade's info up to date and you're good. Email andrewh@codeforamerica.org if you want permission to add and edit groups.

The columns are:
* Name
* Website
* Events Url - Point us to where ever you schedule your events. Only Meetup.com events are working right now.
* RSS - If you have a blog, point us to it. It's pretty smart and can find the feed on its own. To show off your Google Group discussions, use a link like `https://groups.google.com/forum/feed/code-for-san-francisco/msgs/rss.xml?num=15`
* Projects list URL - Can either be a GitHub organization url like `https://github.com/sfbrigade` or a link to a list of project URLs, described below.


##### Projects List
This projects list you point us to will need the following columns:
* `name` - filled in by GitHub if left blank
* `description` - filled in by GitHub if left blank
* `link_url` - filled in by GitHub if left blank
* `code_url` - Only GitHub links work for now. Others will be added as needed later.
* `type` - Is this project an app, an open data policy, a webservice?
* `categories` - Write your own separated by commas. "Education, digital literacy"
* `status` - Whatever status names you use, e.g., "Needs sponsor", "In progress", "Delivered"

An example:
```
name, description, link_url, code_url, type, categories, status
South Bend Voices, "A redeploy of CityVoice for South Bend, IN.", http://www.southbendvoices.com/, https://github.com/codeforamerica/cityvoice, web service, "community engagement, housing", "In progress"
```

That projects list URL can be any flavor of csv. The easiest way is to make a Google Spreadsheet like [my example](https://docs.google.com/spreadsheet/ccc?key=0ArHmv-6U1drqdDBzNXpSZkVzRDJUQnpOS0RJM0FDWGc&usp=sharing) and then select **File > Publish it to the web**. 

If you are using the new Google Spreadsheets, add `/export?format=csv` to the end. 
`https://docs.google.com/spreadsheets/d/<key>/export?format=csv`

If you have the older Google Drive version change `?output=html` to `?output=csv`.
`https://docs.google.com/spreadsheet/pub?key=<key>?output=csv`

Put that in the Brigade Information sheet and you're done.

The projects list URL can also be a JSON file, with a list of strings containing GitHub project URLs.

Lastly, the projects list URL can be a GitHub organization URL, like http://github.com/codeforamerica.

### Civic Tech Issue Finder
Once you've got your organization's GitHub projects on the API, all of your groups open GitHub Issues will be seen in the [Civic Tech Issue Finder](http://www.codeforamerica.org/geeks/civicissues). Use the label "help wanted" to get the most exposure. More info on that [project's README](https://github.com/codeforamerica/civic-issue-finder#civic-issue-finder).

### Civic.json data standard
The `/projects` endpoint is structure is influenced by [Civic.json](https://github.com/BetaNYC/civic.json), a proposed meta-data standard for describing civic tech projects. The goal is for this standard to be simple, and for the data fields that describe projects to be largely assembled programatically.

The standard is still very much in planning phases, and we [welcome discussion](https://github.com/BetaNYC/civic.json/issues).

## Installation

The CFAPI is built on [Flask](http://flask.pocoo.org/) and Python. The `app.py` file describes the models and routes. The `run_update.py` file runs once an hour and collects all the data about the different Brigades. Both `tests.py` and `run_update_test.py` are automatically run by [Travis-CI](https://travis-ci.org/codeforamerica/cfapi) whenever a new commit is made. The production service lives on Heroku. Please contact Andrew and Erica in the "Contribute" section below to get involved.

### Development setup

#### Environmental variables

* `DATABASE_URL=[db connection string]` — My local example is `postgres://hackyourcity@localhost/cfapi` When testing locally, `sqlite:///data.db` is a great way to skip Postgres installation.
* `GITHUB_TOKEN=[GitHub API token]` — Read about setting that up here: http://developer.github.com/v3/oauth/
* `MEETUP_KEY=[Meetup API Key]` — Read about setting that up here: https://secure.meetup.com/meetup_api/key/

Set these environment variables in your `.bash_profile`. Then run `source ~/.bash_profile`.

#### Project setup

* Set up a [virtualenv](https://pypi.python.org/pypi/virtualenv)

```
pip install virtualenv
virtualenv venv-cfapi
source venv-cfapi/bin/activate
```

* Install the required libraries

```
$ pip install -r requirements.txt
```

* Set up a new database

```
createdb cfapi
python -c 'from app import db; db.create_all()'
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

There is a line near the top of run_update.py that sets the `ORG_SOURCES` variable. Change the list of org sources to `test_org_sources.csv` for quicker update testing.

* Start the API

```
python app.py runserver
```

* Visit http://localhost:5000/api/organizations/Code-for-America to see your results.

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
heroku console
python -c 'from app import db; db.create_all()'
```

### Tests
* Set up a new database

```
createdb civic_json_worker_test
python -c 'from app import db; db.create_all()'
```

`python run_update_test.py` to test the run_update process.
`python tests.py` to test the API.


### Migrations
Migrations are handled through [flask-migrate](https://github.com/miguelgrinberg/Flask-Migrate#flask-migrate)

Contacts
--------

* Andrew Hyder ([ondrae](https://github.com/ondrae))
* Erica Kwan ([pui](https://github.com/pui))
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

Copyright (c) 2014 Code for America.
