#!/bin/sh -e
set -x

uv run ruff check src/fastapi_maintenance tests docs_src --fix
uv run ruff format src/fastapi_maintenance tests docs_src
