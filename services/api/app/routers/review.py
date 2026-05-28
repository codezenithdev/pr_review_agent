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
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.models.review import ReviewRequest, ReviewResponse, ReviewStatus
from app.agents.pr_agent import run_review
from app.db import SessionLocal, ReviewRecord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["review"])


class ReviewFeedback(BaseModel):
    """User feedback on a completed review for LangSmith model improvement."""
    helpful: bool
    comment: Optional[str] = None


@router.post("/review", response_model=ReviewResponse)
async def create_review(request: ReviewRequest) -> ReviewResponse:
    """
    Submit a GitHub PR for code review.

    Accepts a PR URL and optional focus areas/custom prompt.
    Returns immediately with a job ID and status (blocks until review completes).

    Args:
        request: ReviewRequest with pr_url (required) and optional focus_areas, custom_prompt

    Returns:
        ReviewResponse with UUID, status, created_at, completed_at

    Raises:
        422: If ReviewRequest fails Pydantic validation
        500: If unexpected error occurs during review
    """
    db = SessionLocal()
    try:
        review_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        # Create database record with PENDING status
        db_record = ReviewRecord(
            id=review_id,
            pr_url=request.pr_url,
            status="in_progress",
            created_at=created_at,
        )
        db.add(db_record)
        db.commit()
        logger.info(f"Review job created: {review_id} for PR: {request.pr_url[:60]}...")

        # Call agent to run the review
        try:
            summary = await run_review(request)

            # Update database record with results
            db_record.status = "completed"
            db_record.result = summary.model_dump_json()
            db_record.completed_at = datetime.utcnow()
            db_record.pr_title = summary.pr_title
            db.commit()

            logger.info(f"Review completed: {review_id}, score={summary.overall_score}")

            return ReviewResponse(
                id=review_id,
                status=ReviewStatus.COMPLETED,
                result=summary,
                created_at=created_at,
                completed_at=db_record.completed_at,
            )

        except Exception as e:
            logger.exception(f"Agent error for review {review_id}: {e}")
            db_record.status = "failed"
            db_record.error = str(e)
            db_record.completed_at = datetime.utcnow()
            db.commit()
            raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in create_review: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        db.close()


@router.get("/review/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str) -> ReviewResponse:
    """
    Retrieve review status and results by ID.

    Args:
        review_id: UUID of the review job

    Returns:
        ReviewResponse with status, result, and timestamps

    Raises:
        404: If review ID not found
    """
    db = SessionLocal()
    try:
        record = db.query(ReviewRecord).filter(ReviewRecord.id == review_id).first()
        if not record:
            logger.warning(f"Review not found: {review_id}")
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

        result = None
        if record.result:
            import json
            result_dict = json.loads(record.result)
            from app.models.review import ReviewSummary
            result = ReviewSummary(**result_dict)

        logger.debug(f"Review status queried: {review_id}, status={record.status}")

        return ReviewResponse(
            id=record.id,
            status=ReviewStatus(record.status),
            result=result,
            created_at=record.created_at,
            completed_at=record.completed_at,
        )
    finally:
        db.close()


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


@router.post("/review/{review_id}/feedback")
async def submit_feedback(review_id: str, feedback: ReviewFeedback):
    """
    Submit feedback on a completed review for model improvement.

    Args:
        review_id: UUID of the completed review
        feedback: ReviewFeedback with helpful flag and optional comment

    Returns:
        JSON response with status and review_id

    Raises:
        404: If review ID not found
    """
    db = SessionLocal()
    try:
        record = db.query(ReviewRecord).filter(ReviewRecord.id == review_id).first()
        if not record:
            logger.warning(f"Feedback submission for non-existent review: {review_id}")
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

        # Store feedback in database
        import json
        feedback_data = {
            "helpful": feedback.helpful,
            "comment": feedback.comment,
            "submitted_at": datetime.utcnow().isoformat(),
        }
        record.feedback = feedback_data
        db.commit()

        # Send feedback to LangSmith for model improvement
        try:
            from langsmith import client as langsmith_client

            langsmith_client.create_feedback(
                run_id=review_id,
                key="helpful" if feedback.helpful else "not_helpful",
                score=1.0 if feedback.helpful else 0.0,
                comment=feedback.comment,
            )
            logger.info(f"Feedback recorded for review {review_id}: helpful={feedback.helpful}")
        except Exception as e:
            logger.warning(f"Error sending feedback to LangSmith: {e}")
            # Don't fail the request if LangSmith is unreachable

        return {"status": "feedback_recorded", "review_id": review_id}
    finally:
        db.close()
