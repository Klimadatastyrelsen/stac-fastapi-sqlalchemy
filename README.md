# stac-fastapi-sqlalchemy

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/stac-utils/stac-fastapi-sqlalchemy/cicd.yaml?style=for-the-badge)](https://github.com/stac-utils/stac-fastapi-sqlalchemy/actions/workflows/cicd.yaml)
[![PyPI](https://img.shields.io/pypi/v/stac-fastapi.sqlalchemy?style=for-the-badge)](https://pypi.org/project/stac-fastapi.sqlalchemy)
[![Documentation](https://img.shields.io/github/actions/workflow/status/stac-utils/stac-fastapi-sqlalchemy/pages.yml?label=Docs&style=for-the-badge)](https://stac-utils.github.io/stac-fastapi-sqlalchemy/)
[![License](https://img.shields.io/github/license/stac-utils/stac-fastapi-sqlalchemy?style=for-the-badge)](https://github.com/stac-utils/stac-fastapi-sqlalchemy/blob/main/LICENSE)

[SQLAlchemy](https://www.sqlalchemy.org/) backend for [stac-fastapi](https://github.com/stac-utils/stac-fastapi), the [FastAPI](https://fastapi.tiangolo.com/) implementation of the [STAC API spec](https://github.com/radiantearth/stac-api-spec)
The SQLAlchemy backend requires **PostGIS>=3**.

## Overview

**stac-fastapi-sqlalchemy** is an HTTP interface built in FastAPI.

## Local Skraafoto database

`docker-compose.skraafoto.yml` requires the existing local
`skraafoto-stac-fastapi:oidc` image, including its `oidc_app:app` wrapper, and
mounts the older-schema adapter in `skraafoto/database.py`.

The local `skraafoto` database on port 5439 must already contain the
`skraafoto_stac` collections, images, and pagination-token table. Set
`POSTGRES_PASS` and configure an external OIDC provider matching `AUTH_ISSUER`,
`AUTH_AUDIENCE`, and `AUTH_JWKS_URL` in the Compose file, then run:

```bash
docker compose -f docker-compose.skraafoto.yml up -d
```

The API is available at <http://localhost:8081>. No schema changes or seed data
are applied. This image does not validate the merged source, which uses
`stac_api.images_mvw` and a different footprint/CRS serializer. Do not rebuild
against the Skraafoto database without verifying schema/serializer compatibility.

For DB-free source tests, install this package and the matching
Klimadatastyrelsen/Septima `stac-fastapi` API, types, and extensions sources
in an isolated Python 3.11 environment:

```bash
python -m pytest --confcutdir=tests/unit tests/unit
```

The cutoff excludes database-backed fixtures and cleanup writes. Upstream
STAC 2.4.8 lacks the production source's href-builder and CRS APIs.

## Contributing

See [CONTRIBUTING](https://github.com/stac-utils/stac-fastapi-sqlalchemy/blob/main/CONTRIBUTING.md) for detailed contribution instructions.

To install:

```shell
git clone https://github.com/stac-utils/stac-fastapi-sqlalchemy
cd stac-fastapi-sqlalchemy
pip install -e ".[dev,server,docs]"
```

To test:

```shell
make test
```

Use Github [Pull Requests](https://github.com/stac-utils/stac-fastapi-sqlalchemy/pulls) to provide new features or to request review of draft code, and use [Issues](https://github.com/stac-utils/stac-fastapi-sqlalchemy/issues) to report bugs or request new features.

### Documentation

To build the docs:

```shell
make docs
```

Then, serve the docs via a local HTTP server:

```shell
mkdocs serve
```

## History

In April of 2023, it was removed from the core **stac-fastapi** repository and moved to its current location (<http://github.com/stac-utils/stac-fastapi-sqlalchemy>).

## License

[MIT](https://github.com/stac-utils/stac-fastapi-sqlalchemy/blob/main/LICENSE)

<!-- markdownlint-disable-file MD033 -->
