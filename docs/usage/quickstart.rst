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
