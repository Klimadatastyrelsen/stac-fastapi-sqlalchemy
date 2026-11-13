"""The sync's precomputed item counts must equal the live count they stand in for."""
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

from stac_fastapi.sqlalchemy.core import CoreCrudClient

SCHEMA = "item_counts_test"
Base = declarative_base()


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = {"schema": SCHEMA}
    id = sa.Column(sa.VARCHAR, primary_key=True)


class Item(Base):
    __tablename__ = "images"
    __table_args__ = {"schema": SCHEMA}
    id = sa.Column(sa.VARCHAR, primary_key=True)
    collection_id = sa.Column(sa.VARCHAR, sa.ForeignKey(Collection.id))
    product_id = sa.Column(sa.VARCHAR, nullable=True)


COUNTS = sa.table(
    "image_counts",
    sa.column("collection_id"),
    sa.column("product_id"),
    sa.column("n"),
    sa.column("images_oid"),
    schema=SCHEMA,
)

# the dagster image_counts sql, schema swapped
BUILD_COUNTS = f"""CREATE TABLE {SCHEMA}.image_counts AS
SELECT collection_id, product_id, count(*) AS n, '{SCHEMA}.images'::regclass::oid AS images_oid
FROM {SCHEMA}.images
GROUP BY collection_id, product_id"""

ROWS = {"a": [None, None, None, "p1", "p1", "p2"], "b": ["p1", "p1", None], "c": []}


@pytest.fixture(autouse=True)
def cleanup():
    # overrides the conftest cleanup, which needs the joplin data this test does not use
    yield


@pytest.fixture
def client(db_session):
    with db_session.reader.context_session() as s:
        s.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        s.execute(sa.text(f"CREATE SCHEMA {SCHEMA}"))
        Base.metadata.create_all(s.connection())
        s.execute(sa.insert(Collection), [{"id": c} for c in ROWS])
        s.execute(
            sa.insert(Item),
            [
                {"id": f"{c}{i}", "collection_id": c, "product_id": p}
                for c, products in ROWS.items()
                for i, p in enumerate(products)
            ],
        )
        s.execute(sa.text(BUILD_COUNTS))
    yield CoreCrudClient(
        session=db_session,
        item_table=Item,
        collection_table=Collection,
        count_table=COUNTS,
    )
    with db_session.reader.context_session() as s:
        s.execute(sa.text(f"DROP SCHEMA {SCHEMA} CASCADE"))


def _live_count(client, session, request, collection_ids):
    query = sa.select(Item)
    if collection_ids is not None:
        query = query.join(Collection).filter(Collection.id.in_(collection_ids))
    query = client._filter_products(query, request)
    # without maintain_column_froms an unfiltered count loses its FROM and returns 1
    count = query.with_only_columns(
        sa.func.count(), maintain_column_froms=True
    ).order_by(None)
    return session.execute(count).scalar()


@pytest.mark.parametrize("products", [None, ["p1"], ["p1", "p2"], []])
@pytest.mark.parametrize("collection_ids", [["a"], ["a", "b"], ["c"], None])
def test_precomputed_count_matches_live(client, db_session, products, collection_ids):
    request = SimpleNamespace(
        scope={} if products is None else {"allowed_products": products}
    )
    with db_session.reader.context_session() as s:
        live = _live_count(client, s, request, collection_ids)
        assert client._precomputed_count(s, request, collection_ids) == live


def test_counts_from_a_replaced_item_table_are_ignored(client, db_session):
    with db_session.reader.context_session() as s:
        s.execute(sa.text(f"CREATE TABLE {SCHEMA}.images_new AS TABLE {SCHEMA}.images"))
        s.execute(sa.text(f"ALTER TABLE {SCHEMA}.images RENAME TO images_old"))
        s.execute(sa.text(f"ALTER TABLE {SCHEMA}.images_new RENAME TO images"))
    with db_session.reader.context_session() as s:
        assert client._precomputed_count(s, SimpleNamespace(scope={}), ["a"]) is None


def test_no_count_table_means_live_count(db_session):
    client = CoreCrudClient(
        session=db_session,
        item_table=Item,
        collection_table=Collection,
        count_table=None,
    )
    with db_session.reader.context_session() as s:
        assert client._precomputed_count(s, SimpleNamespace(scope={}), ["a"]) is None
