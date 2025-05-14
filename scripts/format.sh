#!/bin/sh -e
set -x

ruff check src/fastapi_maintenance tests docs_src --fix
ruff format src/fastapi_maintenance tests docs_src
