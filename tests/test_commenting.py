"""Tests for Bitbucket PR commenting operations.

Tests general comments and inline comments with mocked Bitbucket API responses.
"""

import pytest
import responses


@pytest.fixture
def mock_pr_response():
    """Sample PR response for testing."""
    return {
        "id": 123,
        "title": "Add new feature",
        "state": "OPEN",
        "author": {
            "display_name": "Test User"
        },
        "source": {
            "branch": {
                "name": "feature-branch"
            }
        },
        "destination": {
            "branch": {
                "name": "main"
            }
        },
        "created_on": "2024-01-15T10:30:00.000+00:00",
        "description": "This PR adds a new feature"
    }


@pytest.fixture
def mock_comment_response():
    """Sample comment response from Bitbucket API."""
    return {
        "id": 456,
        "content": {
            "raw": "This looks good!"
        },
        "user": {
            "display_name": "Test User"
        },
        "created_on": "2024-01-15T11:00:00.000+00:00"
    }


@pytest.fixture
def mock_diff_response():
    """Sample unified diff for inline comment testing.
    
    Shows:
    - File src/main.py
    - Hunk starting at old line 10, new line 10
    - Deleted line at old line 14 (shows as '-old code')
    - Added line at new line 14 (shows as '+new code')  
    - Context lines 10-13 and 15-16
    """
    return '''diff --git a/src/main.py b/src/main.py
index abc123..def456 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@ def process_data(data):
     result = []
     for item in data:
         if item > 0:
-            old code here
+            new code here
             result.append(item)
     return result
'''


