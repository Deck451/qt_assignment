"""Test configuration & fixtures module."""

import pytest
from fastapi.testclient import TestClient

from app.main import application


@pytest.fixture
def client() -> TestClient:
    """Initializing a test client."""
    return TestClient(application)
