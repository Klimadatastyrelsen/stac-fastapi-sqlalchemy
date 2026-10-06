"""Database mapping defaults and overrides require no database connection."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("override", [False, True])
def test_database_mapping(override):
    names = ("POSTGRES_SCHEMA", "POSTGRES_ITEM_TABLE", "POSTGRES_TOKEN_SCHEMA")
    expected = ("stac_api", "images_mvw", "data") if override else (
        "skraafoto_stac", "images", "skraafoto_stac"
    )
    env = {name: value for name, value in os.environ.items() if name not in names}
    if override:
        env.update(zip(names, expected))
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from sqlalchemy.orm import configure_mappers
from stac_fastapi.sqlalchemy.models import database

configure_mappers()
schema, table, token_schema = sys.argv[1:]
assert database.Collection.__table__.schema == schema
assert database.Item.__table__.schema == schema
assert database.Item.__table__.name == table
assert database.PaginationToken.__table__.schema == token_schema
foreign_key = next(iter(database.Item.collection_id.foreign_keys))
assert foreign_key.column is database.Collection.__table__.c.id
""",
            *expected,
        ],
        env=env,
        check=True,
    )
