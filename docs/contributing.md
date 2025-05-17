# Contributing

First, you might want to see the basic ways to [help FastAPI Maintenance package and get help](help.md).

## Developing

If you already cloned the <a href="https://github.com/msamsami/fastapi-maintenance" class="external-link" target="_blank">fastapi-maintenance repository</a> and you want to deep dive in the code, here are some guidelines to set up your environment.

### Virtual Environment with `uv`

We use `uv` for Python package management. To set up your development environment:

```console
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install Development Dependencies

After activating the environment, install the required development packages:

```console
uv sync --all-extras --all-groups
```

This installs all the dependencies in your environment.

### Format

There is a script that you can run that will format and clean all your code:

```console
bash scripts/format.sh
```

It will also auto-sort all your imports.

## Tests

We use pytest for testing. To run the tests and generate coverage reports:

```console
bash scripts/test.sh
```

This command generates a directory `./htmlcov/`, if you open the file `./htmlcov/index.html` in your browser, you can explore interactively the regions of code that are covered by the tests, and notice if there is any region missing.

## Docs

First, make sure you set up your environment as described above, that will install all the requirements.

### Docs Live

During local development, you can build the documentation site and check for any changes with live-reloading:

```console
mkdocs serve
```

It will serve the documentation on `http://127.0.0.1:8000`.

That way, you can edit the documentation/source files and see the changes live.

### Docs Structure

The documentation uses <a href="https://www.mkdocs.org/" class="external-link" target="_blank">MkDocs</a> with the Material theme.

All the documentation is in Markdown format in the directory `./docs`.

Many of the tutorials have blocks of code. In most cases, these blocks of code are actual complete applications that can be run as is.
