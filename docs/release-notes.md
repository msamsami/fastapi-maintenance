# Release Notes

## Latest Changes

## 0.0.3

### Fixes

- Fix bug where non-existent routes return maintenance response instead of correct HTTP error. PR [#11](https://github.com/msamsami/fastapi-maintenance/pull/11) by [@msamsami](https://github.com/msamsami).
- Fix bug where FastAPI documentation endpoints become inaccessible during maintenance mode. PR [#10](https://github.com/msamsami/fastapi-maintenance/pull/10) by [@msamsami](https://github.com/msamsami).

### Docs

- Fix incorrect references to "callback" instead of "handler" in docs. PR [#8](https://github.com/msamsami/fastapi-maintenance/pull/8) by [@Attakay78](https://github.com/Attakay78).
- Fix pull request URL in release notes. PR [#7](https://github.com/msamsami/fastapi-maintenance/pull/7) by [@msamsami](https://github.com/msamsami).
- Improve documentation with clearer examples, expanded tutorials, and better organization. PR [#3](https://github.com/msamsami/fastapi-maintenance/pull/3) by [@msamsami](https://github.com/msamsami).

### Internal

- Make `_str_to_bool` method static in `BaseStateBackend` class. PR [#6](https://github.com/msamsami/fastapi-maintenance/pull/6) by [@msamsami](https://github.com/msamsami).
- Merge test dependencies into dev group and add Ruff linting configuration. PR [#4](https://github.com/msamsami/fastapi-maintenance/pull/4) by [@msamsami](https://github.com/msamsami).
- Add Dependabot configuration for package updates using `uv`. PR [#2](https://github.com/msamsami/fastapi-maintenance/pull/2) by [@msamsami](https://github.com/msamsami).

## 0.0.2

### Fixes

- Fix compatibility with different versions of Pydantic. PR [#1](https://github.com/msamsami/fastapi-maintenance/pull/1) by [@msamsami](https://github.com/msamsami).

### Internal

- Add `.python-version` file for development purposes. PR [#1](https://github.com/msamsami/fastapi-maintenance/pull/1) by [@msamsami](https://github.com/msamsami).

## 0.0.1

- First release. 🎉
