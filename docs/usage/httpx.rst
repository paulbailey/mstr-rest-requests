Moving to httpx
===============

In 2.0 the synchronous classes exported by :mod:`mstr.requests` will be built
on `httpx <https://www.python-httpx.org/>`_ instead of requests, so the sync
and async sessions share one HTTP library. The httpx-based classes are
available now from :mod:`mstr.requests.httpx` with the same names and
arguments:

.. code-block:: python

   from mstr.requests.httpx import AuthenticatedMSTRRESTSession

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username="dave",
       password="hellodave",
   ) as session:
       projects = session.get_projects()

They need the ``httpx`` extra (``pip install mstr-rest-requests[httpx]``).
Creating a requests-based session emits a :class:`PendingDeprecationWarning`,
which Python hides by default outside test runners.

What changes
------------

* Methods return :class:`httpx.Response`. Use ``response.is_success``
  instead of ``response.ok``. ``raise_for_status()`` raises
  :class:`httpx.HTTPStatusError`, and also raises for 3xx responses.
* Request arguments follow httpx: ``follow_redirects`` instead of
  ``allow_redirects``, and ``content=`` for raw bodies.
* The session wraps an :class:`httpx.Client` (``session.client``) rather
  than being a :class:`requests.Session`. Configure TLS, proxies, retries
  and connection limits with constructor arguments (``verify``, ``proxy``,
  ``transport``, ``limits``) instead of ``session.mount()`` and adapters.
* As with requests, there is no timeout by default and redirects are
  followed.
* Relative URLs are always appended to ``base_url``, so a leading ``/`` or a
  missing trailing slash no longer drops the ``/api`` segment.
* Use ``with`` or ``session.close()`` to release connections.
* ``to_dict()`` / ``from_dict()`` use the same format, so a session can be
  handed between the requests, httpx and async classes.

.. autoclass:: mstr.requests.httpx.MSTRRESTSession
   :no-index:

.. autoclass:: mstr.requests.httpx.AuthenticatedMSTRRESTSession
   :no-index:
