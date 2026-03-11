"""Bitbucket API client with HTTPBasicAuth authentication.

Uses requests library with session reuse for efficient API calls.
"""

import requests
from requests.auth import HTTPBasicAuth

from src.config import BitbucketConfig


class BitbucketClient:
    """Client for Bitbucket Cloud REST API v2.

    Authenticates using HTTP Basic Auth with API token (RFC-2617).

    Attributes:
        config: BitbucketConfig instance with credentials
        auth: HTTPBasicAuth instance for requests
        session: requests.Session for connection pooling
        repo_url: Base URL for repository-specific endpoints
    """

    BASE_URL = "https://api.bitbucket.org/2.0"

    def __init__(self, config: BitbucketConfig):
        """Initialize client with configuration.

        Args:
            config: Validated BitbucketConfig with credentials
        """
        self.config = config

        # HTTPBasicAuth with email as username, token as password
        # CRITICAL: username=email, password=token (not reversed!)
        self.auth = HTTPBasicAuth(config.bitbucket_username, config.bitbucket_api_token)

        # Session for connection pooling and default headers
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

        # Repository-specific base URL
        self.repo_url = (
            f"{self.BASE_URL}/repositories/"
            f"{config.bitbucket_workspace}/{config.bitbucket_repo_slug}"
        )

    def get(self, endpoint: str, **kwargs) -> dict:
        """Make authenticated GET request to Bitbucket API.

        Args:
            endpoint: API endpoint path (e.g., "/pullrequests")
            **kwargs: Additional arguments for requests.get()

        Returns:
            dict: JSON response from API

        Raises:
            requests.exceptions.HTTPError: On 4xx/5xx responses
        """
        url = f"{self.repo_url}{endpoint}"
        response = self.session.get(url, timeout=self.config.request_timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict | None = None, **kwargs) -> dict:
        """Make authenticated POST request to Bitbucket API.

        Args:
            endpoint: API endpoint path
            data: JSON-serializable request body
            **kwargs: Additional arguments for requests.post()

        Returns:
            dict: JSON response from API

        Raises:
            requests.exceptions.HTTPError: On 4xx/5xx responses
        """
        url = f"{self.repo_url}{endpoint}"
        response = self.session.post(
            url, json=data, timeout=self.config.request_timeout, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def test_authentication(self) -> bool:
        """Test that authentication is working.

        Makes a lightweight API call to verify credentials.

        Returns:
            bool: True if authentication succeeds, False otherwise
        """
        try:
            # Lightweight call to verify auth
            self.session.get(
                f"{self.BASE_URL}/user", timeout=self.config.request_timeout
            ).raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
