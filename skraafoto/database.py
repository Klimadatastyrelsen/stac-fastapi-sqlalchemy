"""ORM mapping for the Skraafoto STAC database."""

import json
from typing import Optional

import geoalchemy2 as ga
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.ext.declarative import declarative_base

from stac_fastapi.sqlalchemy.extensions.query import Queryables, QueryableTypes

BaseModel = declarative_base()


class GeojsonGeometry(ga.Geometry):
    """Return database geometry as GeoJSON."""

    from_text = "ST_GeomFromGeoJSON"

    def result_processor(self, dialect: str, coltype):
        def process(value: Optional[bytes]):
            if value is not None:
                geometry = ga.shape.to_shape(
                    ga.elements.WKBElement(
                        value, srid=self.srid, extended=self.extended
                    )
                )
                return json.loads(json.dumps(geometry.__geo_interface__))

        return process


class Collection(BaseModel):
    __tablename__ = "collections"
    __table_args__ = {"schema": "skraafoto_stac"}

    id = sa.Column(sa.VARCHAR(1024), nullable=False, primary_key=True)
    stac_version = sa.Column(sa.VARCHAR(300))
    stac_extensions = sa.Column(sa.ARRAY(sa.VARCHAR(300)))
    title = sa.Column(sa.VARCHAR(1024))
    description = sa.Column(sa.VARCHAR(1024), nullable=False)
    keywords = sa.Column(sa.ARRAY(sa.VARCHAR(300)))
    version = sa.Column(sa.VARCHAR(300))
    license = sa.Column(sa.VARCHAR(300), nullable=False)
    providers = sa.Column(JSONB)
    summaries = sa.Column(JSONB)
    extent = sa.Column(JSONB)
    links = sa.Column(JSONB)
    type = sa.Column(sa.VARCHAR(300), nullable=False)
    children = sa.orm.relationship("Item", lazy="dynamic")


class Item(BaseModel):
    __tablename__ = "images"
    __table_args__ = {"schema": "skraafoto_stac"}

    id = sa.Column(sa.Text, nullable=False, primary_key=True)
    collection_id = sa.Column(
        sa.Text, sa.ForeignKey("skraafoto_stac.collections.id"), nullable=False
    )
    product_id = sa.Column(sa.Text, nullable=False)
    datetime = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    geometry = sa.Column(
        "footprint", GeojsonGeometry("POLYGON", srid=4326), nullable=False
    )
    data_path = sa.Column(sa.Text)
    properties = sa.Column(JSONB, nullable=False)
    # Images have no STAC version column; use the parent collection's version.
    stac_version = sa.orm.column_property(
        sa.select([Collection.stac_version])
        .where(Collection.id == collection_id)
        .correlate_except(Collection)
        .as_scalar()
    )
    stac_extensions = sa.orm.column_property(
        sa.cast(sa.null(), sa.ARRAY(sa.VARCHAR(300)))
    )
    bbox = sa.orm.column_property(
        array(
            [
                sa.func.ST_XMin(sa.func.ST_Envelope(geometry)),
                sa.func.ST_YMin(sa.func.ST_Envelope(geometry)),
                sa.func.ST_XMax(sa.func.ST_Envelope(geometry)),
                sa.func.ST_YMax(sa.func.ST_Envelope(geometry)),
            ]
        )
    )
    assets = sa.orm.column_property(
        sa.func.jsonb_build_object(
            "image",
            sa.func.jsonb_build_object("href", data_path, "type", "image/tiff"),
        )
    )
    links = sa.orm.column_property(sa.cast(sa.null(), JSONB))
    parent_collection = sa.orm.relationship("Collection", back_populates="children")

    @classmethod
    def get_field(cls, field_name):
        try:
            return getattr(cls, field_name)
        except AttributeError:
            return cls.properties[field_name].cast(
                getattr(QueryableTypes, Queryables(field_name).name)
            )


class PaginationToken(BaseModel):
    __tablename__ = "tokens"
    __table_args__ = {"schema": "skraafoto_stac"}

    id = sa.Column(sa.VARCHAR(100), nullable=False, primary_key=True)
    keyset = sa.Column(sa.VARCHAR(1000), nullable=False)
