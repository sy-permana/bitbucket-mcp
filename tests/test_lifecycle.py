"""Tests for Bitbucket PR lifecycle operations.

Tests create, merge, approve, decline, and request-changes operations
with mocked Bitbucket API responses.
"""

import pytest
import responses


@pytest.fixture
def mock_pr_response():
    """Sample PR response for create and get operations."""
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
        "description": "This PR adds a new feature",
        "links": {
            "html": {
                "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
            }
        }
    }


@pytest.fixture
def mock_participant_response():
    """Sample participant response for approve/request-changes operations."""
    return {
        "user": {
            "display_name": "Test User",
            "account_id": "123456:abcdef"
        },
        "role": "PARTICIPANT",
        "approved": True,
        "participated_on": "2024-01-15T11:00:00.000+00:00"
    }


@pytest.fixture
def mock_merged_pr_response():
    """Sample PR response with MERGED state."""
    return {
        "id": 123,
        "title": "Add new feature",
        "state": "MERGED",
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
        "updated_on": "2024-01-15T12:00:00.000+00:00",
        "links": {
            "html": {
                "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
            }
        }
    }


@pytest.fixture
def mock_declined_pr_response():
    """Sample PR response with DECLINED state."""
    return {
        "id": 123,
        "title": "Add new feature",
        "state": "DECLINED",
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
        "updated_on": "2024-01-15T11:30:00.000+00:00",
        "links": {
            "html": {
                "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
            }
        }
    }


@pytest.fixture
def mock_open_pr_with_participants():
    """Sample OPEN PR response with participants list."""
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
        "participants": [
            {
                "user": {
                    "display_name": "Test User",
                    "account_id": "123456:abcdef"
                },
                "role": "PARTICIPANT",
                "approved": True
            },
            {
                "user": {
                    "display_name": "Reviewer",
                    "account_id": "789012:ghijkl"
                },
                "role": "REVIEWER",
                "approved": False
            }
        ],
        "links": {
            "html": {
                "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
            }
        }
    }


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


