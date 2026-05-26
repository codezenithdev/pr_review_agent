"""
LangGraph agent for PR review orchestration.

Orchestrates the complete review workflow:
1. Fetch PR metadata, files, and commits from GitHub
2. Invoke Claude API for intelligent code review analysis
3. Parse response into structured ReviewSummary
4. Handle progress callbacks for real-time streaming
"""

import json
import logging
from typing import TypedDict, Optional, Callable, Awaitable
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from app.models.review import (
    ReviewRequest,
    ReviewSummary,
    ReviewComment,
    ReviewMetadata,
)
from app.tools.github import (
    fetch_pr_metadata,
    fetch_pr_files,
    fetch_pr_commits,
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State passed through the LangGraph agent nodes."""

    request: ReviewRequest
    metadata: Optional[ReviewMetadata]
    pr_metadata_result: Optional[dict]
    pr_files_result: Optional[dict]
    pr_commits_result: Optional[dict]
    claude_response: Optional[str]
    review_summary: Optional[ReviewSummary]
    error: Optional[str]
    progress_callback: Optional[Callable[[str], Awaitable[None]]]


# System prompt for Claude - defines review dimensions and output format
REVIEW_SYSTEM_PROMPT = """You are an expert code reviewer. Analyze the provided GitHub PR and provide a comprehensive review.

Your review should evaluate:
1. **Security**: Identify security vulnerabilities, unsafe patterns, missing validation, authentication issues
2. **Performance**: Check for performance bottlenecks, inefficient algorithms, memory leaks, unnecessary operations
3. **Maintainability**: Assess code clarity, documentation, naming conventions, code organization
4. **Testability**: Evaluate test coverage, test quality, edge case handling
5. **Best Practices**: Check adherence to language conventions, design patterns, standards

Provide your response as a valid JSON object with this exact structure:
{
    "overall_score": <integer 0-100>,
    "verdict": "<one of: approve, approve_with_suggestions, request_changes, comment>",
    "comments": [
        {
            "file": "<file path>",
            "line": <line number or null if applies to whole file>,
            "severity": "<critical, warning, or info>",
            "category": "<security, performance, logic, style, test, maintainability, etc>",
            "title": "<short summary>",
            "body": "<detailed explanation>",
            "suggestion": "<optional code suggestion in markdown>"
        }
    ],
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3 if applicable>"],
    "critical_issues": ["<critical issue 1>", "<critical issue 2 if applicable>"],
    "summary": "<2-3 sentence executive summary>"
}

Important:
- Be thorough but concise
- Focus on actionable feedback
- Highlight genuine concerns, not nitpicks
- Acknowledge good design and implementation
- Return valid JSON only (no markdown, no extra text)"""


async def node_fetch_pr_metadata(state: AgentState) -> AgentState:
    """Fetch PR metadata from GitHub."""
    try:
        if state.get("progress_callback"):
            await state["progress_callback"]("Fetching PR metadata...")

        logger.info(f"Fetching PR metadata: {state['request'].pr_url}")
        result = fetch_pr_metadata.invoke({"pr_url": state["request"].pr_url})

        if "error" in result:
            state["error"] = f"Failed to fetch PR metadata: {result['error']}"
            logger.error(state["error"])
            return state

        state["pr_metadata_result"] = result
        logger.info(f"PR metadata fetched: {result.get('title')}")
        return state

    except Exception as e:
        state["error"] = f"Error fetching PR metadata: {str(e)}"
        logger.exception(state["error"])
        return state


async def node_fetch_pr_files(state: AgentState) -> AgentState:
    """Fetch PR files and diffs from GitHub."""
    try:
        if state.get("progress_callback"):
            await state["progress_callback"]("Fetching changed files...")

        logger.info(f"Fetching PR files: {state['request'].pr_url}")
        result = fetch_pr_files.invoke({"pr_url": state["request"].pr_url})

        if "error" in result:
            logger.warning(f"Warning fetching PR files: {result['error']}")
            # Don't fail, continue with partial data
            result = {"file_count": 0, "files": {}}

        state["pr_files_result"] = result
        logger.info(f"PR files fetched: {result['file_count']} files")
        return state

    except Exception as e:
        logger.exception(f"Error fetching PR files: {e}")
        # Don't fail, continue with empty files
        state["pr_files_result"] = {"file_count": 0, "files": {}}
        return state


async def node_fetch_pr_commits(state: AgentState) -> AgentState:
    """Fetch PR commits from GitHub."""
    try:
        if state.get("progress_callback"):
            await state["progress_callback"]("Fetching commit messages...")

        logger.info(f"Fetching PR commits: {state['request'].pr_url}")
        result = fetch_pr_commits.invoke({"pr_url": state["request"].pr_url})

        if "error" in result:
            logger.warning(f"Warning fetching PR commits: {result['error']}")
            # Don't fail, continue with partial data
            result = {"commit_count": 0, "commits": []}

        state["pr_commits_result"] = result
        logger.info(f"PR commits fetched: {result['commit_count']} commits")
        return state

    except Exception as e:
        logger.exception(f"Error fetching PR commits: {e}")
        # Don't fail, continue with empty commits
        state["pr_commits_result"] = {"commit_count": 0, "commits": []}
        return state


async def node_analyze_with_claude(state: AgentState) -> AgentState:
    """Invoke Claude API to analyze the PR."""
    try:
        if state.get("progress_callback"):
            await state["progress_callback"]("Analyzing with Claude...")

        # Check for errors from previous nodes
        if state.get("error"):
            logger.error(f"Skipping Claude analysis due to error: {state['error']}")
            return state

        # Build metadata from gathered GitHub data
        metadata_dict = state["pr_metadata_result"].copy()
        metadata_dict["file_diffs"] = state["pr_files_result"].get("files", {})
        metadata = ReviewMetadata(**metadata_dict)
        state["metadata"] = metadata

        # Build the prompt for Claude with all gathered information
        user_prompt = _build_analysis_prompt(
            metadata, state["pr_commits_result"], state["request"]
        )

        logger.info(f"Invoking Claude for PR analysis")

        # Initialize Claude via LangChain
        llm = ChatOpenAI(model="claude-3-5-sonnet-20241022", temperature=0.7)

        # Call Claude API
        message = await llm.ainvoke(
            [
                SystemMessage(content=REVIEW_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )

        response_text = message.content
        logger.info(f"Claude response received: {len(response_text)} chars")

        state["claude_response"] = response_text
        return state

    except Exception as e:
        state["error"] = f"Error invoking Claude: {str(e)}"
        logger.exception(state["error"])
        return state


async def node_parse_response(state: AgentState) -> AgentState:
    """Parse Claude's JSON response into ReviewSummary."""
    try:
        if state.get("error"):
            logger.error(f"Skipping parsing due to error: {state['error']}")
            return state

        if not state.get("claude_response"):
            state["error"] = "No Claude response to parse"
            logger.error(state["error"])
            return state

        logger.info("Parsing Claude response into ReviewSummary")

        # Extract JSON from Claude response
        response_text = state["claude_response"]

        # Try to extract JSON from the response
        try:
            # First, try direct JSON parsing (Claude should return pure JSON)
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                parsed = json.loads(json_str)
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                parsed = json.loads(json_str)
            else:
                raise ValueError(f"Could not extract JSON from response: {response_text[:200]}")

        # Build ReviewSummary from parsed response
        metadata = state["metadata"]
        review_summary = ReviewSummary(
            pr_title=metadata.title,
            overall_score=parsed.get("overall_score", 0),
            verdict=parsed.get("verdict", "comment"),
            pr_url=state["request"].pr_url,
            comments=[
                ReviewComment(**comment) for comment in parsed.get("comments", [])
            ],
            strengths=parsed.get("strengths", []),
            critical_issues=parsed.get("critical_issues", []),
            summary=parsed.get("summary", ""),
        )

        state["review_summary"] = review_summary
        logger.info(
            f"Review parsed successfully: score={review_summary.overall_score}, "
            f"verdict={review_summary.verdict}, comments={len(review_summary.comments)}"
        )
        return state

    except Exception as e:
        state["error"] = f"Error parsing Claude response: {str(e)}"
        logger.exception(state["error"])
        return state


def _build_analysis_prompt(
    metadata: ReviewMetadata, commits_result: dict, request: ReviewRequest
) -> str:
    """Build the user prompt for Claude with PR details."""
    prompt_parts = [
        f"# PR Review Request",
        f"\n## PR Information",
        f"- **Title**: {metadata.title}",
        f"- **Author**: {metadata.author}",
        f"- **Repository**: {metadata.owner}/{metadata.repo}",
        f"- **Base Branch**: {metadata.base_branch} ← {metadata.head_branch}",
        f"- **Changes**: +{metadata.additions} -{metadata.deletions} lines across {metadata.changed_files} files",
    ]

    if request.focus_areas:
        prompt_parts.append(f"\n## Review Focus Areas")
        prompt_parts.append(", ".join(request.focus_areas))

    if request.custom_prompt:
        prompt_parts.append(f"\n## Additional Instructions")
        prompt_parts.append(request.custom_prompt)

    if commits_result.get("commits"):
        prompt_parts.append(f"\n## Commit Messages")
        for commit in commits_result["commits"][:5]:  # Show first 5 commits
            msg = commit.get("message", "").split("\n")[0]  # First line only
            prompt_parts.append(f"- {msg}")

    prompt_parts.append(f"\n## Code Changes")
    if metadata.file_diffs:
        for file_path, diff in list(metadata.file_diffs.items())[:10]:  # First 10 files
            prompt_parts.append(f"\n### File: {file_path}")
            prompt_parts.append("```diff")
            prompt_parts.append(diff[:2000])  # First 2000 chars of diff
            if len(diff) > 2000:
                prompt_parts.append("... [diff truncated]")
            prompt_parts.append("```")
    else:
        prompt_parts.append("(No file diffs available)")

    prompt_parts.append(
        "\nPlease provide a comprehensive code review in JSON format as specified."
    )

    return "\n".join(prompt_parts)


# Build the LangGraph state machine
def _build_review_graph():
    """Create and return the LangGraph state graph for PR review."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("fetch_metadata", node_fetch_pr_metadata)
    graph.add_node("fetch_files", node_fetch_pr_files)
    graph.add_node("fetch_commits", node_fetch_pr_commits)
    graph.add_node("analyze_claude", node_analyze_with_claude)
    graph.add_node("parse_response", node_parse_response)

    # Define edges (workflow)
    graph.set_entry_point("fetch_metadata")
    graph.add_edge("fetch_metadata", "fetch_files")
    graph.add_edge("fetch_files", "fetch_commits")
    graph.add_edge("fetch_commits", "analyze_claude")
    graph.add_edge("analyze_claude", "parse_response")
    graph.add_edge("parse_response", END)

    return graph.compile()


# Singleton graph instance
_review_graph = None


def _get_review_graph():
    """Get or create the review graph."""
    global _review_graph
    if _review_graph is None:
        _review_graph = _build_review_graph()
    return _review_graph


async def run_review(
    request: ReviewRequest,
    progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> ReviewSummary:
    """
    Main async function to run a complete PR review.

    This is the entry point called by Phase 4 endpoints.

    Args:
        request: ReviewRequest with pr_url and optional focus_areas/custom_prompt
        progress_callback: Optional async callback for progress messages (for streaming)

    Returns:
        ReviewSummary with score, verdict, comments, and summary

    Raises:
        ValueError: If review fails or no result produced
    """
    try:
        logger.info(f"Starting review for PR: {request.pr_url}")

        # Initialize agent state
        initial_state: AgentState = {
            "request": request,
            "metadata": None,
            "pr_metadata_result": None,
            "pr_files_result": None,
            "pr_commits_result": None,
            "claude_response": None,
            "review_summary": None,
            "error": None,
            "progress_callback": progress_callback,
        }

        # Get the compiled graph
        graph = _get_review_graph()

        # Run the agent
        logger.info("Invoking LangGraph agent")
        final_state = await graph.ainvoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            logger.error(f"Review failed with error: {final_state['error']}")
            raise ValueError(final_state["error"])

        # Extract result
        review_summary = final_state.get("review_summary")
        if not review_summary:
            raise ValueError("Agent produced no review summary")

        logger.info(
            f"Review completed successfully: score={review_summary.overall_score}, "
            f"verdict={review_summary.verdict}"
        )
        return review_summary

    except Exception as e:
        logger.exception(f"Unexpected error in run_review: {e}")
        raise


__all__ = ["run_review"]
