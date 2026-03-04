API Reference
=============

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

Base session
------------

.. autoclass:: mstr.requests.rest.base.MSTRBaseSession
   :members:
   :show-inheritance:

Protocol
--------

.. autoclass:: mstr.requests.rest.protocols.MSTRSessionProtocol
   :members:

Mixins
------

.. autoclass:: mstr.requests.rest.api.auth.AuthMixin
   :members:

.. autoclass:: mstr.requests.rest.api.sessions.SessionsMixin
   :members:

.. autoclass:: mstr.requests.rest.api.projects.ProjectsMixin
   :members:

.. autoclass:: mstr.requests.rest.mixins.SessionPersistenceMixin
   :members:

Exceptions
----------

.. automodule:: mstr.requests.rest.exceptions
   :members:
   :show-inheritance:

Credential providers
--------------------

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
