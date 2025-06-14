# Contributing

We welcome contributions from the community to help improve FastAPI Maintenance.

First, you might want to see the basic ways to [help FastAPI Maintenance package and get help](help.md).

## Developing

If you already cloned the <a href="https://github.com/msamsami/fastapi-maintenance" class="external-link" target="_blank">fastapi-maintenance repository</a> and you want to deep dive in the code, here are some guidelines to set up your environment.

### Install `uv`

We use `uv` for Python dependency management. If you don't have `uv` installed, follow the instructions on the <a href="https://docs.astral.sh/uv/guides/install-python" class="external-link" target="_blank">official uv website</a>.

Once `uv` is installed, navigate to the cloned repository.

### Set up Virtual Environment

To set up your development virtual environment with `uv`:

```bash
uv venv
source .venv/bin/activate
```

### Install Dependencies

After activating the environment, install the required package and development dependencies:

```bash
uv sync --all-extras --all-groups
```

This installs all the dependencies in your environment.

### Format

There is a script that you can run that will format and clean all your code:

```bash
bash scripts/format.sh
```

## Tests

We use pytest for testing. To run the tests and generate coverage reports:

```bash
bash scripts/test.sh
```

This command generates a directory `./htmlcov/`, if you open the file `./htmlcov/index.html` in your browser, you can explore interactively the regions of code that are covered by the tests, and notice if there is any region missing.

## Docs

First, make sure you set up your environment as described above, that will install all the requirements.

### Docs Live

During local development, you can build the documentation site and check for any changes with live-reloading:

```bash
mkdocs serve
```

It will serve the documentation on `http://127.0.0.1:8000`.

That way, you can edit the documentation/source files and see the changes live.

### Docs Structure

The documentation uses <a href="https://www.mkdocs.org/" class="external-link" target="_blank">MkDocs</a> with the Material theme.

All the documentation is in Markdown format in the directory `./docs`.

Many of the tutorials have blocks of code. In most cases, these blocks of code are actual complete applications that can be run as is.

## Making Contributions

### Coding Standards

We try to maintain high code quality standards to ensure consistency across the project:

- Follow PEP 8 guidelines.
- Write meaningful tests for new features or bug fixes.

### Creating a Pull Request

After making your changes:

- Push your changes to your fork.
- Open a pull request with a clear description of your changes.
- Update the documentation if necessary.

### Code Reviews

Your contributions will go through our review process:

- Address any feedback from code reviews.
- Once approved, your contributions will be merged into the main branch.

Thank you for contributing to FastAPI Maintenance 🚀
