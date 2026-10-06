"""Pagination token client."""
import abc
import logging
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Type

import attr
from sqlalchemy.orm import Session as SqlSession

from stac_fastapi.sqlalchemy.models import database
from stac_fastapi.sqlalchemy.session import Session

logger = logging.getLogger(__name__)


@attr.s
class PaginationTokenClient(abc.ABC):
    """Encode pagination cursors without database storage."""

    session: Session = attr.ib(default=attr.Factory(Session.create_from_env))

    @staticmethod
    @abc.abstractmethod
    def _lookup_id(
        id: str, table: Type[database.BaseModel], session: SqlSession
    ) -> Type[database.BaseModel]:
        """Lookup row by id."""
        ...

    def to_token(self, keyset: str) -> str:  # type:ignore
        """Transform a keyset to a token."""
        # for now just encode the keyset and return it
        return urlsafe_b64encode(
            keyset.encode(encoding="utf-8", errors="strict")
        ).decode("utf-8")

    def from_token(self, token_id: str) -> str:
        """Transform a token to a keyset."""
        return urlsafe_b64decode(token_id).decode("utf-8")