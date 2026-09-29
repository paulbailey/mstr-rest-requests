Testing your code
=================

Code that uses mstr-rest-requests can be tested without a MicroStrategy
server. Every session class takes a ``transport=`` argument, which is passed
to httpx, and :class:`httpx.MockTransport` turns a plain function into a
fake server: it receives each :class:`httpx.Request` and returns an
:class:`httpx.Response`.

The fake only needs to answer the endpoints your code calls, plus
``auth/login`` (with an ``X-MSTR-AuthToken`` header) and ``auth/logout`` if
you use an authenticated session. Returning a MicroStrategy-style JSON error
for anything else makes a missing route easy to spot, because it is raised
as a :class:`~mstr.requests.rest.exceptions.MSTRException`.

This example is run as part of the library's own test suite:

.. literalinclude:: ../../tests/test_docs_testing_example.py
   :language: python
   :lines: 3-

For the async sessions, use the same fake with
:class:`~mstr.requests.AsyncAuthenticatedMSTRRESTSession`; a synchronous
function works with :class:`httpx.MockTransport` in both cases.

To check what your code sent, keep the requests the fake receives, for
example by appending them to a list, and assert on their ``method``,
``url``, ``headers`` or ``content``.
