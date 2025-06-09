# Installation

The first step is to install the package using one of the following methods.

First, make sure you create a virtual environment and activate it.

## Methods

### Using pip

```bash
pip install fastapi-maintenance
```

### Using uv

If you're using uv for dependency management:

```bash
uv add fastapi-maintenance
```

### From Source

For the latest development version, you can install directly from the GitHub repository:

```bash
pip install git+https://github.com/msamsami/fastapi-maintenance.git
```

## Optional Dependencies

If you want to use the command-line interface (CLI), install with the `cli` extra:

```bash
pip install fastapi-maintenance[cli]
```

## Verifying Installation

You can verify the installation by checking the version in Python:

```python
import fastapi_maintenance
print(fastapi_maintenance.__version__)  # Should print the installed version
```

or using the command line if you've installed the CLI extra:

```bash
fastapi-maintenance --version
```

## Next Steps

Now that you have installed FastAPI Maintenance, let's proceed to [First Steps](./first-steps.md) to learn how to add it to your FastAPI application.
