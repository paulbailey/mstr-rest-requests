import setuptools
from mstr import VERSION

setuptools.setup(
    setup_requires="pytest-runner",
    tests_require="pytest",
    version=VERSION,
)
