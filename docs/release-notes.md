# Release Notes

## Latest Changes

## 0.0.5

### Internal

- ⬆ Bump package dependencies. PR [#25](https://github.com/msamsami/fastapi-maintenance/pull/25) by [@msamsami](https://github.com/msamsami).
- 👷 Fix the order of running `coverage xml` command in the Coverage GitHub Action. PR [#22](https://github.com/msamsami/fastapi-maintenance/pull/22) by [@msamsami](https://github.com/msamsami).
- 👷 Remove unnecessary steps and configurations from the Coverage GitHub Action. PR [#21](https://github.com/msamsami/fastapi-maintenance/pull/21) by [@msamsami](https://github.com/msamsami).
- 🔧 Reformat pre-commit config file. PR [#18](https://github.com/msamsami/fastapi-maintenance/pull/18) by [@msamsami](https://github.com/msamsami).

### Refactors

- ✏️ Add LRU caching to route existence checking logic and improve tracking of application route changes. PR [#24](https://github.com/msamsami/fastapi-maintenance/pull/24) by [@msamsami](https://github.com/msamsami).
- ✏️ Refactor path matching logic and add LRU caching. PR [#23](https://github.com/msamsami/fastapi-maintenance/pull/23) by [@msamsami](https://github.com/msamsami).

### Docs

- 📝 Add sections for installing `uv` and making contributions to the Contributing page. PR [#20](https://github.com/msamsami/fastapi-maintenance/pull/20) by [@msamsami](https://github.com/msamsami).
- 📝 Fix duplicate contributing section in Help page. PR [#19](https://github.com/msamsami/fastapi-maintenance/pull/19) by [@msamsami](https://github.com/msamsami).

## 0.0.4

### Docs

- 📝 Add docs for package CLI. PR [#17](https://github.com/msamsami/fastapi-maintenance/pull/17) by [@msamsami](https://github.com/msamsami).
- 📝 Add experimental status warning and improve features section presentation. PR [#14](https://github.com/msamsami/fastapi-maintenance/pull/14) by [@msamsami](https://github.com/msamsami).

### Internal

- 👷 Fix test coverage configurations and remove all `# pragma: no cover` comments from tests. PR [#16](https://github.com/msamsami/fastapi-maintenance/pull/16) by [@msamsami](https://github.com/msamsami).
- 🛠️ Remove Dependabot configuration (`dependabot.yml`) as it doesn't fully support `uv`. PR [#12](https://github.com/msamsami/fastapi-maintenance/pull/12) by [@msamsami](https://github.com/msamsami).

### Features

- ✨ Add initial version of package CLI. PR [#15](https://github.com/msamsami/fastapi-maintenance/pull/15) by [@msamsami](https://github.com/msamsami).

## 0.0.3

### Fixes

- 🐛 Fix bug where non-existent routes return maintenance response instead of correct HTTP error. PR [#11](https://github.com/msamsami/fastapi-maintenance/pull/11) by [@msamsami](https://github.com/msamsami).
- 🐛 Fix bug where FastAPI documentation endpoints become inaccessible during maintenance mode. PR [#10](https://github.com/msamsami/fastapi-maintenance/pull/10) by [@msamsami](https://github.com/msamsami).

### Docs

- 📝 Fix incorrect references to "callback" instead of "handler" in docs. PR [#8](https://github.com/msamsami/fastapi-maintenance/pull/8) by [@Attakay78](https://github.com/Attakay78).
- 📝 Fix pull request URL in release notes. PR [#7](https://github.com/msamsami/fastapi-maintenance/pull/7) by [@msamsami](https://github.com/msamsami).
- 📝 Improve documentation with clearer examples, expanded tutorials, and better organization. PR [#3](https://github.com/msamsami/fastapi-maintenance/pull/3) by [@msamsami](https://github.com/msamsami).

### Internal

- 🔨 Make `_str_to_bool` method static in `BaseStateBackend` class. PR [#6](https://github.com/msamsami/fastapi-maintenance/pull/6) by [@msamsami](https://github.com/msamsami).
- 🔧 Merge test dependencies into dev group and add Ruff linting configuration. PR [#4](https://github.com/msamsami/fastapi-maintenance/pull/4) by [@msamsami](https://github.com/msamsami).
- 🛠️ Add Dependabot configuration for package updates using `uv`. PR [#2](https://github.com/msamsami/fastapi-maintenance/pull/2) by [@msamsami](https://github.com/msamsami).

## 0.0.2

### Fixes

- 🐛 Fix Pydantic v2 raises `ImportError: cannot import name 'BoolError' from 'pydantic'`. PR [#1](https://github.com/msamsami/fastapi-maintenance/pull/1) by [@msamsami](https://github.com/msamsami).

## 0.0.1

- First release. 🎉
