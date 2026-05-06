"""Centralized screening decision policy.

Keep shortlist/review/reject cutoffs in one place so backend and frontend
can rely on the same contract and avoid drift.
"""

SHORTLIST_THRESHOLD = 63.0
REVIEW_THRESHOLD = 44.0
POLICY_VERSION = "2026-05-05.v1"


def get_screening_policy() -> dict:
    return {
        "shortlist_threshold": SHORTLIST_THRESHOLD,
        "review_threshold": REVIEW_THRESHOLD,
        "policy_version": POLICY_VERSION,
    }


def bucket_label(score: float) -> str:
    if score >= SHORTLIST_THRESHOLD:
        return "Shortlist"
    if score >= REVIEW_THRESHOLD:
        return "Review"
    return "Reject"
