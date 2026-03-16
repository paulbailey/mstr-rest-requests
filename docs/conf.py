# Configuration file for the Sphinx documentation builder.
#
# Full docs: https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib.metadata

# -- Project information -----------------------------------------------------

project = "mstr-rest-requests"
copyright = "2020–2026, Paul Bailey"
author = "Paul Bailey"

_meta = importlib.metadata.metadata("mstr-rest-requests")
version = _meta["Version"]
release = version

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for autodoc -----------------------------------------------------

autodoc_member_order = "bysource"

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"

# -- Options for intersphinx -------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}
