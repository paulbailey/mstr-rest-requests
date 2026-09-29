Quick start
===========

You need the URL of a MicroStrategy Library REST API, which usually ends in
``/MicroStrategyLibrary/api/``, and credentials for it.

Connecting with a context manager
---------------------------------

:class:`~mstr.requests.AuthenticatedMSTRRESTSession` logs in when the
``with`` block starts and logs out when it ends:

.. code-block:: python

   from mstr.requests import AuthenticatedMSTRRESTSession

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username="dave",
       password="hellodave",
   ) as session:
       projects = session.get("projects").json()

See :doc:`authentication` for the other ways to log in and for reading
credentials from a secrets manager.

Logging in and out yourself
---------------------------

Use :class:`~mstr.requests.MSTRRESTSession` when you want to control when the
session logs in and out:

.. code-block:: python

   from mstr.requests import MSTRRESTSession

   with MSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/"
   ) as session:
       session.login(username="dave", password="hellodave")
       projects = session.get_projects()
       session.logout()

Here the ``with`` block only closes the connection pool when it ends. Without
one, call ``session.close()`` when you are done.

Making requests
---------------

The session has the usual ``get``, ``post``, ``put``, ``patch``, ``delete``,
``head``, ``options`` and ``request`` methods. They take httpx's arguments
(``params``, ``json``, ``headers``, ``timeout`` and so on) and return an
:class:`httpx.Response`. URLs are relative to ``base_url``.

Two extra keyword arguments cover the MicroStrategy headers:

* ``include_auth`` (default ``True``) sends the ``X-MSTR-AuthToken`` header.
* ``project_id`` sends the ``X-MSTR-ProjectID`` header that project-scoped
  endpoints need.

.. code-block:: python

   session.load_projects()
   project_id = session.get_project_id("My Project")
   response = session.get("reports/abc123", project_id=project_id)

Error responses from the API raise typed exceptions; see :doc:`errors`.

Client options
--------------

The session wraps an :class:`httpx.Client`, available as ``session.client``.
Extra constructor arguments such as ``verify``, ``proxy``, ``limits``,
``http2`` or ``transport`` are passed to it. Unlike httpx's own defaults,
there is no timeout unless you pass ``timeout=``, and redirects are followed.

.. code-block:: python

   session = MSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       proxy="http://proxy.example.com:8080",
       timeout=30,
   )

Session state
-------------

.. code-block:: python

   session.has_session()       # True if an auth token is present
   session.get_session_info()  # GET /sessions
   session.extend_session()    # PUT /sessions, which prolongs the session
   session.get_userinfo()      # GET /sessions/userInfo

Saving and restoring a session
------------------------------

A logged-in session can be serialised and restored later, for example to
hand it to another process:

.. code-block:: python

   import json

   data = session.json()

   # Later, perhaps in another process:
   restored = MSTRRESTSession.from_dict(json.loads(data))

``to_dict()`` returns the same data as a dictionary. The sync and async
sessions share the format, so a session saved by one can be restored by the
other.
