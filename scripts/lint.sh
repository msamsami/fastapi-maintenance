#!/usr/bin/env bash

set -e
set -x

mypy src/fastapi_maintenance
ruff check src/fastapi_maintenance tests docs_src
ruff format src/fastapi_maintenance tests docs_src --check
