Quick Start with mstr-rest-requests
===================================

Assuming you have a working MicroStrategy Library installation to point at:

Establishing a connection
-------------------------

Probably the easiest way to establish a connection is by explicitly logging in and out:

.. autoclass:: mstr.requests.MSTRRESTSession
   :members: login, logout
   :no-index:

Establishing a connection with a context manager
------------------------------------------------

.. autoclass:: mstr.requests.AuthenticatedMSTRRESTSession
   :members:
   :no-index:

``AuthenticatedMSTRRESTSession`` accepts optional credential arguments. Use
``username`` and ``password`` for standard auth, ``identity_token`` for
delegation, or ``api_key`` for trusted (API key) authentication. Example with
API key:

.. code-block:: python

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       api_key="your-api-key",
   ) as session:
       session.get("projects")
