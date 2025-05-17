#!/usr/bin/env bash

set -e
set -x

uv run mypy src/fastapi_maintenance
uv run ruff check src/fastapi_maintenance tests
uv run ruff format src/fastapi_maintenance tests --check
