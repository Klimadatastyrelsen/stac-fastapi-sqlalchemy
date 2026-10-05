"""Exercise the real production source with mocked database I/O."""

from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from stac_fastapi.api.models import create_post_request_model
from stac_fastapi.extensions.core import (
    ContextExtension,
    CrsExtension,
    FilterExtension,
    SortExtension,
    TokenPaginationExtension,
)
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
    session.scalar.return_value = 1
    session.execute.return_value.scalar.return_value = 1
    session.execute.return_value.scalars.return_value.first.return_value = None
    reader = SimpleNamespace(context_session=lambda: nullcontext(session))
    client = core.CoreCrudClient(
        session=SimpleNamespace(reader=reader), extensions=[ContextExtension()]
    )
    monkeypatch.setattr(core, "select_page", Mock(return_value=EmptyPage()))
    return client, session


def request_for(products):
    scope = {} if products is None else {"allowed_products": products}
    return SimpleNamespace(
        scope=scope,
        base_url="http://test-server/",
        query_params={},
        _json={},
    )


def search_for(ids=None):
    return SimpleNamespace(
        pt=None,
        collections=["collection"],
        ids=ids,
        limit=10,
        intersects=None,
        bbox=None,
        sortby=None,
        filter=None,
        datetime=None,
    )


@pytest.mark.parametrize("products", [None, [], ["allowed"], ["allowed", "other"]])
@pytest.mark.parametrize("endpoint", ["collection", "item", "search", "ids"])
def test_product_filter_reaches_item_queries(client, endpoint, products):
    crud, session = client
    request = request_for(products)
    if endpoint == "item":
        with pytest.raises(NotFoundError):
            crud.get_item("item", "collection", request=request)
        query = session.execute.call_args.args[0]
    elif endpoint == "collection":
        crud.item_collection("collection", request=request)
        query = core.select_page.call_args.args[1]
    else:
        crud.post_search(
            search_for(["item"] if endpoint == "ids" else None), request=request
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
    assert "stac_api.images_mvw" in sql

    if endpoint == "ids":
        count_query = session.scalar.call_args.args[0]
        count_sql = compile_sql(count_query)
        assert "count(*)" in count_sql
        assert "images_mvw.id = 'item'" in count_sql
        assert "ORDER BY" not in count_sql
        if products is not None:
            assert "product_id IN" in count_sql
    elif endpoint != "item":
        count_sql = compile_sql(session.execute.call_args.args[0])
        if products is not None:
            assert "product_id IN" in count_sql


@pytest.mark.parametrize("matched", [0, 1, 2])
def test_ids_context_uses_database_count_not_requested_ids(client, matched):
    crud, session = client
    session.scalar.return_value = matched
    response = crud.post_search(
        search_for(["item", "item", "missing"]),
        request=request_for(["allowed"]),
    )
    assert response["context"] == {"returned": 0, "limit": 10, "matched": matched}
    session.scalar.assert_called_once()


@pytest.mark.parametrize("products", [None, [], ["allowed"]])
def test_get_search_preserves_product_scope(client, products):
    crud, _ = client
    crud.post_request_model = create_post_request_model(
        [
            ContextExtension(),
            CrsExtension(),
            FilterExtension(),
            SortExtension(),
            TokenPaginationExtension(),
        ]
    )
    crs = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
    response = crud.get_search(
        ids=["item"],
        collections=["collection"],
        crs=crs,
        bbox_crs=crs,
        filter_crs=crs,
        filter_lang="cql-json",
        request=request_for(products),
    )
    sql = compile_sql(core.select_page.call_args.args[1])
    assert ("product_id IN" in sql) == (products is not None)
    if products:
        assert "'allowed'" in sql
    elif products == []:
        assert "1 != 1" in sql
    assert response["links"][0]["method"] == "GET"
    assert response["links"][0]["body"] is None


@pytest.mark.parametrize("srid", [4326, 25832])
def test_production_geometry_and_bbox_expressions(client, srid):
    crud, _ = client
    query = sa.select(database.Item).options(
        crud._geometry_expression(srid), crud._bbox_expression(srid)
    )
    sql = compile_sql(query)
    assert database.Item.__table__.fullname == "stac_api.images_mvw"
    assert database.Item.footprint.type.srid == 4326
    assert database.Item.footprint.type.geometry_type == "POLYGON"
    assert "ST_AsEWKB" in sql
    assert "ST_XMin(ST_Envelope(" in sql
    assert "ST_YMax(ST_Envelope(" in sql
    assert ("ST_Transform" in sql) == (srid != 4326)
    if srid != 4326:
        assert "25832" in sql
    assert [column.name for column in database.Item.__table__.primary_key] == [
        "id",
        "collection_id",
    ]
    assert database.PaginationToken.__table__.schema == "data"


def test_serializer_preserves_geometry_and_adds_product():
    Settings.set(SqlalchemySettings())
    footprint = {
        "type": "Polygon",
        "coordinates": [[[12, 55], [13, 55], [13, 56], [12, 55]]],
    }
    item = database.Item(
        id="item",
        collection_id="collection",
        product_id="allowed",
        properties={"product_id": "stale"},
        datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        footprint=footprint,
        bbox=[Decimal("12"), Decimal("55"), Decimal("13"), Decimal("56")],
        data_path="https://example.test/image.tif",
    )
    result = ItemSerializer.db_to_stac(
        item, ApiTokenHrefBuilder("http://test-server/", None)
    )
    assert result["properties"]["product_id"] == "allowed"
    assert item.properties == {"product_id": "stale"}
    assert result["geometry"] == footprint
    assert result["bbox"] == [12.0, 55.0, 13.0, 56.0]
    assert result["assets"]["data"]["href"] == item.data_path
