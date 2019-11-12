# mstr-rest-requests

A extension to the excellent `requests` `Session` object, to enable more straightforward interaction with MicroStrategy's REST API.

[![Build status](https://travis-ci.org/paulbailey/mstr-rest-requests.svg?branch=master)](https://travis-ci.org/paulbailey/mstr-rest-requests/)

## Usage

### Installation

Simply install the package however you normally install them, for example:

`pip install mstr-rest-requests`

### Examples

#### Authentication

Here's how to get an authenticated session (currently only standard and anonymous authentication are supported):

```
from mstr.requests import MSTRRESTSession

session = MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')
session.login(username='dave', password='hellodave')
session.has_session()
# returns True
```

#### Session handling

Several convenience methods are implemented to make dealing with Session objects easier.

`def has_session(self)`

Will return a boolean as to whether the session contains an authentication tokem.

`def destroy_auth_token(self)`

Removes the auth token from the session

`def json(self)`

Returns a JSON representation of the session that can be reconstituted with:

`update_from_json(self, data)`

where `data` is either a dict or a string containing JSON data.

#### HTTP requests

The MSTRRESTSession adds two parameters to all request methods:

`include_auth=True, project_id=None`

so you can specify a `project_id` on any request by adding the parameter.

#### Convenience methods for API calls

TODO
