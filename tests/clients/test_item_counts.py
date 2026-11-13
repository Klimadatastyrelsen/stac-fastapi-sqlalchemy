"""The sync's precomputed item counts stand in for the live count."""
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

from stac_fastapi.sqlalchemy.core import CoreCrudClient

SCHEMA = "item_counts_test"


class Item(declarative_base()):
    __tablename__ = "images"
    __table_args__ = {"schema": SCHEMA}
    id = sa.Column(sa.Integer, primary_key=True)


@pytest.fixture(autouse=True)
def cleanup():
    # overrides the conftest cleanup, which needs the joplin data this test does not use
    yield


def test_precomputed_count(db_session):
    counts = sa.table(
        "image_counts",
        sa.column("collection_id"),
        sa.column("product_id"),
        sa.column("n"),
        sa.column("images_oid"),
        schema=SCHEMA,
    )
    client = CoreCrudClient(session=db_session, item_table=Item, count_table=counts)
    with db_session.reader.context_session() as s:
        s.execute(
            sa.text(
                f"""CREATE SCHEMA {SCHEMA};
                CREATE TABLE {SCHEMA}.images AS SELECT * FROM (VALUES
                    ('a', NULL), ('a', NULL), ('a', 'p1'), ('a', 'p2'), ('b', 'p1'), ('b', NULL)
                ) v (collection_id, product_id);
                CREATE TABLE {SCHEMA}.image_counts AS
                SELECT collection_id, product_id, count(*) AS n, '{SCHEMA}.images'::regclass::oid AS images_oid
                FROM {SCHEMA}.images GROUP BY collection_id, product_id"""
            )
        )

        def count(collection_ids, scope):
            return client._precomputed_count(
                s, SimpleNamespace(scope=scope), collection_ids
            )

        assert count(["a"], {}) == 4
        assert count(["a"], {"allowed_products": ["p1"]}) == 3
        assert count(None, {"allowed_products": []}) == 3

        # a new sync swaps in another images table; the old counts must not be used
        s.execute(sa.text(f"ALTER TABLE {SCHEMA}.images RENAME TO old_images"))
        s.execute(sa.text(f"CREATE TABLE {SCHEMA}.images AS TABLE {SCHEMA}.old_images"))
        assert count(["a"], {}) is None
        s.rollback()
