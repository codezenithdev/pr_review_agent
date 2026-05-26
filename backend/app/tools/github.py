"""
LangChain tools for GitHub API integration.

Three @tool decorated functions to fetch PR metadata, files/diffs, and commits
from GitHub for the PR review agent pipeline.
"""

import os
import re
import logging
from typing import Optional
import httpx
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _extract_pr_url_parts(pr_url: str) -> tuple[str, str, int]:
    """
    Parse GitHub PR URL to extract owner, repo, and PR number.

    Args:
        pr_url: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

    Returns:
        Tuple of (owner, repo, pr_number)

    Raises:
        ValueError: If URL is invalid GitHub PR URL format
    """
    # Pattern: https://github.com/owner/repo/pull/number
    pattern = r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, pr_url)

    if not match:
        raise ValueError(
            f"Invalid GitHub PR URL format. Expected: "
            f"https://github.com/owner/repo/pull/NUMBER, got: {pr_url}"
        )

    owner, repo, pr_number = match.groups()
    return owner, repo, int(pr_number)


def _get_github_headers() -> dict:
    """
    Get GitHub API headers with authentication.

    Returns:
        Dict with Authorization header

    Raises:
        ValueError: If GITHUB_TOKEN is not set
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN environment variable not set. "
            "Please set it in .env or environment."
        )

    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


@tool
def fetch_pr_metadata(pr_url: str) -> dict:
    """
    Fetch GitHub PR metadata: title, author, additions, deletions, changed_files count.

    Args:
        pr_url: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

    Returns:
        Dict with PR metadata fields (owner, repo, pr_number, title, author,
        additions, deletions, changed_files, base_branch, head_branch, state)

    Example:
        {
            "owner": "anthropics",
            "repo": "anthropic-sdk-python",
            "pr_number": 123,
            "title": "Add feature X",
            "author": "jane-doe",
            "additions": 150,
            "deletions": 45,
            "changed_files": 3,
            "base_branch": "main",
            "head_branch": "feature/x",
            "state": "open"
        }
    """
    try:
        owner, repo, pr_number = _extract_pr_url_parts(pr_url)
    except ValueError as e:
        return {"error": str(e)}

    try:
        headers = _get_github_headers()
    except ValueError as e:
        return {"error": str(e)}

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)

            if response.status_code == 404:
                return {"error": f"PR not found or private: {pr_url}"}
            elif response.status_code == 401:
                return {"error": "Invalid GitHub token (401 Unauthorized)"}
            elif response.status_code == 403:
                return {"error": "Access forbidden (403)"}
            elif response.status_code == 429:
                retry_after = response.headers.get("X-RateLimit-Reset", "unknown")
                return {"error": f"Rate limit exceeded. Retry after: {retry_after}"}
            elif response.status_code >= 400:
                return {"error": f"GitHub API error {response.status_code}"}

            data = response.json()

            return {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "title": data.get("title", ""),
                "author": data.get("user", {}).get("login", "unknown"),
                "additions": data.get("additions", 0),
                "deletions": data.get("deletions", 0),
                "changed_files": data.get("changed_files", 0),
                "base_branch": data.get("base", {}).get("ref", "main"),
                "head_branch": data.get("head", {}).get("ref", "unknown"),
                "state": data.get("state", "unknown"),
            }

    except httpx.TimeoutException:
        return {"error": "Request timeout while fetching PR metadata"}
    except httpx.RequestError as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error fetching PR metadata: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


@tool
def fetch_pr_files(pr_url: str) -> dict:
    """
    Fetch PR files with their unified diffs.

    Caps at 20 files and 4000 chars per diff to keep token usage manageable.

    Args:
        pr_url: Full GitHub PR URL

    Returns:
        Dict with file_count and files dict mapping file paths to unified diffs.
        Skips binary files (no patch available).

    Example:
        {
            "file_count": 2,
            "files": {
                "src/main.py": "@@ -1,5 +1,7 @@ ...",
                "tests/test_main.py": "@@ -10,3 +10,5 @@ ..."
            }
        }
    """
    try:
        owner, repo, pr_number = _extract_pr_url_parts(pr_url)
    except ValueError as e:
        return {"error": str(e), "file_count": 0, "files": {}}

    try:
        headers = _get_github_headers()
    except ValueError as e:
        return {"error": str(e), "file_count": 0, "files": {}}

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    try:
        files_dict = {}
        file_count = 0

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers, params={"per_page": 20})

            if response.status_code == 404:
                return {
                    "error": f"PR not found or private: {pr_url}",
                    "file_count": 0,
                    "files": {},
                }
            elif response.status_code == 401:
                return {
                    "error": "Invalid GitHub token (401 Unauthorized)",
                    "file_count": 0,
                    "files": {},
                }
            elif response.status_code >= 400:
                return {
                    "error": f"GitHub API error {response.status_code}",
                    "file_count": 0,
                    "files": {},
                }

            files_data = response.json()

            for file_obj in files_data:
                filename = file_obj.get("filename", "")
                patch = file_obj.get("patch", "")

                # Skip binary files and renames with no changes
                if not patch:
                    continue

                # Truncate large diffs to 4000 chars
                if len(patch) > 4000:
                    patch = patch[:4000] + "\n... [diff truncated]"

                files_dict[filename] = patch
                file_count += 1

        return {"file_count": file_count, "files": files_dict}

    except httpx.TimeoutException:
        return {
            "error": "Request timeout while fetching PR files",
            "file_count": 0,
            "files": {},
        }
    except httpx.RequestError as e:
        return {
            "error": f"Network error: {str(e)}",
            "file_count": 0,
            "files": {},
        }
    except Exception as e:
        logger.exception(f"Unexpected error fetching PR files: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "file_count": 0,
            "files": {},
        }


@tool
def fetch_pr_commits(pr_url: str) -> dict:
    """
    Fetch PR commit messages for understanding PR intent.

    Returns up to 10 commits.

    Args:
        pr_url: Full GitHub PR URL

    Returns:
        Dict with commit_count and commits list of dicts with message, author, date.

    Example:
        {
            "commit_count": 2,
            "commits": [
                {
                    "message": "Add feature X\n\nDetailed description",
                    "author": "jane-doe",
                    "date": "2025-05-25T10:30:00Z"
                }
            ]
        }
    """
    try:
        owner, repo, pr_number = _extract_pr_url_parts(pr_url)
    except ValueError as e:
        return {"error": str(e), "commit_count": 0, "commits": []}

    try:
        headers = _get_github_headers()
    except ValueError as e:
        return {"error": str(e), "commit_count": 0, "commits": []}

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits"

    try:
        commits_list = []

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers, params={"per_page": 10})

            if response.status_code == 404:
                return {
                    "error": f"PR not found or private: {pr_url}",
                    "commit_count": 0,
                    "commits": [],
                }
            elif response.status_code == 401:
                return {
                    "error": "Invalid GitHub token (401 Unauthorized)",
                    "commit_count": 0,
                    "commits": [],
                }
            elif response.status_code >= 400:
                return {
                    "error": f"GitHub API error {response.status_code}",
                    "commit_count": 0,
                    "commits": [],
                }

            commits_data = response.json()

            for commit_obj in commits_data:
                commit_info = commit_obj.get("commit", {})
                message = commit_info.get("message", "")
                author = commit_info.get("author", {}).get("name", "unknown")
                date = commit_info.get("author", {}).get("date", "unknown")

                commits_list.append(
                    {
                        "message": message,
                        "author": author,
                        "date": date,
                    }
                )

        return {
            "commit_count": len(commits_list),
            "commits": commits_list,
        }

    except httpx.TimeoutException:
        return {
            "error": "Request timeout while fetching PR commits",
            "commit_count": 0,
            "commits": [],
        }
    except httpx.RequestError as e:
        return {
            "error": f"Network error: {str(e)}",
            "commit_count": 0,
            "commits": [],
        }
    except Exception as e:
        logger.exception(f"Unexpected error fetching PR commits: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "commit_count": 0,
            "commits": [],
        }


__all__ = [
    "fetch_pr_metadata",
    "fetch_pr_files",
    "fetch_pr_commits",
]
