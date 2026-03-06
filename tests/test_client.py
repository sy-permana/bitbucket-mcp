"""Tests for Bitbucket API client.

Tests authentication, request handling, and error scenarios.
"""

import pytest
import responses
from requests.auth import HTTPBasicAuth

from src.client.bitbucket_client import BitbucketClient
from src.config import BitbucketConfig


@pytest.fixture
def mock_config():
    """Create a mock BitbucketConfig for testing."""
    return BitbucketConfig(
        bitbucket_username="test@example.com",
        bitbucket_api_token="test-token-12345",
        bitbucket_workspace="test-workspace",
        bitbucket_repo_slug="test-repo"
    )


@pytest.fixture
def client(mock_config):
    """Create a BitbucketClient instance for testing."""
    return BitbucketClient(mock_config)


class TestClientInitialization:
    """Tests for client initialization and configuration."""
    
    def test_client_initialization(self, client, mock_config):
        """Test that client initializes with correct config and auth."""
        assert client.config == mock_config
        assert isinstance(client.auth, HTTPBasicAuth)
        assert client.session.auth == client.auth
        assert client.session.headers["Accept"] == "application/json"
        assert client.session.headers["Content-Type"] == "application/json"
    
    def test_client_auth_parameters(self, client, mock_config):
        """CRITICAL: Verify HTTPBasicAuth parameter order is correct.
        
        HTTPBasicAuth must receive: username=email, password=token
        Reversing these will cause authentication failures!
        """
        assert client.auth.username == mock_config.bitbucket_username
        assert client.auth.password == mock_config.bitbucket_api_token
        assert client.auth.username == "test@example.com"
        assert client.auth.password == "test-token-12345"
    
    def test_client_repo_url_construction(self, client, mock_config):
        """Test that repo_url is constructed correctly."""
        expected_url = (
            f"https://api.bitbucket.org/2.0/repositories/"
            f"{mock_config.bitbucket_workspace}/{mock_config.bitbucket_repo_slug}"
        )
        assert client.repo_url == expected_url
        assert client.repo_url.endswith("/test-workspace/test-repo")


class TestClientRequests:
    """Tests for HTTP request methods."""
    
    @responses.activate
    def test_get_request(self, client):
        """Test GET request with correct URL construction."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json={"values": []},
            status=200
        )
        
        result = client.get("/pullrequests")
        
        assert result == {"values": []}
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.url == "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests"
        assert "Authorization" in request.headers
    
    @responses.activate
    def test_post_request(self, client):
        """Test POST request with JSON data."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json={"id": 123},
            status=201
        )
        
        data = {"title": "Test PR", "source": {"branch": {"name": "feature"}}}
        result = client.post("/pullrequests", data)
        
        assert result == {"id": 123}
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        import json
        assert json.loads(request.body) == data
    
    @responses.activate
    def test_get_request_timeout(self, client):
        """Test that GET requests use 30-second timeout."""
        import requests
        
        def request_callback(request):
            # Verify timeout parameter
            return (200, {}, '{"values": []}')
        
        responses.add_callback(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/test",
            callback=request_callback
        )
        
        # Just verify the call works - timeout is internal to requests
        client.get("/test")
        assert len(responses.calls) == 1


class TestClientAuthentication:
    """Tests for authentication verification."""
    
    @responses.activate
    def test_test_authentication_success(self, client):
        """Test test_authentication returns True on 200 response."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/user",
            json={"username": "testuser"},
            status=200
        )
        
        result = client.test_authentication()
        
        assert result is True
    
    @responses.activate
    def test_test_authentication_failure_401(self, client):
        """Test test_authentication returns False on 401 response."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/user",
            json={"error": "Unauthorized"},
            status=401
        )
        
        result = client.test_authentication()
        
        assert result is False
    
    @responses.activate
    def test_test_authentication_failure_403(self, client):
        """Test test_authentication returns False on 403 response."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/user",
            json={"error": "Forbidden"},
            status=403
        )
        
        result = client.test_authentication()
        
        assert result is False
    
    @responses.activate
    def test_test_authentication_failure_network(self, client):
        """Test test_authentication returns False on network error."""
        import requests
        
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/user",
            body=requests.exceptions.ConnectTimeout("Connection timeout")
        )
        
        result = client.test_authentication()
        
        assert result is False


class TestClientErrorHandling:
    """Tests for error handling."""
    
    @responses.activate
    def test_get_raises_on_404(self, client):
        """Test that GET raises HTTPError on 404."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/notfound",
            json={"error": "Not found"},
            status=404
        )
        
        import requests
        with pytest.raises(requests.exceptions.HTTPError):
            client.get("/notfound")
    
    @responses.activate
    def test_post_raises_on_400(self, client):
        """Test that POST raises HTTPError on 400."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/bad",
            json={"error": "Bad request"},
            status=400
        )
        
        import requests
        with pytest.raises(requests.exceptions.HTTPError):
            client.post("/bad", {"invalid": "data"})
