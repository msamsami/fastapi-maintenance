import pytest


@pytest.fixture
def anyio_backend():
    """Configure pytest-anyio to use asyncio backend for async tests."""
    return "asyncio"
