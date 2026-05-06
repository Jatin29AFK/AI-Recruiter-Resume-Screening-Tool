from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class ExperienceRequirements(BaseModel):
    min_years_experience: Optional[int] = None
    max_years_experience: Optional[int] = None


class ScoringWeights(BaseModel):
    """Customizable scoring weights based on recruiter's feedback"""
    must_have_match: float = 0.40       # Required skills coverage
    relevant_experience: float = 0.20   # Experience relevance
    preferred_skills: float = 0.15      # Nice-to-have skills
    achievements_impact: float = 0.10   # Measurable impact/achievements
    industry_fit: float = 0.10          # Domain/industry alignment
    career_progression: float = 0.05    # Career growth/stability


class JDRequirements(BaseModel):
    required_skills: list[str]
    preferred_skills: list[str]
    general_skills: list[str]
    experience_requirements: ExperienceRequirements
    education_requirements: list[str]
    mandatory_certifications: list[str] = []
    scoring_weights: Optional[ScoringWeights] = None


class EvidenceItem(BaseModel):
    skill: str
    mentioned_in: list[str]
    supporting_lines: list[str]
    has_action_evidence: bool
    evidence_strength: str


class EvidenceSummary(BaseModel):
    strong_evidence_skills: list[str]
    medium_evidence_skills: list[str]
    weak_evidence_skills: list[str]
    skill_support_score: float


class ExperienceEstimate(BaseModel):
    estimated_years: Optional[float] = None
    estimated_months: Optional[int] = None
    ranges_found: list[tuple[int, int]]
    note: str


class ExperienceComparison(BaseModel):
    meets_requirement: Optional[bool] = None
    gap_years: Optional[float] = None
    message: str


class MatchScores(BaseModel):
    required_skill_score: float
    preferred_skill_score: float
    general_skill_score: float
    weighted_skill_score: float
    semantic_score: float
    section_evidence_score: float
    skill_support_score: float
    critical_missing_penalty: float
    overall_score: float
    fit_label: str
    # New recruiter-focused dimensions
    career_progression_score: float = 0.0
    achievements_score: float = 0.0
    industry_fit_score: float = 0.0
    leadership_signals: list[str] = []
    red_flags: list[str] = []
    shortlist_recommendation: bool = False
    recruiter_action: str = ""


class LLMExplanation(BaseModel):
    fit_summary: str
    strengths: list[str]
    weaknesses: list[str]
    llm_recommendations: list[str]
    provider: str


class StructuredResume(BaseModel):
    full_name: str = ""
    current_title: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    location: str = ""
    headline: str = ""
    summary: str = ""
    skills: list[str]
    experience_bullets: list[str]
    project_bullets: list[str]
    education: str = ""
    certifications: str = ""


class ATSAuditIssue(BaseModel):
    title: str
    severity: str
    details: str
    recommendation: str


class ATSAuditReport(BaseModel):
    score: float
    grade: str
    issues: list[ATSAuditIssue]
    quick_fixes: list[str]


class KeywordCoverageItem(BaseModel):
    skill: str
    priority: str
    status: str
    evidence_sections: list[str]
    supporting_lines: list[str] = []


class KeywordCoverageSummary(BaseModel):
    strong_count: int
    medium_count: int
    weak_count: int
    missing_count: int


class KeywordCoverageReport(BaseModel):
    items: list[KeywordCoverageItem]
    summary: KeywordCoverageSummary


class ShortlistSimulation(BaseModel):
    verdict: str
    reasons: list[str]
    action_plan: list[str]


class AnalysisSnapshot(BaseModel):
    overall_score: float
    fit_label: str
    matched_skills: list[str]
    missing_skills: list[str]
    critical_missing_skills: list[str]


class TailoringPlan(BaseModel):
    target_role_keywords: list[str]
    skills_to_emphasize: list[str]
    skills_not_allowed_to_add: list[str]
    allowed_skill_terms: list[str]
    sections_to_rewrite: list[str]
    unresolved_gaps: list[str]
    manual_review_notice: str
    user_should_review_on_own: bool


class TailoredResumeDraft(BaseModel):
    headline: str
    summary: str
    skills: list[str]
    experience_bullets: list[str]
    project_bullets: list[str]
    change_log: list[str]
    manual_review_note: str
    unresolved_gaps: list[str]


