Upgrading from 1.x
==================

Since 2.0 the sessions exported by :mod:`mstr.requests` are built on
`httpx <https://www.python-httpx.org/>`_ instead of requests, so the sync and
async sessions share one HTTP library. The class names, arguments and
methods are the same, so most code keeps working unchanged.

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
* Sessions saved with ``to_dict()`` / ``json()`` in 1.x load unchanged.
* requests and requests-toolbelt are no longer installed by default.
* :mod:`mstr.requests.httpx` from 1.3 still works as an alias for
  :mod:`mstr.requests`.

Keeping 1.x behaviour
---------------------

The requests-based classes are available until 3.0 from
:mod:`mstr.requests.compat`. They need the ``requests`` extra and emit a
:class:`DeprecationWarning` when created:

.. code-block:: bash

   pip install mstr-rest-requests[requests]

.. code-block:: python

   from mstr.requests.compat import AuthenticatedMSTRRESTSession
