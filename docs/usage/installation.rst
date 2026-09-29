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

The deprecated requests-based sessions in :mod:`mstr.requests.compat` need
the ``requests`` extra:

.. code-block:: bash

   pip install mstr-rest-requests[requests]

The ``async`` and ``httpx`` extras from 1.x still install, but add nothing:
httpx is a core dependency since 2.0.

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

Build the documentation:

.. code-block:: bash

   uv run sphinx-build -b html docs docs/_build/html