class TailorValidation(BaseModel):
    unsupported_added_terms: list[str]
    safe_to_export: bool
    manual_review_required: bool
    manual_review_notice: str
    validator_notes: list[str]


class ResumeTailorResponse(BaseModel):
    analysis_before: AnalysisSnapshot
    tailoring_plan: TailoringPlan
    structured_resume: StructuredResume
    tailored_resume: TailoredResumeDraft
    validation: TailorValidation
    analysis_after: AnalysisSnapshot
    score_delta: float
    manual_review_notice: str
    user_should_review_on_own: bool


class JDComparisonItem(BaseModel):
    jd_index: int
    jd_title: str
    overall_score: float
    fit_label: str
    required_skill_score: float
    skill_support_score: float
    critical_missing_skills: list[str]
    matched_skills: list[str]
    recommendation_verdict: Optional[str] = None  # Strongly Recommended | Recommended | Borderline | Not Recommended


class MultiJDCompareResponse(BaseModel):
    resume_filename: str
    comparisons: list[JDComparisonItem]
    best_match: Optional[JDComparisonItem] = None


class DomainDetectionResult(BaseModel):
    domain: str
    label: str
    score: float
    confidence: str
    all_scores: dict[str, float]


class AnalysisMeta(BaseModel):
    reliability: str
    warning_message: Optional[str] = None
    resume_domain: DomainDetectionResult
    jd_domain: DomainDetectionResult
    active_domain: DomainDetectionResult


# ── Recommendation models ──────────────────────────────────────────────────

class SectionScore(BaseModel):
    name: str
    score: int
    explanation: str


class FinalRecommendation(BaseModel):
    label: str           # Strongly Recommended | Recommended | Borderline | Not Recommended
    badge_color: str     # green | yellow | red
    justification: str


class RecommendationReport(BaseModel):
    section_scores: list[SectionScore]
    key_strengths: list[str]
    gaps_and_risks: list[str]
    final_recommendation: FinalRecommendation


class MatchAnalysisResponse(BaseModel):
    filename: str
    raw_resume_text: str
    resume_serve_id: Optional[str] = None
    resume_sections: dict[str, str]
    structured_resume: StructuredResume
    section_skill_map: dict[str, list[str]]
    resume_skills: list[str]
    jd_requirements: JDRequirements
    categorized_resume_skills: dict[str, list[str]]
    categorized_jd_skills: dict[str, list[str]]
    matched_skills: list[str]
    missing_skills: list[str]
    critical_missing_skills: list[str]
    preferred_missing_skills: list[str]
    fuzzy_matches: list[tuple[str, str, float]]
    skill_evidence_map: dict[str, EvidenceItem]
    evidence_summary: EvidenceSummary
    experience_estimate: ExperienceEstimate
    experience_comparison: ExperienceComparison
    scores: MatchScores
    suggestions: list[str]
    llm_explanation: Optional[LLMExplanation] = None
    ats_audit: ATSAuditReport
    keyword_coverage: KeywordCoverageReport
    shortlist_simulation: ShortlistSimulation
    analysis_meta: Optional[AnalysisMeta] = None
    resume_domain: Optional[DomainDetectionResult] = None
    jd_domain: Optional[DomainDetectionResult] = None
    recommendation: Optional[RecommendationReport] = None
    is_likely_resume: bool = True
    resume_file_warning: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str


# ── Recruiter / Batch screening models ──────────────────────────────────────

