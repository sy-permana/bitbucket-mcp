"""Tests for Bitbucket PR read operations.

Tests list_prs and get_pr tools with mocked Bitbucket API responses.
"""

import pytest
import responses
import requests


@pytest.fixture
def mock_pr_list_response():
    """Sample Bitbucket PR list API response."""
    return {
        "values": [
            {
                "id": 42,
                "title": "Add authentication feature",
                "state": "OPEN",
                "author": {
                    "display_name": "John Doe"
                },
                "source": {
                    "branch": {
                        "name": "feature/auth"
                    }
                },
                "destination": {
                    "branch": {
                        "name": "main"
                    }
                },
                "created_on": "2024-01-15T10:30:00.000+00:00",
                "comment_count": 5
            },
            {
                "id": 41,
                "title": "Fix bug in login",
                "state": "MERGED",
                "author": {
                    "display_name": "Jane Smith"
                },
                "source": {
                    "branch": {
                        "name": "bugfix/login"
                    }
                },
                "destination": {
                    "branch": {
                        "name": "main"
                    }
                },
                "created_on": "2024-01-14T09:00:00.000+00:00",
                "comment_count": 2
            },
            {
                "id": 40,
                "title": "Update documentation",
                "state": "DECLINED",
                "author": {
                    "display_name": "Bob Wilson"
                },
                "source": {
                    "branch": {
                        "name": "docs/update"
                    }
                },
                "destination": {
                    "branch": {
                        "name": "main"
                    }
                },
                "created_on": "2024-01-13T08:00:00.000+00:00",
                "comment_count": 0
            }
        ],
        "pagelen": 20,
        "size": 3
    }


@pytest.fixture
def mock_pr_detail_response():
    """Sample single PR API response."""
    return {
        "id": 42,
        "title": "Add authentication feature",
        "state": "OPEN",
        "author": {
            "display_name": "John Doe"
        },
        "source": {
            "branch": {
                "name": "feature/auth"
            }
        },
        "destination": {
            "branch": {
                "name": "main"
            }
        },
        "created_on": "2024-01-15T10:30:00.000+00:00",
        "updated_on": "2024-01-16T14:45:00.000+00:00",
        "comment_count": 5,
        "description": "This PR adds OAuth2 authentication support.\n\nChanges:\n- Add auth middleware\n- Add login endpoint\n- Add tests",
        "reviewers": [
            {"display_name": "Jane Smith"},
            {"display_name": "Bob Wilson"}
        ]
    }


class TestListPullRequests:
    """Tests for bitbucket_list_pull_requests tool."""
    
    @responses.activate
    def test_list_prs_success(self, mock_env_vars, mock_pr_list_response):
        """Test list_prs returns formatted PR list."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json=mock_pr_list_response,
            status=200
        )
        
        # Import after mocking environment
        from src.server import bitbucket_list_pull_requests
        
        result = bitbucket_list_pull_requests()
        
        # Should be a string (not dict/JSON)
        assert isinstance(result, str)
        # Should contain PR info
        assert "PR #42" in result
        assert "Add authentication feature" in result
        assert "John Doe" in result
        assert "OPEN" in result
        # Should have multiple PRs
        assert "PR #41" in result
        assert "PR #40" in result
    
    @responses.activate
    def test_list_prs_with_state_filter(self, mock_env_vars, mock_pr_list_response):
        """Test list_prs with state filter filters correctly."""
        # Filter to only return OPEN PRs
        open_prs = {
            "values": [pr for pr in mock_pr_list_response["values"] if pr["state"] == "OPEN"],
            "pagelen": 20,
            "size": 1
        }
        
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json=open_prs,
            status=200
        )
        
        from src.server import bitbucket_list_pull_requests
        
        result = bitbucket_list_pull_requests(state="open")
        
        assert isinstance(result, str)
        assert "PR #42" in result
        assert "OPEN" in result
        # Should not have MERGED or DECLINED PRs
        assert "MERGED" not in result or "State: MERGED" not in result
    
    @responses.activate
    def test_list_prs_empty_result(self, mock_env_vars):
        """Test list_prs returns 'No pull requests found' when empty."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json={"values": [], "pagelen": 20, "size": 0},
            status=200
        )
        
        from src.server import bitbucket_list_pull_requests
        
        result = bitbucket_list_pull_requests()
        
        assert isinstance(result, str)
        assert "No pull requests found" in result


class TestGetPullRequest:
    """Tests for bitbucket_get_pull_request tool."""
    
    @responses.activate
    def test_get_pr_success(self, mock_env_vars, mock_pr_detail_response):
        """Test get_pr returns formatted PR details."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/42",
            json=mock_pr_detail_response,
            status=200
        )
        
        from src.server import bitbucket_get_pull_request
        
        result = bitbucket_get_pull_request(42)
        
        # Should be a string
        assert isinstance(result, str)
        # Should contain detailed PR info
        assert "PR #42" in result
        assert "Add authentication feature" in result
        assert "John Doe" in result
        assert "OPEN" in result
        assert "feature/auth" in result
        assert "main" in result
        assert "OAuth2 authentication support" in result
        assert "Jane Smith" in result  # Reviewer
    
    @responses.activate
    def test_get_pr_not_found(self, mock_env_vars):
        """Test get_pr returns error string for non-existent PR (404)."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/999",
            json={"error": "Not found"},
            status=404
        )
        
        from src.server import bitbucket_get_pull_request
        
        result = bitbucket_get_pull_request(999)
        
        # Should be an error string (not exception)
        assert isinstance(result, str)
        assert "Failed to fetch PR #999" in result or "Not found" in result
        assert "bitbucket_get_pull_request" in result or "Failed" in result


class TestToolReturnFormats:
    """Tests for tool return format requirements."""
    
    @responses.activate
    def test_tools_return_strings_not_json(self, mock_env_vars, mock_pr_list_response):
        """Test all tools return strings (never JSON objects)."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json=mock_pr_list_response,
            status=200
        )
        
        from src.server import bitbucket_list_pull_requests
        
        result = bitbucket_list_pull_requests()
        
        # Must be string type
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        # Must not be a JSON string that parses to dict
        import json
        try:
            parsed = json.loads(result)
            # If it parses, it should NOT be a dict at the top level
            assert not isinstance(parsed, dict), "Tool returned JSON object as string"
        except json.JSONDecodeError:
            pass  # Good - not valid JSON
    
    @responses.activate
    def test_error_messages_include_context(self, mock_env_vars):
        """Test error messages include tool name and context."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/999",
            json={"error": "Not found"},
            status=404
        )
        
        from src.server import bitbucket_get_pull_request
        
        result = bitbucket_get_pull_request(999)
        
        # Error should contain tool name or context
        assert "bitbucket_get_pull_request" in result or "Failed to fetch" in result
        # Should mention the PR ID
        assert "999" in result
