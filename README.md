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

Use the existing `skraafoto-stac-fastapi:oidc` image and local `skraafoto`
database (port 5439, schema `skraafoto_stac`). The Compose file mounts the
image-compatible adapter at `skraafoto/database.py`. Set `POSTGRES_PASS` and
configure `AUTH_ISSUER`, `AUTH_AUDIENCE`, and `AUTH_JWKS_URL` for your OIDC
provider, then run:

```bash
docker compose -f docker-compose.skraafoto.yml up -d
```

No schema changes or seed data are applied. The merged source uses a different
schema and footprint/CRS serializer; verify compatibility before using it with
this database.

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
