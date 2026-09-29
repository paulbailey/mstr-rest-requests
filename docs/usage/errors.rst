Errors
======

When the API answers with an error status and a JSON error body, the session
raises an exception from :mod:`mstr.requests.rest.exceptions`, chosen by the
MicroStrategy error code in the body:

.. list-table::
   :header-rows: 1

   * - Exception
     - Error codes
     - Meaning
   * - :class:`~mstr.requests.rest.exceptions.LoginFailureException`
     - ERR003
     - Authentication failed
   * - :class:`~mstr.requests.rest.exceptions.IServerException`
     - ERR002, ERR0013
     - Intelligence Server error, or server unreachable
   * - :class:`~mstr.requests.rest.exceptions.ResourceNotFoundException`
     - ERR004
     - Resource not found
   * - :class:`~mstr.requests.rest.exceptions.InvalidRequestException`
     - ERR005, ERR006, ERR007
     - Missing or invalid input
   * - :class:`~mstr.requests.rest.exceptions.SessionException`
     - ERR009
     - Session invalid or timed out
   * - :class:`~mstr.requests.rest.exceptions.InsufficientPrivilegesException`
     - ERR0014, ERR0017
     - Missing privilege or permission
   * - :class:`~mstr.requests.rest.exceptions.ObjectAlreadyExistsException`
     - ERR0015
     - Object already exists
   * - :class:`~mstr.requests.rest.exceptions.MSTRUnknownException`
     - none
     - The error body has no error code
   * - :class:`~mstr.requests.rest.exceptions.MSTRException`
     - any other
     - Base class of all of the above

Every exception has ``code`` and ``message`` attributes, plus
``iserver_code`` and ``iserver_message`` when the server reports an
Intelligence Server error code.

.. code-block:: python

   from mstr.requests.rest.exceptions import (
       LoginFailureException,
       ResourceNotFoundException,
   )

   try:
       response = session.get("reports/abc123", project_id=project_id)
   except ResourceNotFoundException as e:
       print(e.code, e.message)

Error responses without a JSON body, such as a proxy's HTML error page, are
returned as normal. Check ``response.is_success`` or call
``response.raise_for_status()`` if you need to catch those too.

:class:`~mstr.requests.rest.exceptions.ExecutionCancelledException` is not
raised by the library; it is there for your own code to use when a report or
cube execution is cancelled.
