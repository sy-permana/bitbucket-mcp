"""Tests for configuration validation."""

import os
import pytest

from src.config import BitbucketConfig


@pytest.fixture
def valid_env(monkeypatch):
    """Fixture providing valid environment variables."""
    # Clear any existing values first
    for var in ["BITBUCKET_USERNAME", "BITBUCKET_API_TOKEN", 
                "BITBUCKET_WORKSPACE", "BITBUCKET_REPO_SLUG"]:
        monkeypatch.delenv(var, raising=False)
    
    # Set valid values
    monkeypatch.setenv("BITBUCKET_USERNAME", "test@example.com")
    monkeypatch.setenv("BITBUCKET_API_TOKEN", "test-token-12345")
    monkeypatch.setenv("BITBUCKET_WORKSPACE", "test-workspace")
    monkeypatch.setenv("BITBUCKET_REPO_SLUG", "test-repo")


class TestConfigFromEnvSuccess:
    """Tests for successful configuration loading."""
    
    def test_config_from_env_success(self, valid_env):
        """Test that all 4 env vars are loaded correctly."""
        config = BitbucketConfig.from_env()
        
        assert config.bitbucket_username == "test@example.com"
        assert config.bitbucket_api_token == "test-token-12345"
        assert config.bitbucket_workspace == "test-workspace"
        assert config.bitbucket_repo_slug == "test-repo"


class TestConfigMissingVariables:
    """Tests for missing environment variable handling."""
    
    @pytest.mark.parametrize("missing_var", [
        "BITBUCKET_USERNAME",
        "BITBUCKET_API_TOKEN",
        "BITBUCKET_WORKSPACE",
        "BITBUCKET_REPO_SLUG"
    ])
    def test_config_missing_single_var(self, monkeypatch, valid_env, missing_var):
        """Test that missing each individual var raises ValueError."""
        # Remove one variable
        monkeypatch.delenv(missing_var, raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            BitbucketConfig.from_env()
        
        # Assert missing var name is in message
        assert missing_var in str(exc_info.value)
    
    def test_config_missing_multiple_vars(self, monkeypatch, valid_env):
        """Test that missing multiple vars lists all in error message."""
        # Remove two variables
        monkeypatch.delenv("BITBUCKET_USERNAME", raising=False)
        monkeypatch.delenv("BITBUCKET_API_TOKEN", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            BitbucketConfig.from_env()
        
        error_msg = str(exc_info.value)
        # Assert both missing vars are in message
        assert "BITBUCKET_USERNAME" in error_msg
        assert "BITBUCKET_API_TOKEN" in error_msg
    
    def test_config_all_missing(self, monkeypatch):
        """Test that all missing vars lists all 4 in error message."""
        # Ensure all vars are cleared
        for var in ["BITBUCKET_USERNAME", "BITBUCKET_API_TOKEN", 
                    "BITBUCKET_WORKSPACE", "BITBUCKET_REPO_SLUG"]:
            monkeypatch.delenv(var, raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            BitbucketConfig.from_env()
        
        error_msg = str(exc_info.value)
        # Assert all 4 vars are in message
        assert "BITBUCKET_USERNAME" in error_msg
        assert "BITBUCKET_API_TOKEN" in error_msg
        assert "BITBUCKET_WORKSPACE" in error_msg
        assert "BITBUCKET_REPO_SLUG" in error_msg


class TestConfigErrorMessageFormat:
    """Tests for error message quality."""
    
    def test_config_error_message_contains_configuration_error(self, monkeypatch):
        """Test error message contains 'Configuration error:' prefix."""
        for var in ["BITBUCKET_USERNAME", "BITBUCKET_API_TOKEN", 
                    "BITBUCKET_WORKSPACE", "BITBUCKET_REPO_SLUG"]:
            monkeypatch.delenv(var, raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            BitbucketConfig.from_env()
        
        assert "Configuration error:" in str(exc_info.value)
    
    def test_config_error_message_contains_helpful_descriptions(self, monkeypatch):
        """Test error message contains helpful descriptions for each var."""
        for var in ["BITBUCKET_USERNAME", "BITBUCKET_API_TOKEN", 
                    "BITBUCKET_WORKSPACE", "BITBUCKET_REPO_SLUG"]:
            monkeypatch.delenv(var, raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            BitbucketConfig.from_env()
        
        error_msg = str(exc_info.value)
        # Check for helpful descriptions
        assert "Atlassian email" in error_msg or "email" in error_msg.lower()
        assert "bitbucket.org" in error_msg.lower() or "settings" in error_msg.lower()
        assert "workspace" in error_msg.lower()
        assert "repository" in error_msg.lower() or "repo" in error_msg.lower()