class CandidateSummary(BaseModel):
    candidate_id: Optional[str] = None
    candidate_index: int
    filename: str
    overall_score: float
    fit_label: str
    ats_score: float
    required_skill_score: float
    skill_support_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    critical_missing_skills: list[str]
    estimated_experience_years: Optional[float] = None
    experience_meets_requirement: Optional[bool] = None
    shortlist_verdict: str          # "Shortlist" | "Review" | "Reject"
    backend_verdict: Optional[str] = None
    shortlist_reasons: list[str]
    ats_issues_count: int
    keyword_strong_count: int
    keyword_missing_count: int
    recommendation: Optional[RecommendationReport] = None
    linkedin_url: Optional[str] = None
    # New recruiter-focused fields
    career_progression_score: float = 0.0
    achievements_score: float = 0.0
    industry_fit_score: float = 0.0
    leadership_signals: list[str] = []
    red_flags: list[str] = []
    # Language quality analysis
    language_quality: dict = {}
    over_tailoring_flag: bool = False
    # Education fit & non-negotiable advisory flags
    education_meets_requirement: Optional[bool] = None
    non_negotiable_flags: list[str] = []
    seniority_level: str = 'mid'
    # Resume text for viewing (parsed)
    resume_text: Optional[str] = None
    # Serve ID for downloading the original uploaded file
    resume_serve_id: Optional[str] = None
    # Evidence summary for detail panel
    evidence_summary: Optional[dict] = None
    # Timeline gap analysis
    timeline_gaps: list[str] = []
    # Full ATS issues list for drill-down
    ats_issues: list[dict] = []
    # Keyword coverage items with evidence for drill-down
    keyword_coverage_items: list[dict] = []
    # Primary coverage info (helps explain when JD has no explicit 'Required' section)
    primary_coverage: float = 0.0
    primary_coverage_source: str = 'required'  # 'required' or 'preferred+general'
    # Required skills counts (for clearer recruiter UI)
    required_skills_count: int = 0
    required_skills_matched_count: int = 0
    # Backend-first non-negotiable screening verdict
    non_negotiable_verdict: str = "pass"  # pass | review | reject
    non_negotiable_reasons: list[str] = []
    review_flags: list[str] = []


class BatchFileOutcome(BaseModel):
    filename: str
    status: str  # analyzed | skipped_non_resume | failed_analysis
    reason_code: Optional[str] = None
    message: Optional[str] = None


class ScreeningPolicy(BaseModel):
    shortlist_threshold: float
    review_threshold: float
    policy_version: str


class BatchAnalysisResponse(BaseModel):
    jd_title: str
    total_candidates: int
    policy: ScreeningPolicy
    shortlisted: list[CandidateSummary]
    review: list[CandidateSummary]
    rejected: list[CandidateSummary]
    all_candidates: list[CandidateSummary]
    skipped_files: list[str] = []
    failed_files: list[str] = []
    file_outcomes: list[BatchFileOutcome] = []


# ── Job Management ─────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience: Optional[int] = None
    education_requirements: Optional[list[str]] = []
    mandatory_certifications: Optional[list[str]] = []
    tags: Optional[list[str]] = []


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    min_experience: Optional[int] = None
    education_requirements: Optional[list[str]] = None
    mandatory_certifications: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class Job(BaseModel):
    job_id: str
    title: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience: Optional[int] = None
    education_requirements: list[str] = []
    mandatory_certifications: list[str] = []
    tags: list[str]
    created_at: str
    updated_at: str
    recruiter_id: str = "default"


class JobListResponse(BaseModel):
    jobs: list[Job]
    total: int


# ── Recruiter Notes ────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    candidate_id: str
    content: str


class NoteUpdate(BaseModel):
    content: str


class RecruiterNote(BaseModel):
    note_id: str
    candidate_id: str
    recruiter_id: str
    content: str
    created_at: str
    updated_at: str


class NoteListResponse(BaseModel):
    notes: list[RecruiterNote]
    total: int


# ── Candidate Status Tracking ──────────────────────────────────────────────

class CandidateStatus(str, Enum):
    NEW = "New"
    SCREENING = "Screening"
    PHONE_SCREEN = "Phone Screen"
    INTERVIEW = "Interview"
    TECHNICAL_ROUND = "Technical Round"
    OFFER = "Offer"
    HIRED = "Hired"
    REJECTED = "Rejected"
    ON_HOLD = "On Hold"


class StatusHistoryEntry(BaseModel):
    status: str
    changed_at: str
    changed_by: str
    note: Optional[str] = None


class CandidateStatusUpdate(BaseModel):
    candidate_id: str
    status: CandidateStatus
    note: Optional[str] = None


class CandidateStatusBatchRequest(BaseModel):
    candidate_ids: list[str]


class CandidateWithStatus(CandidateSummary):
    candidate_id: str
    status: str = "New"
    status_history: list[StatusHistoryEntry] = []
    recruiter_notes_count: int = 0
    tags: list[str] = []
    all_candidates: list[CandidateSummary]   # sorted by score desc
