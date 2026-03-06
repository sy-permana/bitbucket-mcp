"""MCP Server entry point for Bitbucket PR Manager.

Initializes FastMCP server with validated configuration and authenticated client.
All logging output goes to stderr to avoid corrupting stdio protocol.
"""

# CRITICAL: Configure logging to stderr BEFORE any other imports
# This ensures all logs (including from imported modules) go to stderr
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Now import other modules (their logs will also go to stderr)
from mcp.server.fastmcp import FastMCP
from src.config import BitbucketConfig
from src.client import BitbucketClient

# Validate configuration on import (fail fast)
try:
    config = BitbucketConfig.from_env()
    logger.info(f"Configuration loaded for workspace: {config.bitbucket_workspace}")
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

# Initialize Bitbucket client
bitbucket_client = BitbucketClient(config)

# Initialize FastMCP server
mcp = FastMCP("bitbucket-pr-manager")

if __name__ == "__main__":
    logger.info("Starting Bitbucket PR Manager MCP server...")
    mcp.run(transport="stdio")
