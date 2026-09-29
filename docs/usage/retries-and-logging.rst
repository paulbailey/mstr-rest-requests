Retries and logging
===================

Retries
-------

Sessions don't retry by default. Pass ``retries=`` to any session class
(sync or async) to retry:

* requests that failed to connect, or timed out waiting for a pooled
  connection, whatever their method, because the server never saw them;
* ``GET``, ``HEAD``, ``OPTIONS``, ``PUT`` and ``DELETE`` requests that timed
  out, hit another network error, or got a ``502``, ``503`` or ``504``.

``POST`` and ``PATCH`` requests are not retried after the server may have
received them, since MicroStrategy may already have acted on them.

The first retry waits ``backoff_factor`` seconds (default ``0.5``), and each
further retry waits twice as long as the one before, up to 60 seconds. If
the server sends a longer ``Retry-After`` (in seconds), that is used
instead, up to the same 60-second limit.

.. code-block:: python

   from mstr.requests import AuthenticatedMSTRRESTSession

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username="dave",
       password="hellodave",
       retries=3,
       backoff_factor=1,
   ) as session:
       ...

If every attempt fails, you get the last response (or its exception), just
as without retries.

To re-login when a session expires, see :ref:`long-running-jobs`.

Logging
-------

The library logs through the standard :mod:`logging` module, under the
``mstr.requests`` logger:

* ``DEBUG``: every request's method, URL, status and time taken, such as
  ``GET https://your-server/MicroStrategyLibrary/api/projects -> 200 (84 ms)``.
* ``INFO``: logging in again after a session expired.
* ``WARNING``: each retry, failed keep-alive requests, and logout errors
  that happen while a ``with`` block is already raising.

Headers, request and response bodies, tokens and passwords are never
logged, and any ``user:password@`` part of a URL is removed.

.. code-block:: python

   import logging

   logging.basicConfig()
   logging.getLogger("mstr.requests").setLevel(logging.DEBUG)
