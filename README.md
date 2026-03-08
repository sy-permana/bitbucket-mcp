# Bitbucket PR Manager MCP Server

A Model Context Protocol (MCP) server that wraps the Atlassian Bitbucket REST API v2, enabling AI agents to autonomously manage, review, and merge Pull Requests.

## Features

- **PR Operations**: List, get details, create, merge, approve, decline, request changes
- **Diff Viewing**: Fetch PR diffs with automatic truncation at 10,000 characters
- **Comments**: Add general PR comments and inline line-specific comments
- **CI/CD Status**: Check commit status for any commit hash
- **Error Handling**: All tools return clear string messages with context

## Requirements

- Python 3.10+
- Bitbucket API Token with read/write access to repositories

## Environment Variables

Set these environment variables before running:

| Variable | Description |
|----------|-------------|
| `BITBUCKET_USERNAME` | Your Bitbucket username |
| `BITBUCKET_API_TOKEN` | Your Bitbucket API token |
| `BITBUCKET_WORKSPACE` | Your Bitbucket workspace name |
| `BITBUCKET_REPO_SLUG` | Repository slug (e.g., "my-project") |

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Installation

```bash
# Clone the repository
git clone https://github.com/sy-permana/bitbucket-mcp.git
cd bitbucket-mcp

# Install dependencies
pip install -e ".[dev]"

# Or just runtime dependencies
pip install -e .
```

## Usage

### Running as MCP Server

```bash
# With environment variables set
python -m src.server

# Or use the mcp CLI
mcp run src.server:server
```

### Using with Claude Desktop

Add this to your Claude Desktop config:

```json
{
  "mcpServers": {
    "bitbucket-pr-manager": {
      "command": "python",
      "args": ["-m", "src.server"],
      "env": {
        "BITBUCKET_USERNAME": "your-username",
        "BITBUCKET_API_TOKEN": "your-token",
        "BITBUCKET_WORKSPACE": "your-workspace",
        "BITBUCKET_REPO_SLUG": "your-repo"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `bitbucket_list_prs` | List pull requests with optional state filter |
| `bitbucket_get_pr` | Get detailed information about a PR |
| `bitbucket_get_pr_diff` | Fetch PR diff (truncated at 10k chars) |
| `bitbucket_check_commit_status` | Check CI/CD status for a commit |
| `bitbucket_create_pr` | Create a new pull request |
| `bitbucket_merge_pr` | Merge an open pull request |
| `bitbucket_approve_pr` | Approve a pull request |
| `bitbucket_decline_pr` | Decline a pull request |
| `bitbucket_request_changes` | Request changes on a PR |
| `bitbucket_add_comment` | Add a general comment to a PR |
| `bitbucket_add_inline_comment` | Add an inline comment to a specific line |

## Development

```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Project Structure

```
bitbucket-mcp/
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration validation
│   ├── client/
│   │   ├── __init__.py
│   │   └── bitbucket_client.py  # API client
│   └── server.py           # MCP server
├── tests/
│   ├── conftest.py
│   ├── test_server.py
│   ├── test_commenting.py
│   └── ...
├── .planning/              # Project planning (GSD)
├── pyproject.toml
└── README.md
```

## License

MIT
