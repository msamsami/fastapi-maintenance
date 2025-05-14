#!/usr/bin/env bash

set -e
set -x

uv run coverage run -m pytest tests
uv run coverage combine
uv run coverage report
uv run coverage html
