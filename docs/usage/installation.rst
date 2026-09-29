Installation
============

Python 3.10 or later is required.

Install from PyPI with pip:

.. code-block:: bash

   pip install mstr-rest-requests

Optional extras
---------------

To use the built-in credential providers, install the corresponding extra:

.. code-block:: bash

   pip install mstr-rest-requests[aws]    # AWS Secrets Manager & SSM Parameter Store
   pip install mstr-rest-requests[azure]  # Azure Key Vault
   pip install mstr-rest-requests[gcp]    # Google Cloud Secret Manager

To use the async sessions, install the ``async`` extra, which adds
`httpx <https://www.python-httpx.org/>`_:

.. code-block:: bash

   pip install mstr-rest-requests[async]

To try the httpx-based synchronous sessions that become the default in 2.0,
install the ``httpx`` extra:

.. code-block:: bash

   pip install mstr-rest-requests[httpx]

Development
-----------

Clone the repository and install with `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: bash

   git clone https://github.com/paulbailey/mstr-rest-requests.git
   cd mstr-rest-requests
   uv sync --all-extras

Run the test suite:

.. code-block:: bash

   uv run pytest
