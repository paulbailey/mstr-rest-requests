# mstr-rest-requests

A extension to the excellent `requests` `Session` object, to enable more straightforward interaction with MicroStrategy's REST API.

## Usage

Simply install the package however you normally install them, for example:

`pip install mstr-rest-requests`

Here's how to get an authenticated session (currently only standard and anonymous authentication are supported):

```
from mstr.requests import MSTRRESTSession

session = MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')
session.login(username='dave', password='hellodave')
session.has_session()
# returns True
```