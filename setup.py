import setuptools
from src.mstr_rest_requests import VERSION

setuptools.setup(
    setup_requires="pytest-runner",
    tests_require="pytest",
    version=VERSION
)
