"""Shared pytest fixtures for Bitbucket PR Manager tests."""

import pytest

from src.config import BitbucketConfig
from src.client import BitbucketClient


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set all 4 required environment variables to test values."""
    env_vars = {
        "BITBUCKET_USERNAME": "test@example.com",
        "BITBUCKET_API_TOKEN": "ATCTT3xFf_test_token",
        "BITBUCKET_WORKSPACE": "test-workspace",
        "BITBUCKET_REPO_SLUG": "test-repo",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def bitbucket_config(mock_env_vars):
    """Return BitbucketConfig instance with mocked environment."""
    return BitbucketConfig.from_env()


@pytest.fixture
def bitbucket_client(bitbucket_config):
    """Return BitbucketClient instance with test config."""
    return BitbucketClient(bitbucket_config)


@pytest.fixture
def mock_missing_env(monkeypatch):
    """Fixture that unsets all 4 env vars for error testing."""
    env_vars = [
        "BITBUCKET_USERNAME",
        "BITBUCKET_API_TOKEN",
        "BITBUCKET_WORKSPACE",
        "BITBUCKET_REPO_SLUG",
    ]
    for key in env_vars:
        monkeypatch.delenv(key, raising=False)
    return env_vars
