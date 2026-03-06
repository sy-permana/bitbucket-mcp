"""Tests for MCP server initialization and logging configuration."""

import sys
import logging
from unittest.mock import patch, MagicMock

import pytest


class TestLoggingConfiguration:
    """Test logging is configured to stderr before other imports."""
    
    def test_logging_to_stderr(self, mock_env_vars):
        """Test that logging is configured with StreamHandler to stderr."""
        with patch('logging.basicConfig') as mock_basic_config:
            # Import should call basicConfig with stderr handler
            import src.server as server_module
            
            # Verify basicConfig was called
            assert mock_basic_config.called, "logging.basicConfig should be called"
            
            # Get the call arguments
            call_args = mock_basic_config.call_args
            
            # Check handlers parameter contains StreamHandler with sys.stderr
            if 'handlers' in call_args.kwargs:
                handlers = call_args.kwargs['handlers']
            elif len(call_args.args) >= 1:
                handlers = call_args.args[0] if isinstance(call_args.args[0], list) else call_args.kwargs.get('handlers', [])
            else:
                handlers = []
            
            # Should have at least one handler that writes to stderr
            assert any(
                isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
                for h in handlers
            ), "Logging should be configured to use stderr"


class TestServerInitialization:
    """Test server initialization with config and client."""
    
    def test_server_imports_with_valid_config(self, mock_env_vars):
        """Test server can be imported when valid env vars are set."""
        # Should not raise any exceptions
        import src.server as server_module
        
        # Verify mcp instance exists
        assert hasattr(server_module, 'mcp'), "Server should have mcp instance"
        assert server_module.mcp is not None, "mcp should not be None"
    
    def test_mcp_instance_created(self, mock_env_vars):
        """Test FastMCP instance is created with correct name."""
        from mcp.server.fastmcp import FastMCP
        import src.server as server_module
        
        assert isinstance(server_module.mcp, FastMCP), "mcp should be FastMCP instance"
        # The name is set during initialization
        assert server_module.mcp.name == "bitbucket-pr-manager", \
            f"Expected name 'bitbucket-pr-manager', got '{server_module.mcp.name}'"
    
    def test_config_loaded_on_import(self, mock_env_vars):
        """Test config is loaded when server is imported."""
        import src.server as server_module
        
        # Config should be accessible
        assert hasattr(server_module, 'config'), "Server should have config"
        assert server_module.config is not None, "config should not be None"
        assert server_module.config.bitbucket_workspace == "test-workspace"


class TestServerErrorHandling:
    """Test server handles missing configuration gracefully."""
    
    def test_server_exits_on_missing_config(self, mock_missing_env):
        """Test server exits with error when config is missing."""
        with patch('sys.exit') as mock_exit:
            with patch('logging.getLogger') as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                
                # Import should trigger config validation and exit
                try:
                    import importlib
                    import src.server
                    importlib.reload(src.server)
                except SystemExit:
                    pass  # Expected
                
                # Verify sys.exit was called with error code
                mock_exit.assert_called_once()
                exit_call = mock_exit.call_args[0][0]
                assert exit_call == 1, f"Expected exit code 1, got {exit_call}"


class TestClientInitialization:
    """Test Bitbucket client is initialized with config."""
    
    def test_client_initialized(self, mock_env_vars):
        """Test BitbucketClient is created with config."""
        import src.server as server_module
        
        assert hasattr(server_module, 'bitbucket_client'), \
            "Server should have bitbucket_client"
        assert server_module.bitbucket_client is not None, \
            "bitbucket_client should not be None"
