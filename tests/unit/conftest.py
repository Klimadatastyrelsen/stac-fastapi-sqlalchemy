"""Isolated source tests: run with --confcutdir=tests/unit."""

import os

import pytest

for name, value in {
    "POSTGRES_USER": "unused",
    "POSTGRES_PASS": "unused",
    "POSTGRES_HOST_READER": "127.0.0.1",
    "POSTGRES_HOST_WRITER": "127.0.0.1",
    "POSTGRES_PORT": "1",
    "POSTGRES_DBNAME": "unused",
}.items():
    os.environ[name] = value


@pytest.fixture(autouse=True)
def prohibit_database_connections(monkeypatch):
    def reject_connection(*args, **kwargs):
        raise AssertionError("Source unit tests must not connect to a database")

    monkeypatch.setattr("psycopg2.connect", reject_connection)
