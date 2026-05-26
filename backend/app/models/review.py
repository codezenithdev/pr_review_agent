"""
Pydantic models for PR review request/response data contracts.

Defines the shape of data flowing through the review pipeline:
- ReviewRequest: Client input for submitting a PR for review
- ReviewComment: Individual code-level finding/comment
- ReviewSummary: Complete review output (score, verdict, findings)
- ReviewStatus: Enum for review job state tracking
- ReviewMetadata: GitHub PR metadata and diffs (agent working state)
- ReviewResponse: API wrapper with timestamps and status
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ReviewStatus(str, Enum):
    """Status of a review job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewRequest(BaseModel):
    """Client request to review a GitHub PR."""

    pr_url: str = Field(
        ...,
        description="Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)",
    )
    focus_areas: Optional[list[str]] = Field(
        default=None,
        description="Areas to emphasize in review (e.g., ['security', 'performance'])",
    )
    custom_prompt: Optional[str] = Field(
        default=None, description="Additional instructions for the review"
    )

    @field_validator("pr_url")
    @classmethod
    def validate_pr_url(cls, v: str) -> str:
        """Validate that the URL is a valid GitHub PR URL."""
        # Basic GitHub PR URL pattern: https://github.com/owner/repo/pull/number
        if not (
            "github.com" in v
            and "/pull/" in v
            and v.startswith(("http://", "https://"))
        ):
            raise ValueError(
                f"Invalid GitHub PR URL. Expected format: "
                f"https://github.com/owner/repo/pull/123, got: {v}"
            )
        return v


class ReviewComment(BaseModel):
    """Individual code-level comment/finding in a review."""

    file: str = Field(..., description="File path (e.g., src/app.py)")
    line: Optional[int] = Field(
        default=None, description="Line number (None if applies to whole file)"
    )
    severity: str = Field(
        ..., description="Severity level: 'critical', 'warning', or 'info'"
    )
    category: str = Field(
        ...,
        description="Category (e.g., 'security', 'logic', 'style', 'performance', 'test')",
    )
    title: str = Field(..., description="Short summary (< 80 chars)")
    body: str = Field(..., description="Full explanation of the finding (required)")
    suggestion: Optional[str] = Field(
        default=None, description="Proposed code change or fix (markdown)"
    )

    @field_validator("body")
    @classmethod
    def validate_body_not_empty(cls, v: str) -> str:
        """Ensure body has meaningful content."""
        if not v or len(v.strip()) < 1:
            raise ValueError("body must be a non-empty string")
        return v


class ReviewSummary(BaseModel):
    """Complete review output with findings, score, and verdict."""

    pr_title: str = Field(..., description="Original PR title from GitHub")
    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Score 0–100 (populated by agent's scoring logic)",
    )
    verdict: str = Field(
        ...,
        description="One of: 'approve', 'approve_with_suggestions', 'request_changes', 'comment'",
    )
    pr_url: str = Field(..., description="Echo back the original PR URL")
    comments: list[ReviewComment] = Field(
        default_factory=list, description="Code-level findings (may be empty)"
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="2–3 highlights of good design/implementation",
    )
    critical_issues: list[str] = Field(
        default_factory=list, description="2–3 blocking concerns (if any)"
    )
    summary: str = Field(..., description="2–3 sentence summary of the review")


class ReviewMetadata(BaseModel):
    """GitHub PR metadata and diffs for agent working state."""

    owner: str = Field(..., description="GitHub org/user")
    repo: str = Field(..., description="Repository name")
    pr_number: int = Field(..., description="PR number")
    title: str = Field(..., description="PR title")
    author: str = Field(..., description="PR author username")
    additions: int = Field(..., description="Number of added lines")
    deletions: int = Field(..., description="Number of deleted lines")
    changed_files: int = Field(..., description="Number of files changed")
    base_branch: str = Field(..., description="Target branch (e.g., main)")
    head_branch: str = Field(..., description="Feature branch")
    file_diffs: dict[str, str] = Field(
        default_factory=dict,
        description="Raw mapping of {file_path: unified_diff}",
    )
    file_diffs_parsed: Optional[dict[str, list[dict]]] = Field(
        default=None,
        description="Structured diff format with hunk details (populated by agent)",
    )


class ReviewResponse(BaseModel):
    """API response wrapper with status and timestamps."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique review run ID (UUID4)",
    )
    status: ReviewStatus = Field(..., description="Current review status")
    result: Optional[ReviewSummary] = Field(
        default=None, description="Review result (null until completed)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when review was submitted",
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when review finished"
    )


__all__ = [
    "ReviewStatus",
    "ReviewRequest",
    "ReviewComment",
    "ReviewSummary",
    "ReviewMetadata",
    "ReviewResponse",
]
