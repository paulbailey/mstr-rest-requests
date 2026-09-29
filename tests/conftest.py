"""Tests marked ``live`` call demo.microstrategy.com and only run with ``--live``."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run tests marked 'live', which need demo.microstrategy.com",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="needs --live (calls demo.microstrategy.com)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