class TestMergePullRequest:
    """Tests for bitbucket_merge_pr tool."""

    @responses.activate
    def test_merge_pr_success(self, mock_env_vars, mock_pr_response, mock_merged_pr_response):
        """Test merge_pr returns confirmation with branch info."""
        # First GET to check PR state
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        # Then POST to merge
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/merge",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(123, strategy="merge_commit")

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "merged" in result.lower()
        # Should contain PR ID
        assert "123" in result
        # Should show branch info
        assert "feature-branch" in result or "main" in result

    @responses.activate
    def test_merge_pr_with_fast_forward_strategy(self, mock_env_vars, mock_pr_response, mock_merged_pr_response):
        """Test merge_pr with fast_forward strategy."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/merge",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(123, strategy="fast_forward")

        assert isinstance(result, str)
        assert "merged" in result.lower()

    @responses.activate
    def test_merge_pr_with_squash_strategy(self, mock_env_vars, mock_pr_response, mock_merged_pr_response):
        """Test merge_pr with squash strategy."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/merge",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(123, strategy="squash")

        assert isinstance(result, str)
        assert "merged" in result.lower()

    @responses.activate
    def test_merge_pr_already_merged(self, mock_env_vars, mock_merged_pr_response):
        """Test merge_pr fails with validation error for already merged PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(123)

        # Should return error
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
        # Should mention state
        assert "merged" in result.lower() or "state" in result.lower()
        assert "123" in result

    @responses.activate
    def test_merge_pr_already_declined(self, mock_env_vars, mock_declined_pr_response):
        """Test merge_pr fails with validation error for declined PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_declined_pr_response,
            status=200
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(123)

        # Should return error
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
        # Should mention state
        assert "declined" in result.lower() or "state" in result.lower()

    @responses.activate
    def test_merge_pr_with_close_source_branch(self, mock_env_vars, mock_pr_response, mock_merged_pr_response):
        """Test merge_pr accepts close_source_branch parameter."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/merge",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(123, close_source_branch=True)

        assert isinstance(result, str)
        assert "merged" in result.lower()


class TestApprovePullRequest:
    """Tests for bitbucket_approve_pr tool."""

    @responses.activate
    def test_approve_pr_success(self, mock_env_vars, mock_pr_response, mock_participant_response):
        """Test approve_pr returns confirmation."""
        # First GET to check PR state
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        # Then POST to approve
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/approve",
            json=mock_participant_response,
            status=200
        )

        from src.server import bitbucket_approve_pr

        result = bitbucket_approve_pr(123)

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "approved" in result.lower()
        # Should contain PR ID
        assert "123" in result

    @responses.activate
    def test_approve_pr_already_merged(self, mock_env_vars, mock_merged_pr_response):
        """Test approve_pr fails for already merged PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_approve_pr

        result = bitbucket_approve_pr(123)

        # Should return error
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
        # Should mention state
        assert "merged" in result.lower() or "state" in result.lower()

    @responses.activate
    def test_approve_pr_duplicate(self, mock_env_vars, mock_open_pr_with_participants):
        """Test approve_pr handles duplicate approval."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_open_pr_with_participants,
            status=200
        )

        from src.server import bitbucket_approve_pr

        result = bitbucket_approve_pr(123)

        # Should indicate already approved
        assert isinstance(result, str)
        assert "already" in result.lower() or "approved" in result.lower()


class TestDeclinePullRequest:
    """Tests for bitbucket_decline_pr tool."""

    @responses.activate
    def test_decline_pr_success(self, mock_env_vars, mock_pr_response, mock_declined_pr_response):
        """Test decline_pr returns confirmation."""
        # First GET to check PR state
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        # Then POST to decline
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/decline",
            json=mock_declined_pr_response,
            status=200
        )

        from src.server import bitbucket_decline_pr

        result = bitbucket_decline_pr(123)

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "declined" in result.lower()
        # Should contain PR ID
        assert "123" in result

    @responses.activate
    def test_decline_pr_already_merged(self, mock_env_vars, mock_merged_pr_response):
        """Test decline_pr fails for already merged PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_decline_pr

        result = bitbucket_decline_pr(123)

        # Should return error
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
        # Should mention state
        assert "merged" in result.lower() or "state" in result.lower()

    @responses.activate
    def test_decline_pr_already_declined(self, mock_env_vars, mock_declined_pr_response):
        """Test decline_pr handles already declined PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_declined_pr_response,
            status=200
        )

        from src.server import bitbucket_decline_pr

        result = bitbucket_decline_pr(123)

        # Should indicate already declined
        assert isinstance(result, str)
        assert "already" in result.lower() or "declined" in result.lower()


class TestRequestChanges:
    """Tests for bitbucket_request_changes tool."""

    @responses.activate
    def test_request_changes_success(self, mock_env_vars, mock_pr_response, mock_participant_response):
        """Test request_changes returns confirmation."""
        # First GET to check PR state
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        # Then POST to request changes
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/request-changes",
            json=mock_participant_response,
            status=200
        )

        from src.server import bitbucket_request_changes

        result = bitbucket_request_changes(123)

        # Should be a string
        assert isinstance(result, str)
        # Should contain success indicator
        assert "changes" in result.lower() or "requested" in result.lower()
        # Should contain PR ID
        assert "123" in result

    @responses.activate
    def test_request_changes_with_comment(self, mock_env_vars, mock_pr_response, mock_participant_response):
        """Test request_changes with optional comment."""
        # GET for state check
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        # POST to request changes
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/request-changes",
            json=mock_participant_response,
            status=200
        )
        # POST to add comment
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/comments",
            json={"id": 456, "content": {"raw": "Please fix the indentation"}},
            status=201
        )

        from src.server import bitbucket_request_changes

        result = bitbucket_request_changes(123, comment="Please fix the indentation")

        # Should succeed
        assert isinstance(result, str)
        assert "changes" in result.lower() or "requested" in result.lower()

    @responses.activate
    def test_request_changes_already_merged(self, mock_env_vars, mock_merged_pr_response):
        """Test request_changes fails for already merged PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_merged_pr_response,
            status=200
        )

        from src.server import bitbucket_request_changes

        result = bitbucket_request_changes(123)

        # Should return error
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
        # Should mention state
        assert "merged" in result.lower() or "state" in result.lower()

    @responses.activate
    def test_request_changes_already_declined(self, mock_env_vars, mock_declined_pr_response):
        """Test request_changes fails for already declined PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_declined_pr_response,
            status=200
        )

        from src.server import bitbucket_request_changes

        result = bitbucket_request_changes(123)

        # Should return error
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
        # Should mention state
        assert "declined" in result.lower() or "state" in result.lower()


class TestLifecycleErrorHandling:
    """Tests for error handling across all lifecycle operations."""

    @responses.activate
    def test_create_pr_http_error(self, mock_env_vars):
        """Test create_pr handles HTTP errors."""
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
            json={"error": "Unauthorized"},
            status=401
        )

        from src.server import bitbucket_create_pr

        result = bitbucket_create_pr(
            title="Test PR",
            source_branch="feature"
        )

        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()
        assert "401" in result or "unauthorized" in result.lower()

    @responses.activate
    def test_merge_pr_not_found(self, mock_env_vars):
        """Test merge_pr handles 404 for non-existent PR."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/999",
            json={"error": "Not found"},
            status=404
        )

        from src.server import bitbucket_merge_pr

        result = bitbucket_merge_pr(999)

        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()
        assert "999" in result

    @responses.activate
    def test_approve_pr_conflict(self, mock_env_vars, mock_pr_response):
        """Test approve_pr handles 409 conflict."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/approve",
            json={"error": "Conflict"},
            status=409
        )

        from src.server import bitbucket_approve_pr

        result = bitbucket_approve_pr(123)

        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()

    @responses.activate
    def test_decline_pr_rate_limited(self, mock_env_vars, mock_pr_response):
        """Test decline_pr handles 429 rate limit."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/decline",
            json={"error": "Rate limit exceeded"},
            status=429
        )

        from src.server import bitbucket_decline_pr

        result = bitbucket_decline_pr(123)

        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()
        assert "429" in result or "rate" in result.lower()

    @responses.activate
    def test_request_changes_server_error(self, mock_env_vars, mock_pr_response):
        """Test request_changes handles 500 server error."""
        responses.add(
            responses.GET,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123",
            json=mock_pr_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/123/request-changes",
            json={"error": "Internal server error"},
            status=500
        )

        from src.server import bitbucket_request_changes

        result = bitbucket_request_changes(123)

        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()
        assert "500" in result or "server" in result.lower()
