"""Configuration module for Bitbucket PR Manager MCP Server."""

import os
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from typing_extensions import Self


class BitbucketConfig(BaseModel):
    """Configuration loaded from environment variables."""
    
    bitbucket_username: str = Field(description="Atlassian account email")
    bitbucket_api_token: str = Field(description="Bitbucket API token")
    bitbucket_workspace: str = Field(description="Bitbucket workspace name")
    bitbucket_repo_slug: str = Field(description="Repository slug")
    
    @classmethod
    def from_env(cls) -> Self:
        """Load configuration from environment variables.
        
        Raises:
            ValueError: If any required environment variables are missing.
        """
        required_vars = [
            "BITBUCKET_USERNAME",
            "BITBUCKET_API_TOKEN",
            "BITBUCKET_WORKSPACE",
            "BITBUCKET_REPO_SLUG"
        ]
        
        missing = [var for var in required_vars if not os.environ.get(var)]
        
        if missing:
            raise ValueError(
                f"Configuration error: Missing required environment variables: "
                f"{', '.join(missing)}\n\n"
                f"Please set the following:\n"
                f"  - BITBUCKET_USERNAME (your Atlassian email)\n"
                f"  - BITBUCKET_API_TOKEN (from bitbucket.org settings)\n"
                f"  - BITBUCKET_WORKSPACE (your workspace name)\n"
                f"  - BITBUCKET_REPO_SLUG (repository slug)"
            )
        
        return cls(
            bitbucket_username=os.environ["BITBUCKET_USERNAME"],
            bitbucket_api_token=os.environ["BITBUCKET_API_TOKEN"],
            bitbucket_workspace=os.environ["BITBUCKET_WORKSPACE"],
            bitbucket_repo_slug=os.environ["BITBUCKET_REPO_SLUG"]
        )
