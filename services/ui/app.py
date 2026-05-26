"""
PR Review Agent - Streamlit UI

Full-stack web interface for automated GitHub PR code reviews.
Consumes FastAPI backend at http://localhost:8000
"""

import streamlit as st
import requests
import json
from datetime import datetime
import time

# Configuration
BACKEND_URL = "http://localhost:8000"
REVIEW_ENDPOINT = f"{BACKEND_URL}/api/review"
STREAM_ENDPOINT = f"{BACKEND_URL}/api/review/stream"

# Page configuration
st.set_page_config(
    page_title="PR Review Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background: #d4edda;
        padding: 12px;
        border-radius: 6px;
        margin: 5px 0;
    }
    .error-box {
        background: #f8d7da;
        padding: 12px;
        border-radius: 6px;
        margin: 5px 0;
    }
    .warning-box {
        background: #fff3cd;
        padding: 12px;
        border-radius: 6px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "reviews" not in st.session_state:
    st.session_state.reviews = {}
if "current_pr_url" not in st.session_state:
    st.session_state.current_pr_url = ""
if "current_review" not in st.session_state:
    st.session_state.current_review = None
if "backend_available" not in st.session_state:
    st.session_state.backend_available = True

# Helper functions
def check_backend_health():
    """Check if backend is available"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def submit_review(pr_url, focus_areas, custom_prompt):
    """Submit PR for review via sync endpoint"""
    try:
        payload = {
            "pr_url": pr_url,
            "focus_areas": focus_areas if focus_areas else None,
            "custom_prompt": custom_prompt if custom_prompt else None
        }

        with st.spinner("🔄 Analyzing PR..."):
            response = requests.post(REVIEW_ENDPOINT, json=payload, timeout=120)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Backend error: {response.status_code}")
            st.json(response.json())
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Connection error: {str(e)}")
        return None

def stream_review(pr_url, focus_areas, custom_prompt):
    """Submit PR for review via streaming endpoint with progress"""
    try:
        payload = {
            "pr_url": pr_url,
            "focus_areas": focus_areas if focus_areas else None,
            "custom_prompt": custom_prompt if custom_prompt else None
        }

        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        with progress_placeholder.container():
            progress_bar = st.progress(0)
            status_text = status_placeholder.empty()

        progress_value = 0
        messages = []
        review_data = None

        try:
            with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=120) as r:
                if r.status_code != 200:
                    st.error(f"Backend error: {r.status_code}")
                    progress_placeholder.empty()
                    return None

                for line in r.iter_lines():
                    if line:
                        line_str = line.decode('utf-8') if isinstance(line, bytes) else line

                        # Handle event markers
                        if line_str.startswith("event:"):
                            event_type = line_str.split(":", 1)[1].strip()
                            if event_type == "complete":
                                status_text.text("✅ Review complete!")
                                progress_bar.progress(1.0)

                        # Handle data payloads
                        elif line_str.startswith("data:"):
                            data_str = line_str.split(":", 1)[1].strip()

                            # Try to parse as JSON (final result)
                            try:
                                data = json.loads(data_str)
                                if isinstance(data, dict) and ("overall_score" in data or "error" in data):
                                    review_data = data
                                    progress_bar.progress(1.0)
                                else:
                                    # Progress message
                                    if isinstance(data, str):
                                        messages.append(data)
                                        status_text.text(f"🔄 {data}")
                                        progress_value = min(progress_value + 0.15, 0.85)
                                        progress_bar.progress(progress_value)
                            except json.JSONDecodeError:
                                # Plain text message
                                if data_str and not data_str.startswith("{"):
                                    messages.append(data_str.strip('"'))
                                    status_text.text(f"🔄 {data_str.strip('\"')}")
                                    progress_value = min(progress_value + 0.15, 0.85)
                                    progress_bar.progress(progress_value)

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Connection error: {str(e)}")
            progress_placeholder.empty()
            return None

        # Clear progress indicators
        time.sleep(0.5)
        progress_placeholder.empty()

        return review_data

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def display_review_results(review):
    """Display formatted review results"""
    if not review:
        st.error("No review data available")
        return

    # Handle error responses
    if "error" in review:
        st.error(f"❌ Review failed: {review.get('error', 'Unknown error')}")
        return

    st.markdown("---")
    st.header("📋 Review Results")

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        score = review.get("overall_score", 0)
        st.metric("Overall Score", score, f"{score}/100")

    with col2:
        verdict = review.get("verdict", "unknown")
        verdict_emoji = {
            "approve": "✅",
            "approve_with_suggestions": "⚠️",
            "request_changes": "❌",
            "comment": "💬"
        }.get(verdict, "❓")
        st.metric("Verdict", f"{verdict_emoji}")
        st.caption(verdict.replace("_", " ").title())

    with col3:
        comment_count = len(review.get("comments", []))
        st.metric("Comments", comment_count)

    with col4:
        critical_count = len(review.get("critical_issues", []))
        severity = "🔴" if critical_count > 0 else "✅"
        st.metric("Critical Issues", critical_count, severity)

    # Summary section
    st.subheader("📝 Summary")
    st.info(review.get("summary", "No summary available"))

    # Strengths section
    if review.get("strengths"):
        st.subheader("✨ Strengths")
        for strength in review["strengths"]:
            st.success(f"✓ {strength}")

    # Critical issues section
    if review.get("critical_issues"):
        st.subheader("🚨 Critical Issues")
        for issue in review["critical_issues"]:
            st.error(f"⚠ {issue}")

    # Detailed comments section
    if review.get("comments"):
        st.subheader("💬 Detailed Comments")

        for i, comment in enumerate(review["comments"], 1):
            severity = comment.get("severity", "info").upper()
            severity_emoji = {
                "CRITICAL": "🔴",
                "WARNING": "🟠",
                "INFO": "🔵"
            }.get(severity, "⚪")

            file_name = comment.get("file", "unknown").split("/")[-1]
            line_info = f":{comment.get('line')}" if comment.get('line') else ""

            with st.expander(f"{severity_emoji} [{comment.get('category', 'general').upper()}] {file_name}{line_info} — {comment.get('title', 'No title')}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Severity:** {severity}")
                    st.markdown(f"**Category:** {comment.get('category', 'N/A')}")

                with col2:
                    st.markdown(f"**File:** `{comment.get('file', 'unknown')}`")
                    st.markdown(f"**Line:** {comment.get('line', 'Whole file')}")

                st.markdown("---")
                st.write(comment.get("body", "No description"))

                if comment.get("suggestion"):
                    st.markdown("**Suggestion:**")
                    st.code(comment["suggestion"], language="python")

    # Export options
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        json_str = json.dumps(review, indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=json_str,
            file_name=f"review_{review.get('pr_url', 'unknown').split('/')[-1]}.json",
            mime="application/json"
        )

    with col2:
        if st.button("🔄 Start New Review"):
            st.session_state.current_pr_url = ""
            st.session_state.current_review = None
            st.rerun()

    with col3:
        st.metric("Review Date", datetime.now().strftime("%Y-%m-%d %H:%M"))

# Main UI
st.markdown("""
# 🔍 PR Review Agent

Automated code review powered by Claude, LangGraph, and GitHub
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    # Backend status
    backend_available = check_backend_health()
    if backend_available:
        st.success("✅ Backend connected")
    else:
        st.error("❌ Backend unavailable (http://localhost:8000)")

    st.divider()

    # Review options
    st.subheader("Review Options")
    focus_areas = st.multiselect(
        "Focus Areas",
        ["security", "performance", "maintainability", "testability", "best_practices"],
        default=["security", "performance"],
        help="Areas to emphasize in the review"
    )

    custom_prompt = st.text_area(
        "Custom Instructions (Optional)",
        placeholder="Add any specific review guidelines or focus points...",
        height=100
    )

    st.divider()

    # Usage info
    st.subheader("ℹ️ How to Use")
    st.markdown("""
    1. Enter a GitHub PR URL
    2. Optionally select focus areas
    3. Click "Review PR"
    4. Watch progress in real-time
    5. Review results appear below
    6. Download as JSON if needed
    """)

    st.divider()
    st.caption("Phase 5: Streamlit UI | Backend: Phase 3-4 ✅")

# Main content
col1, col2 = st.columns([4, 1])

with col1:
    pr_url = st.text_input(
        "GitHub PR URL",
        placeholder="https://github.com/owner/repo/pull/123",
        value=st.session_state.current_pr_url,
        help="Full URL to the GitHub Pull Request"
    )

with col2:
    review_button = st.button(
        "📤 Review PR",
        use_container_width=True,
        type="primary",
        disabled=not backend_available
    )

# Process review submission
if review_button:
    if not pr_url:
        st.error("❌ Please enter a PR URL")
    elif not pr_url.startswith("https://github.com/"):
        st.error("❌ Invalid GitHub URL format")
    else:
        st.session_state.current_pr_url = pr_url

        # Try streaming first, fall back to sync if needed
        review_data = stream_review(pr_url, focus_areas, custom_prompt)

        if review_data:
            st.session_state.current_review = review_data
            st.session_state.reviews[pr_url] = review_data
            st.rerun()
        else:
            st.error("❌ Failed to get review results")

# Display current review if available
if st.session_state.current_review:
    display_review_results(st.session_state.current_review)

# Review history (optional)
if st.session_state.reviews and len(st.session_state.reviews) > 1:
    with st.sidebar:
        st.divider()
        st.subheader("📚 Review History")
        for url, review in list(st.session_state.reviews.items())[-5:]:
            pr_num = url.split("/")[-1]
            score = review.get("overall_score", "?")
            if st.button(f"PR #{pr_num} (Score: {score})", key=f"history_{pr_num}"):
                st.session_state.current_pr_url = url
                st.session_state.current_review = review
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px; color: #666;">
<p>🚀 <strong>PR Review Agent</strong> | Powered by Claude + LangGraph + FastAPI + Streamlit</p>
<p style="font-size: 12px;">Backend: http://localhost:8000 | Frontend: http://localhost:8501</p>
</div>
""", unsafe_allow_html=True)
