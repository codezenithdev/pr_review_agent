"""
FastAPI router for PR review endpoints.

Provides three endpoints:
1. POST /api/review - Submit PR for review (returns immediately with job ID)
2. GET /api/review/{id} - Poll for review status and results
3. POST /api/review/stream - Stream review progress via Server-Sent Events (SSE)
"""

import json
import uuid
import logging
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.review import ReviewRequest, ReviewResponse, ReviewStatus
from app.agents.pr_agent import run_review

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["review"])

# In-memory job storage (MVP; Phase 7 can add database)
reviews_store: dict[str, ReviewResponse] = {}


@router.post("/review", response_model=ReviewResponse)
async def create_review(request: ReviewRequest) -> ReviewResponse:
    """
    Submit a GitHub PR for code review.

    Accepts a PR URL and optional focus areas/custom prompt.
    Returns immediately with a job ID and PENDING status.

    For MVP: blocks until review completes.
    Future: could use background tasks/job queue.

    Args:
        request: ReviewRequest with pr_url (required) and optional focus_areas, custom_prompt

    Returns:
        ReviewResponse with UUID, status (PENDING or COMPLETED), created_at, completed_at

    Raises:
        422: If ReviewRequest fails Pydantic validation (invalid PR URL, etc.)
        500: If unexpected error occurs during review
    """
    try:
        # Create response object with UUID
        review_id = str(uuid.uuid4())
        response = ReviewResponse(
            id=review_id,
            status=ReviewStatus.PENDING,
            result=None,
            created_at=datetime.utcnow(),
            completed_at=None,
        )

        # Store in-memory with PENDING status initially
        reviews_store[review_id] = response
        logger.info(
            f"Review job created: {review_id} for PR: {request.pr_url[:60]}..."
        )

        # Call Phase 3 agent to run the review
        try:
            summary = await run_review(request)
            response.result = summary
            response.status = ReviewStatus.COMPLETED
            response.completed_at = datetime.utcnow()
            logger.info(f"Review completed: {review_id}, score={summary.overall_score}")
        except Exception as e:
            logger.exception(f"Agent error for review {review_id}: {e}")
            response.status = ReviewStatus.FAILED
            response.completed_at = datetime.utcnow()
            reviews_store[review_id] = response
            raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

        # Update storage with final response
        reviews_store[review_id] = response
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in create_review: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/review/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str) -> ReviewResponse:
    """
    Retrieve review status and results by ID.

    Polls for the current status of a submitted review.
    If status is COMPLETED, includes the ReviewSummary result.
    If status is FAILED, review encountered an error.

    Args:
        review_id: UUID of the review job (returned by POST /api/review)

    Returns:
        ReviewResponse with current status, result (if completed), and timestamps

    Raises:
        404: If review ID not found in storage
    """
    if review_id not in reviews_store:
        logger.warning(f"Review not found: {review_id}")
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    response = reviews_store[review_id]
    logger.debug(f"Review status queried: {review_id}, status={response.status}")
    return response


@router.post("/review/stream")
async def stream_review(request: ReviewRequest):
    """
    Stream review progress via Server-Sent Events (SSE).

    Accepts a ReviewRequest and streams real-time progress updates.
    Emits status messages as the review progresses, ending with final ReviewSummary.

    SSE Event types:
    - data: "message" — Status update (e.g., "Fetching PR metadata...")
    - event: complete, data: {...ReviewSummary JSON...} — Review finished
    - event: error, data: {...error details...} — Review failed

    Args:
        request: ReviewRequest with pr_url (required) and optional focus_areas, custom_prompt

    Returns:
        StreamingResponse with text/event-stream media type

    Example SSE output:
        data: "Fetching PR metadata..."
        data: "Analyzing diffs..."
        data: "Running Openai review..."
        event: complete
        data: {"pr_title": "...", "overall_score": 82, ...full ReviewSummary...}
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for review progress."""
        try:
            logger.info(f"SSE stream started for PR: {request.pr_url[:60]}...")

            # Emit initial status
            yield f"data: \"Fetching PR metadata...\"\n\n"

            # Queue to collect progress messages from agent
            progress_messages = []

            async def progress_callback(message: str) -> None:
                """Called by agent nodes to report progress."""
                progress_messages.append(message)

            # Call Phase 3 agent with progress callback
            try:
                summary = await run_review(request, progress_callback=progress_callback)

                # Emit collected progress messages
                for msg in progress_messages:
                    yield f"data: {json.dumps(msg)}\n\n"

                # Emit final result
                result_json = summary.model_dump_json()
                yield f"event: complete\ndata: {result_json}\n\n"
                logger.info(f"SSE stream completed: PR review finished")

            except Exception as e:
                logger.exception(f"Agent error in stream_review: {e}")
                error_response = {"error": str(e), "type": type(e).__name__}
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"

        except Exception as e:
            logger.exception(f"Unexpected error in event_generator: {e}")
            error_response = {"error": "Internal server error", "detail": str(e)}
            yield f"event: error\ndata: {json.dumps(error_response)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable proxy buffering for real-time streaming
            "Connection": "keep-alive",
        },
    )
