"""Tests for Bitbucket PR lifecycle operations.

Tests create, merge, approve, decline operations with mocked Bitbucket API responses.
"""

import pytest
import responses


class TestCreatePullRequest:
    """Tests for bitbucket_create_pr tool."""

    @responses.activate
    def test_create_pr_success(self, mock_env_vars):
        """Test create_pr returns formatted success message with PR details."""
        # Mock the POST response for creating a PR
        mock_response = {
            "id": 123,
            "title": "Add user authentication",
            "state": "OPEN",
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
            "links": {
                "html": {
                    "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
                }
            }
        }

        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json=mock_response,
            status=201
        )

        from src.server import bitbucket_create_pr

        result = bitbucket_create_pr(
            title="Add user authentication",
            source_branch="feature/auth",
            target_branch="main",
            description="This PR adds OAuth2 authentication support."
        )

        # Should be a string
        assert isinstance(result, str)
        # Should contain PR info per tiered format: ID, title, branches, URL
        assert "Created PR #123" in result
        assert "Add user authentication" in result
        assert "Source: feature/auth → Target: main" in result
        assert "https://bitbucket.org/test-workspace/test-repo/pull-requests/123" in result

    @responses.activate
    def test_create_pr_minimal_args(self, mock_env_vars):
        """Test create_pr with only required arguments."""
        mock_response = {
            "id": 124,
            "title": "Quick fix",
            "state": "OPEN",
            "source": {
                "branch": {
                    "name": "hotfix/urgent"
                }
            },
            "destination": {
                "branch": {
                    "name": "main"  # API returns default branch when not specified
                }
            },
            "links": {
                "html": {
                    "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/124"
                }
            }
        }

        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json=mock_response,
            status=201
        )

        from src.server import bitbucket_create_pr

        # Only required args: title and source_branch
        result = bitbucket_create_pr(
            title="Quick fix",
            source_branch="hotfix/urgent"
        )

        assert isinstance(result, str)
        assert "Created PR #124" in result
        assert "Quick fix" in result
        assert "hotfix/urgent" in result

    @responses.activate
    def test_create_pr_with_close_source_branch(self, mock_env_vars):
        """Test create_pr with close_source_branch=True."""
        mock_response = {
            "id": 125,
            "title": "Feature implementation",
            "state": "OPEN",
            "source": {
                "branch": {
                    "name": "feature/new-thing"
                }
            },
            "destination": {
                "branch": {
                    "name": "develop"
                }
            },
            "close_source_branch": True,
            "links": {
                "html": {
                    "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/125"
                }
            }
        }

        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json=mock_response,
            status=201
        )

        from src.server import bitbucket_create_pr

        result = bitbucket_create_pr(
            title="Feature implementation",
            source_branch="feature/new-thing",
            target_branch="develop",
            close_source_branch=True
        )

        assert isinstance(result, str)
        assert "Created PR #125" in result

    @responses.activate
    def test_create_pr_error_handling(self, mock_env_vars):
        """Test create_pr returns error message on API failure."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json={"error": "Source branch not found"},
            status=404
        )

        from src.server import bitbucket_create_pr

        result = bitbucket_create_pr(
            title="Test PR",
            source_branch="nonexistent-branch"
        )

        # Should return error string
        assert isinstance(result, str)
        # Should contain tool name or error indicator
        assert "bitbucket_create_pr" in result or "Failed" in result
        # Should mention creating PR
        assert "create PR" in result.lower() or "Failed" in result

    @responses.activate
    def test_create_pr_auth_error(self, mock_env_vars):
        """Test create_pr returns error message on authentication failure."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json={"error": "Unauthorized"},
            status=401
        )

        from src.server import bitbucket_create_pr

        result = bitbucket_create_pr(
            title="Test PR",
            source_branch="feature/test"
        )

        assert isinstance(result, str)
        assert "Failed" in result or "bitbucket_create_pr" in result
        assert "401" in result or "Authentication" in result or "Unauthorized" in result
