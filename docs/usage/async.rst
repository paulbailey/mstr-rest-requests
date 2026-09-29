Async usage
===========

:class:`~mstr.requests.AsyncMSTRRESTSession` and
:class:`~mstr.requests.AsyncAuthenticatedMSTRRESTSession` are the async
counterparts of the synchronous sessions. Like them, they are built on
`httpx <https://www.python-httpx.org/>`_, and they work with asyncio and trio.

.. code-block:: python

   import asyncio

   from mstr.requests import AsyncAuthenticatedMSTRRESTSession


   async def main():
       async with AsyncAuthenticatedMSTRRESTSession(
           base_url="https://your-server/MicroStrategyLibrary/api/",
           username="dave",
           password="hellodave",
       ) as session:
           await session.load_projects()
           project_id = session.get_project_id("My Project")
           responses = await asyncio.gather(
               session.get("reports/abc123", project_id=project_id),
               session.get("reports/def456", project_id=project_id),
           )


   asyncio.run(main())

Every method of the synchronous session exists with the same name and
arguments; the ones that make requests are coroutines and return
:class:`httpx.Response` objects.

Credentials
-----------

Credential arguments accept anything the synchronous session accepts, plus
``async def`` callables. Plain callables, including the built-in credential
providers, run in a worker thread so a secrets-manager lookup doesn't block
the event loop.

Client options
--------------

The session wraps an :class:`httpx.AsyncClient`, available as
``session.client``. Extra keyword arguments such as ``verify``, ``limits``,
``http2`` or ``transport`` are passed to it. To match the synchronous
session, requests have no timeout by default (pass ``timeout=`` to set one)
and redirects are followed.

Use ``async with`` or ``await session.aclose()`` to release connections.

Saved sessions
--------------

``to_dict()`` and ``from_dict()`` use the same format as the synchronous
session, so a session saved by one can be restored by the other.

See :ref:`async-api` for the full list of methods.
