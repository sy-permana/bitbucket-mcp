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


class TestTruncateDiff:
    """Tests for the _truncate_diff helper function."""
    
    def test_truncate_diff_imports(self, mock_env_vars):
        """Verify _truncate_diff can be imported from server module."""
        from src.server import _truncate_diff
        assert callable(_truncate_diff)
    
    def test_truncate_diff_returns_full_when_under_limit(self, mock_env_vars):
        """Should return full diff when under character limit."""
        from src.server import _truncate_diff
        
        diff = 'diff --git a/file1.py b/file1.py\n--- a/file1.py\n+++ b/file1.py\n@@ -1 +1 @@\n-old\n+new'
        result = _truncate_diff(diff, 10000)
        assert result == diff
    
    def test_truncate_diff_handles_empty_diff(self, mock_env_vars):
        """Should handle empty diff gracefully."""
        from src.server import _truncate_diff
        
        result = _truncate_diff('', 10000)
        assert result == ''
    
    def test_truncate_diff_handles_none(self, mock_env_vars):
        """Should handle None diff gracefully."""
        from src.server import _truncate_diff
        
        result = _truncate_diff(None, 10000)
        assert result is None or result == ''
    
    def test_truncate_diff_breadth_first_strategy(self, mock_env_vars):
        """Should use breadth-first: include complete files, truncate at file boundary."""
        from src.server import _truncate_diff
        
        # Create a multi-file diff
        file1 = 'diff --git a/file1.py b/file1.py\n--- a/file1.py\n+++ b/file1.py\n@@ -1 +1 @@\n-old1\n+new1'
        file2 = '\ndiff --git a/file2.py b/file2.py\n--- a/file2.py\n+++ b/file2.py\n@@ -1 +1 @@\n-old2\n+new2'
        file3 = '\ndiff --git a/file3.py b/file3.py\n--- a/file3.py\n+++ b/file3.py\n@@ -1 +1 @@\n-old3\n+new3'
        
        diff = file1 + file2 + file3
        
        # Use a limit that includes file1 (with buffer for truncation message) but not file2
        # file1 is ~86 chars, need +100 buffer for truncation message = ~186
        # file1+file2 is ~86+90 = ~176 chars without separators
        limit = 200  # Enough for file1 + truncation message, but not file1+file2
        result = _truncate_diff(diff, limit)
        
        # Should include file1
        assert 'file1.py' in result
        
        # Should show truncation indicator
        assert '[... truncated ...]' in result
        assert 'Additional files' in result
        
        # file2 should NOT be included (truncated before it)
        assert 'file2.py' not in result
    
    def test_truncate_diff_adds_truncation_message(self, mock_env_vars):
        """Should add truncation indicator when truncating."""
        from src.server import _truncate_diff
        
        file1 = 'diff --git a/file1.py b/file1.py\n' + 'x' * 100
        file2 = '\ndiff --git a/file2.py b/file2.py\n' + 'y' * 100
        
        diff = file1 + file2
        limit = 150  # Only enough for part of file1
        
        result = _truncate_diff(diff, limit)
        
        # Should have truncation indicator
        assert '[... truncated ...]' in result


class TestGetPRDiff:
    """Tests for the bitbucket_get_pr_diff tool."""
    
    @responses.activate
    def test_get_pr_diff_success(self, mock_env_vars):
        """Should fetch and format diff with metadata header."""
        from src.server import bitbucket_get_pr_diff
        
        # Mock PR details response
        mock_pr = {
            'id': 123,
            'title': 'Test PR',
            'author': {'display_name': 'Test User'},
            'state': 'OPEN',
            'source': {'branch': {'name': 'feature-branch'}},
            'destination': {'branch': {'name': 'main'}}
        }
        
        # Mock diff response as text/plain
        mock_diff_text = 'diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new'
        
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/diff",
            body=mock_diff_text,
            status=200,
            content_type='text/plain'
        )
        
        result = bitbucket_get_pr_diff(123)
        
        # Verify result contains metadata
        assert 'PR #123' in result or 'Test PR' in result
        assert 'diff --git' in result
    
    @responses.activate
    def test_diff_truncation(self, mock_env_vars):
        """Should truncate diff when exceeding 10,000 characters."""
        from src.server import bitbucket_get_pr_diff
        
        # Mock PR details
        mock_pr = {
            'id': 456,
            'title': 'Large PR',
            'author': {'display_name': 'Developer'},
            'state': 'OPEN',
            'source': {'branch': {'name': 'develop'}},
            'destination': {'branch': {'name': 'main'}}
        }
        
        # Mock large diff response (>10k chars)
        large_diff = 'diff --git a/large.py b/large.py\n' + '\n'.join([f'+line {i}' for i in range(500)])
        
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/456",
            json=mock_pr,
            status=200
        )
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/456/diff",
            body=large_diff,
            status=200,
            content_type='text/plain'
        )
        
        result = bitbucket_get_pr_diff(456)
        
        # Verify truncation occurred
        assert len(result) <= 11000  # Allow some overhead for metadata + truncation message
        assert '[... truncated ...]' in result or 'truncated' in result.lower()
    
    @responses.activate
    def test_get_pr_diff_not_found(self, mock_env_vars):
        """Should return error message when PR not found."""
        from src.server import bitbucket_get_pr_diff
        
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/999",
            json={"error": "Not found"},
            status=404
        )
        
        result = bitbucket_get_pr_diff(999)
        
        # Verify error message format
        assert '[bitbucket_get_pr_diff]' in result
        assert '999' in result
        assert 'not found' in result.lower() or '404' in result
    
    @responses.activate
    def test_get_pr_diff_http_error(self, mock_env_vars):
        """Should return error message on HTTP error."""
        from src.server import bitbucket_get_pr_diff
        
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json={"error": "Server error"},
            status=500
        )
        
        result = bitbucket_get_pr_diff(123)
        
        # Verify error message format
        assert '[bitbucket_get_pr_diff]' in result
        assert '123' in result
        assert '500' in result
    
    def test_get_pr_diff_generic_error(self, mock_env_vars):
        """Should return error message on generic exception."""
        from src.server import bitbucket_get_pr_diff
        from unittest.mock import patch
        
        # Mock generic error during API call
        with patch('src.server.bitbucket_client') as mock_client:
            mock_client.get.side_effect = Exception("Connection timeout")
            
            result = bitbucket_get_pr_diff(123)
        
        # Verify error message format
        assert '[bitbucket_get_pr_diff]' in result
        assert '123' in result
        assert 'Connection timeout' in result