class TestGeneralComment:
    """Tests for bitbucket_add_comment tool."""

    @responses.activate
    def test_add_comment_success(self, mock_env_vars, mock_comment_response):
        """Test add_comment returns success message on 201."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/comments",
            json=mock_comment_response,
            status=201
        )

        from src.server import bitbucket_add_comment

        result = bitbucket_add_comment(
            pr_id=123,
            content="This looks good!"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "Comment added to PR #123" in result

    @responses.activate
    def test_add_comment_empty(self, mock_env_vars):
        """Test add_comment returns error for empty content."""
        from src.server import bitbucket_add_comment

        result = bitbucket_add_comment(pr_id=123, content="")

        # Should be a string
        assert isinstance(result, str)
        # Should contain error indicator
        assert "Failed" in result or "empty" in result.lower()
        assert "bitbucket_add_comment" in result

    @responses.activate
    def test_add_comment_whitespace(self, mock_env_vars):
        """Test add_comment returns error for whitespace-only content."""
        from src.server import bitbucket_add_comment

        result = bitbucket_add_comment(pr_id=123, content="   \n\t  ")

        # Should be a string
        assert isinstance(result, str)
        # Should contain error indicator
        assert "Failed" in result or "empty" in result.lower()
        assert "bitbucket_add_comment" in result

    @responses.activate
    def test_add_comment_api_error(self, mock_env_vars):
        """Test add_comment returns formatted error on API 401."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/comments",
            json={"error": "Unauthorized"},
            status=401
        )

        from src.server import bitbucket_add_comment

        result = bitbucket_add_comment(
            pr_id=123,
            content="Test comment"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain error indicators
        assert "Failed" in result or "error" in result.lower()
        assert "401" in result or "Authentication" in result


class TestInlineComment:
    """Tests for bitbucket_add_inline_comment tool."""

    @responses.activate
    def test_inline_added_line(self, mock_env_vars, mock_diff_response, mock_comment_response):
        """Test inline comment on added line uses 'to' field."""
        # Mock GET for diff
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/diff",
            body=mock_diff_response,
            status=200,
            content_type="text/plain"
        )
        
        # Capture the POST request to verify 'to' field
        posted_data = {}
        def capture_post(request):
            import json
            posted_data['body'] = json.loads(request.body)
            return (201, {}, json.dumps(mock_comment_response))
        
        responses.add_callback(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/comments",
            callback=capture_post,
            content_type="application/json"
        )

        from src.server import bitbucket_add_inline_comment

        result = bitbucket_add_inline_comment(
            pr_id=123,
            file_path="src/main.py",
            line=14,
            content="Good addition!"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "Comment added to PR #123" in result
        # Verify 'to' field was used (added line)
        assert posted_data['body']['inline']['to'] == 14
        assert 'from' not in posted_data['body']['inline'] or posted_data['body']['inline']['from'] is None

    @responses.activate
    def test_inline_deleted_line(self, mock_env_vars, mock_diff_response, mock_comment_response):
        """Test inline comment on deleted line uses 'from' field."""
        # Mock GET for diff
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/diff",
            body=mock_diff_response,
            status=200,
            content_type="text/plain"
        )
        
        # Capture the POST request to verify 'from' field
        posted_data = {}
        def capture_post(request):
            import json
            posted_data['body'] = json.loads(request.body)
            return (201, {}, json.dumps(mock_comment_response))
        
        responses.add_callback(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/comments",
            callback=capture_post,
            content_type="application/json"
        )

        from src.server import bitbucket_add_inline_comment

        result = bitbucket_add_inline_comment(
            pr_id=123,
            file_path="src/main.py",
            line=14,
            content="Why was this removed?"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "Comment added to PR #123" in result
        # Verify 'from' field was used (deleted line - old file line number)
        assert posted_data['body']['inline']['from'] == 14
        assert 'to' not in posted_data['body']['inline'] or posted_data['body']['inline']['to'] is None

    @responses.activate
    def test_inline_context_line(self, mock_env_vars, mock_diff_response, mock_comment_response):
        """Test inline comment on context line uses 'to' field."""
        # Mock GET for diff
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/diff",
            body=mock_diff_response,
            status=200,
            content_type="text/plain"
        )
        
        # Capture the POST request
        posted_data = {}
        def capture_post(request):
            import json
            posted_data['body'] = json.loads(request.body)
            return (201, {}, json.dumps(mock_comment_response))
        
        responses.add_callback(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/comments",
            callback=capture_post,
            content_type="application/json"
        )

        from src.server import bitbucket_add_inline_comment

        result = bitbucket_add_inline_comment(
            pr_id=123,
            file_path="src/main.py",
            line=11,  # Context line: "    result = []"
            content="This could be a set for O(1) lookup"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "Comment added to PR #123" in result
        # Verify 'to' field was used (context line)
        assert posted_data['body']['inline']['to'] == 11

    @responses.activate
    def test_inline_file_not_found(self, mock_env_vars, mock_diff_response):
        """Test inline comment returns error when file not in diff."""
        # Mock GET for diff
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/diff",
            body=mock_diff_response,
            status=200,
            content_type="text/plain"
        )

        from src.server import bitbucket_add_inline_comment

        result = bitbucket_add_inline_comment(
            pr_id=123,
            file_path="src/nonexistent.py",  # File not in diff
            line=10,
            content="Comment"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain error indicator
        assert "Failed" in result or "error" in result.lower()
        # Should mention file not found
        assert "not found" in result.lower() or "File" in result
        assert "src/nonexistent.py" in result

    @responses.activate
    def test_inline_line_not_found(self, mock_env_vars, mock_diff_response):
        """Test inline comment returns error when line not in diff."""
        # Mock GET for diff
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/diff",
            body=mock_diff_response,
            status=200,
            content_type="text/plain"
        )

        from src.server import bitbucket_add_inline_comment

        result = bitbucket_add_inline_comment(
            pr_id=123,
            file_path="src/main.py",
            line=999,  # Line doesn't exist in diff
            content="Comment"
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain error indicator
        assert "Failed" in result or "error" in result.lower()
        # Should mention line not found
        assert "not found" in result.lower() or "Line" in result
        assert "line 999" in result.lower() or "999" in result

    @responses.activate
    def test_inline_empty_content(self, mock_env_vars, mock_diff_response):
        """Test inline comment returns error for empty content with context."""
        from src.server import bitbucket_add_inline_comment

        result = bitbucket_add_inline_comment(
            pr_id=123,
            file_path="src/main.py",
            line=10,
            content=""
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain error indicator with file and line context
        assert "Failed" in result or "empty" in result.lower()
        assert "src/main.py" in result
        assert "line 10" in result.lower() or "10" in result
