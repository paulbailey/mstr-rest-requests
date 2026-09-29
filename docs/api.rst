API reference
=============

.. automodule:: mstr.requests

Session classes
---------------

.. autoclass:: mstr.requests.MSTRRESTSession
   :members:
   :inherited-members:
   :show-inheritance:

.. autoclass:: mstr.requests.AuthenticatedMSTRRESTSession
   :members:
   :show-inheritance:

.. autodata:: mstr.requests.Credential

.. autoclass:: mstr.requests.rest.httpx_sync.base.MSTRBaseSession
   :members:
   :show-inheritance:

.. autoclass:: mstr.requests.MSTRSessionProtocol
   :members:

.. _async-api:

Async session classes
---------------------

.. autoclass:: mstr.requests.AsyncMSTRRESTSession
   :members:
   :inherited-members:
   :show-inheritance:

.. autoclass:: mstr.requests.AsyncAuthenticatedMSTRRESTSession
   :members:
   :show-inheritance:

.. autodata:: mstr.requests.AsyncCredential

.. autoclass:: mstr.requests.rest.aio.AsyncMSTRBaseSession
   :members:
   :show-inheritance:

.. autoclass:: mstr.requests.AsyncMSTRSessionProtocol
   :members:

Core helpers
------------

.. automodule:: mstr.requests.rest.core
   :members:
   :exclude-members: Credential

Deprecated modules
------------------

.. automodule:: mstr.requests.httpx

.. automodule:: mstr.requests.compat

.. autoclass:: mstr.requests.compat.MSTRRESTSession
   :members:
   :inherited-members:
   :show-inheritance:

.. autoclass:: mstr.requests.compat.AuthenticatedMSTRRESTSession
   :members:
   :show-inheritance:

.. autoclass:: mstr.requests.compat.MSTRBaseSession
   :members:
   :show-inheritance:

.. autoclass:: mstr.requests.compat.MSTRSessionProtocol
   :members:

Exceptions
----------

.. automodule:: mstr.requests.rest.exceptions
   :members:
   :show-inheritance:

.. _credential-providers-api:

Credential providers
--------------------

.. automodule:: mstr.requests.credentials

Environment variables
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: mstr.requests.credentials.env
   :members:

AWS
~~~

.. automodule:: mstr.requests.credentials.aws
   :members:
   :show-inheritance:

Azure
~~~~~

.. automodule:: mstr.requests.credentials.azure
   :members:
   :show-inheritance:

GCP
~~~

.. automodule:: mstr.requests.credentials.gcp
   :members:
   :show-inheritance:
