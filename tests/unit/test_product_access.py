"""Product restrictions on item queries and serialization."""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql
from stac_fastapi.extensions.core import ContextExtension
from stac_fastapi.types.config import Settings
from stac_fastapi.types.errors import NotFoundError

from stac_fastapi.sqlalchemy import core
from stac_fastapi.sqlalchemy.config import SqlalchemySettings
from stac_fastapi.sqlalchemy.models import database
from stac_fastapi.sqlalchemy.serializers import ItemSerializer
from stac_fastapi.sqlalchemy.types.links import ApiTokenHrefBuilder


class EmptyPage(list):
    paging = SimpleNamespace(has_next=False, has_previous=False)


def compile_sql(query):
    return str(
        query.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


@pytest.fixture
def client(monkeypatch):
    session = Mock()
    session.scalar.return_value = 0
    session.execute.return_value.scalar.return_value = 1
    session.execute.return_value.scalars.return_value.first.return_value = None
    reader = SimpleNamespace(context_session=lambda: nullcontext(session))
    client = core.CoreCrudClient(
        session=SimpleNamespace(reader=reader), extensions=[ContextExtension()]
    )
    monkeypatch.setattr(core, "select_page", Mock(return_value=EmptyPage()))
    return client, session


@pytest.mark.parametrize("products", [None, [], ["allowed", "other"]])
@pytest.mark.parametrize("endpoint", ["collection", "item", "search", "ids"])
def test_product_filter_reaches_item_queries(client, endpoint, products):
    crud, session = client
    request = SimpleNamespace(
        scope={} if products is None else {"allowed_products": products},
        base_url="http://test-server/",
        query_params={},
        _json={},
    )
    if endpoint == "item":
        with pytest.raises(NotFoundError):
            crud.get_item("item", "collection", request=request)
        query = session.execute.call_args.args[0]
    elif endpoint == "collection":
        crud.item_collection("collection", request=request)
        query = core.select_page.call_args.args[1]
    else:
        response = crud.post_search(
            SimpleNamespace(
                pt=None, collections=["collection"],
                ids=["item"] if endpoint == "ids" else None,
                limit=10, intersects=None, bbox=None, sortby=None,
                filter=None, datetime=None,
            ),
            request=request,
        )
        query = core.select_page.call_args.args[1]

    sql = compile_sql(query)
    if products is None:
        assert "product_id IN" not in sql
    elif not products:
        assert "product_id IN (NULL) AND (1 != 1)" in sql
    else:
        assert "product_id IN (" in sql
        for product in products:
            assert f"'{product}'" in sql
    if endpoint == "ids":
        assert response["context"]["matched"] == 0
        count_sql = compile_sql(session.scalar.call_args.args[0])
        assert "count(*)" in count_sql
        assert ".id = 'item'" in count_sql
        assert "ORDER BY" not in count_sql
        assert ".bbox" not in count_sql
    elif endpoint != "item":
        count_sql = compile_sql(session.execute.call_args.args[0])
    if endpoint != "item":
        assert ("product_id IN" in count_sql) == (products is not None)
        if products == []:
            assert "1 != 1" in count_sql
        for product in products or []:
            assert f"'{product}'" in count_sql


def test_serializer_uses_product_column_without_mutating_properties():
    Settings.set(SqlalchemySettings())
    item = database.Item(
        id="item",
        collection_id="collection",
        product_id="allowed",
        properties={"product_id": "stale"},
        datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        data_path="https://example.test/image.tif",
    )
    result = ItemSerializer.db_to_stac(
        item, ApiTokenHrefBuilder("http://test-server/", None)
    )
    assert result["properties"]["product_id"] == "allowed"
    assert item.properties == {"product_id": "stale"}
