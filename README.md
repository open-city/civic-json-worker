# civic-json-worker

[Flask](http://flask.pocoo.org) app for tracking opengov projects in Chicago.

**NOTE**: *civic-json-worker is being expanded to work for any city. Development of this project has moved to Code for America's [civic-json-worker fork](https://github.com/codeforamerica/civic-json-worker#contribute).*

## Objective

Keep track of all the civic tech projects worked on at the Chicago open gov hack night. Eventually this could track all civic projects in Chicago, or even nationally.

## The plan

Curate a simple list of Github URLs for civic tech projects and leave filling in the rest to the [Github API](http://developer.github.com/). 

Looking at [other civic tech listing projects](http://commons.codeforamerica.org/) like this that have [gone stale](http://digital.cityofchicago.org/index.php/open-data-applications/), the real sticking point is in maintaining and curating the list of projects. If we can make the maintenance part as simple as possible, we have a greater chance that this thing will live on.

So humans will be responsible for one thing: __deciding what gets tracked__. 

```json
[
    "https://github.com/dssg/census-communities-usa",
    "https://github.com/open-city/open-gov-hack-night",
    ...
]
```

The rest is up to computers. When the ``/update-projects/`` path is hit on this app, it loops over the projects in the list and captures something like this:

``` json
[
    {
        "contributors": [
            {
                "avatar_url": "https://0.gravatar.com/avatar/5e5eb188a0e4d3a7c8f38ee0fc3a6cbd?d=https%3A%2F%2Fidenticons.github.com%2Fd8c3ef3ed05a213a7225bf5e6e46101a.png", 
                "contributions": 51, 
                "html_url": "https://github.com/derekeder", 
                "login": "derekeder"
            }, 
            {
                "avatar_url": "https://2.gravatar.com/avatar/813d23c289052af417387a9270d0da31?d=https%3A%2F%2Fidenticons.github.com%2Ffa9357bb22fd993fc9795619c7e1d4f7.png", 
                "contributions": 46, 
                "html_url": "https://github.com/fgregg", 
                "login": "fgregg"
            }, 
            {
                "avatar_url": "https://2.gravatar.com/avatar/1d0c5faee140af87d7d6967bc946ecc6?d=https%3A%2F%2Fidenticons.github.com%2F44e80db9ed8527f429c969e804432b0f.png", 
                "contributions": 9, 
                "html_url": "https://github.com/evz", 
                "login": "evz"
            }
        ], 
        "contributors_url": "https://api.github.com/repos/datamade/csvdedupe/contributors", 
        "created_at": "2013-07-11T14:23:33Z", 
        "description": "Command line tool for deduplicating CSV files", 
        "forks_count": 2, 
        "homepage": null, 
        "html_url": "https://github.com/datamade/csvdedupe", 
        "id": 11343900, 
        "language": "Python", 
        "name": "csvdedupe", 
        "open_issues": 8, 
        "owner": {
            "avatar_url": "https://2.gravatar.com/avatar/0a89207d38feff1dcd938bdc1e4a9b5e?d=https%3A%2F%2Fidenticons.github.com%2F3424042f8cb2b04950903794ad9c8daf.png", 
            "html_url": "https://github.com/datamade", 
            "login": "datamade"
        }, 
        "updated_at": "2013-09-20T06:32:39Z", 
        "watchers_count": 26
    },
    ...
]
```

This data is hosted on a publicly available endpoint as JSON with a CORS configuration that allows it to be loaded via 
an Ajax call, for [use on this site](http://opengovhacknight.org/projects.html) for listing/sorting/searching projects. 
__bonus:__ anyone can use [this JSON
file](http://worker.opengovhacknight.org/data/project_details.json) for their
own purposes. Details on setting up a CORS configuration for nginx can be found
[here](https://github.com/open-city/civic-json-worker/issues/16#issuecomment-28759993)

## Benefits

By pushing everything on to Github, we will have very little to maintain, content-wise, as administrators. Simultaneously, we will encourage people to:

* sign up for Github if they aren't already
* keep their projects open source (we can't crawl private repos)
* make sure their description and website urls are up to date
* use the issue tracker

## Setup this app

Propping this sucker up for oneself is pretty simple. However, there are some basic requirements which can be gotten 
in the standard Python fashion (assuming you are working in a [virtualenv](https://pypi.python.org/pypi/virtualenv)):

``` bash
$ pip install -r requirements.txt
```

Besides that, there are a few environmental variables that you'll need to set:

``` bash
$ export FLASK_KEY=[whatever you want] # This is a string that you'll check to make sure that only trusted people are deleting things
$ export GITHUB_TOKEN=[Github API token] # Read about setting that up here: http://developer.github.com/v3/oauth/
$ export S3_BUCKET=[Name of the bucket] # This is the bucket where you'll store the JSON files 
$ export AWS_ACCESS_KEY=[Amazon Web Services Key] # This will need access to the bucket above
$ export AWS_SECRET_KEY=[Amazon Web Services Secret] # This will need access to the bucket above
```

Probably easiest placed in the .bashrc (or the like) of 
the user that the app is running as rather than manually set but you get the idea...

### Want to help? Have ideas to make this better?

The issue tracker is actively watched and pull requests are welcome!
