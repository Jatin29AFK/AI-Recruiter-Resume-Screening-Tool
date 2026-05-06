def get_fit_label(score: float) -> str:
    if score >= 85:
        return "Excellent Fit"
    elif score >= 63:
        return "Good Fit"
    elif score >= 48:
        return "Average Fit"
    return "Low Fit"


def calculate_section_evidence_score(
    matched_skills: list[str],
    section_skill_map: dict[str, list[str]]
) -> float:
    weights = {
        "skills": 0.25,
        "experience": 0.35,
        "projects": 0.25,
        "summary": 0.10,
        "certifications": 0.05
    }

    if not matched_skills:
        return 0.0

    matched_set = set(matched_skills)
    score = 0.0

    for section, weight in weights.items():
        section_skills = set(section_skill_map.get(section, []))
        overlap = matched_set.intersection(section_skills)
        section_ratio = len(overlap) / len(matched_set) if matched_set else 0.0
        score += weight * section_ratio

    return min(score, 1.0)


def calculate_weighted_skill_score(
    matched_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    general_skills: list[str]
) -> dict:
    matched_set = set(matched_skills)
    required_set = set(required_skills)
    preferred_set = set(preferred_skills)
    general_set = set(general_skills)

    required_score = len(matched_set.intersection(required_set)) / len(required_set) if required_set else 0.0
    preferred_score = len(matched_set.intersection(preferred_set)) / len(preferred_set) if preferred_set else 0.0
    general_score = len(matched_set.intersection(general_set)) / len(general_set) if general_set else 0.0

    weighted_skill_score = (
        0.55 * required_score +
        0.10 * preferred_score +
        0.35 * general_score
    )

    return {
        "required_skill_score": round(required_score * 100, 2),
        "preferred_skill_score": round(preferred_score * 100, 2),
        "general_skill_score": round(general_score * 100, 2),
        "weighted_skill_score": round(weighted_skill_score * 100, 2),
        "weighted_skill_score_raw": weighted_skill_score
    }


def calculate_match_score(
    matched_skills: list[str],
    semantic_score: float,
    section_skill_map: dict[str, list[str]],
    required_skills: list[str],
    preferred_skills: list[str],
    general_skills: list[str],
    critical_missing_skills: list[str],
    skill_support_score: float,
    career_progression_score: float = 50.0,
    achievements_score: float = 0.0,
    industry_fit_score: float = 50.0,
    scoring_weights: dict = None,
    required_skill_groups: list[list[str]] = None,
) -> dict:
    """
    Score a resume against a JD in a way that mirrors natural HR shortlisting.

    Key design decisions
    --------------------
    1.  primary_coverage adapts when the JD has no required section: falls back
        to preferred+general coverage so JDs without an explicit "Required:"
        header still differentiate candidates properly.

    2.  skill_breadth = matched / all_jd_skills.  Rewards candidates who cover
        many JD skills even when those skills aren't in the required tier.

    3.  Semantic similarity now uses CountVectorizer (not TF-IDF) so shared
        domain vocabulary actually contributes to the score (~40-60% for
        genuine matches instead of the previous 13-17%).

    4.  No blunt "N matches → floor" rules.  Every component is proportional so
        poor matches score low and strong matches score high.  The only floor is
        coverage-based: primary_coverage ≥ 80 % → overall ≥ 55 %.

    5.  achievements_score defaults to 35 % (not 0) when no quantified data is
        available, avoiding penalising resumes that are light on numbers.
    """
    weighted_skill = calculate_weighted_skill_score(
        matched_skills=matched_skills,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        general_skills=general_skills,
    )

    evidence_score    = calculate_section_evidence_score(matched_skills, section_skill_map)
    support_score_raw = skill_support_score / 100.0

    # Compute required score. If the JD defines alternative groups (e.g.
    # "at least one of the following languages"), treat each group as a
    # single requirement unit satisfied when any member appears in the
    # resume. This avoids unfairly penalizing candidates when JD lists
    # multiple language alternatives.
    matched_set = set(matched_skills)
    required_set = set(required_skills)

    if required_skill_groups:
        groups = [set(g) for g in required_skill_groups if g]
        # Standalone requireds are those not covered by any group
        standalone_requireds = [r for r in required_skills if not any(r in g for g in groups)]
        units = groups + [set([r]) for r in standalone_requireds]
        satisfied_units = sum(1 for u in units if len(u & matched_set) > 0)
        required_score_raw = satisfied_units / max(len(units), 1)
        required_units_count = len(units)
        required_units_matched_count = satisfied_units
    else:
        required_score_raw = weighted_skill["required_skill_score"] / 100.0
        required_units_count = len(required_set)
        required_units_matched_count = len(matched_set & required_set)
    preferred_score_raw = weighted_skill["preferred_skill_score"] / 100.0
    general_score_raw   = weighted_skill["general_skill_score"]  / 100.0
    achievements_raw    = achievements_score / 100.0
    industry_raw        = industry_fit_score  / 100.0
    career_raw          = career_progression_score / 100.0

    required_set  = set(required_skills)
    preferred_set = set(preferred_skills)
    general_set   = set(general_skills)
    matched_set   = set(matched_skills)

    # ── Primary coverage ──────────────────────────────────────────────────────
    # When the JD defines explicit required skills, use those.
    # When it doesn't (required_skills=[]), fall back to preferred+general —
    # common in real job posts whose authors skipped the "Required:" header.
    # Compute penalty relative to the number of requirement units (groups + standalone)
    if required_units_count:
        # Cap at 0.05 so 2 missing out of 5 required only costs 5 points, not 12.
        crit_penalty = min(len(critical_missing_skills) / max(required_units_count, 1), 0.05)
    else:
        crit_penalty = 0.0

    if required_set or required_skill_groups:
        primary_coverage = max(0.0, required_score_raw - crit_penalty)
        primary_coverage_source = "required"
    elif preferred_set:
        # If JD has no explicit required section, treat preferred as the
        # primary signal. General/nice-to-have should help only as a bonus,
        # not dilute the denominator.
        preferred_coverage = len(matched_set & preferred_set) / max(len(preferred_set), 1)
        general_bonus = 0.15 * (len(matched_set & general_set) / max(len(general_set), 1)) if general_set else 0.0
        primary_coverage = min(1.0, preferred_coverage + general_bonus)
        crit_penalty = 0.0
        primary_coverage_source = "preferred(+general bonus)"
    else:
        primary_coverage = len(matched_set & general_set) / max(len(general_set), 1)
        crit_penalty = 0.0
        primary_coverage_source = "general"

    # ── Skill breadth ─────────────────────────────────────────────────────────
    if required_set or required_skill_groups:
        breadth_pool = required_set | preferred_set | general_set
    elif preferred_set:
        breadth_pool = preferred_set
    else:
        breadth_pool = general_set

    skill_breadth = min(len(matched_set & breadth_pool) / max(len(breadth_pool), 1), 1.0)

    # Must-have dimension: primary coverage is the headline signal;
    # breadth rewards broader JD alignment even when exact required keywords differ.
    must_have_score = 0.65 * primary_coverage + 0.35 * skill_breadth

    # ── Relevant-experience dimension ─────────────────────────────────────────
    # Semantic similarity (CountVectorizer cosine) is consistently low (10-30%)
    # for short JDs vs long resumes and should not dominate this component.
    # Skill-evidence and section-support are more reliable signals.
    relevant_exp = (
        0.20 * semantic_score   +   # domain vocabulary overlap (CountVectorizer)
        0.50 * evidence_score   +   # skills backed by work/project bullets
        0.30 * support_score_raw    # skills corroborated across sections
    )

    # Achievements: treat unknown as 35 % rather than 0 to avoid unfair penalty
    effective_achievements = max(achievements_raw, 0.35)

    # ── Final weighted blend ──────────────────────────────────────────────────
    overall_score = (
        0.35 * must_have_score        +
        0.35 * relevant_exp           +
        0.12 * effective_achievements +
        0.10 * preferred_score_raw    +
        0.05 * career_raw             +
        0.03 * industry_raw
    )

    # ── Coverage-based floor ─────────────────────────────────────────────────
    # Graduated floors ensure realistic scores that track skill coverage.
    # Required JDs: stricter (explicit requirements listed).
    # Preferred-only JDs: more generous (skills are aspirational, not mandatory).
    if required_set or required_skill_groups:
        if primary_coverage >= 0.80:
            if support_score_raw >= 0.60 or evidence_score >= 0.55:
                overall_score = max(overall_score, 0.72)
            else:
                overall_score = max(overall_score, 0.60)
        elif primary_coverage >= 0.60:
            overall_score = max(overall_score, 0.55)
        elif primary_coverage >= 0.50:
            overall_score = max(overall_score, 0.50)
        elif primary_coverage >= 0.40:
            overall_score = max(overall_score, 0.46)
        elif primary_coverage >= 0.25:
            overall_score = max(overall_score, 0.42)
    elif preferred_set:
        # Preferred-only JDs: matching half the preferred skills → Good Fit.
        if primary_coverage >= 0.65:
            overall_score = max(overall_score, 0.72)
        elif primary_coverage >= 0.50:
            overall_score = max(overall_score, 0.65)
        elif primary_coverage >= 0.35:
            overall_score = max(overall_score, 0.58)
        elif primary_coverage >= 0.25:
            overall_score = max(overall_score, 0.52)
        elif preferred_score_raw >= 0.15:
            overall_score = max(overall_score, 0.46)

    overall_score   = max(0.0, min(overall_score, 1.0))
    overall_percent = round(overall_score * 100, 2)

    # raw_penalty kept for output compatibility
    raw_penalty       = crit_penalty
    effective_penalty = crit_penalty

    # ── Shortlist recommendation ──────────────────────────────────────────────
    # Candidate is worth shortlisting when they score ≥ 65 overall OR cover
    # ≥ 80 % of required skills (even if some other signals are weaker).
    shortlist_recommendation = overall_percent >= 65 or primary_coverage >= 0.80

    if overall_percent >= 85:
        recruiter_action = "Prioritize – top candidate, interview immediately"
    elif overall_percent >= 70:
        recruiter_action = "Shortlist – strong match, recommend for screening"
    elif overall_percent >= 50:
        recruiter_action = "Consider – potential fit, worth a screening call"
    else:
        recruiter_action = "Low priority – significant skill or experience gaps"

    # Provide primary coverage info so callers can explain whether the
    # headline coverage came from required, preferred, or general fallback.
    primary_coverage_percent = round(primary_coverage * 100, 2)

    return {
        "required_skill_score": round(required_score_raw * 100, 2),
        "preferred_skill_score": weighted_skill["preferred_skill_score"],
        "general_skill_score": weighted_skill["general_skill_score"],
        "weighted_skill_score": weighted_skill["weighted_skill_score"],
        "semantic_score": round(semantic_score * 100, 2),
        "section_evidence_score": round(evidence_score * 100, 2),
        "skill_support_score": round(skill_support_score, 2),
        "critical_missing_penalty": round(raw_penalty * 100, 2),
        "overall_score": overall_percent,
        "fit_label": get_fit_label(overall_percent),
        "career_progression_score": round(career_progression_score, 2),
        "achievements_score": round(achievements_score, 2),
        "industry_fit_score": round(industry_fit_score, 2),
        "primary_coverage": primary_coverage_percent,
        "primary_coverage_source": primary_coverage_source,
        "required_skills_count": required_units_count,
        "required_skills_matched_count": required_units_matched_count,
        "shortlist_recommendation": shortlist_recommendation,
        "recruiter_action": recruiter_action,
    }
    """
    Calculate match score with recruiter-focused dimensions:
    - Must-have match (required skills)
    - Relevant experience (semantic + section evidence)
    - Preferred skills
    - Achievements/impact
    - Industry/domain fit
    - Career progression/stability
    """
    # ── Scoring weights ───────────────────────────────────────────────────────
    # Natural shortlisting: semantic/experience drives the score, not just
    # required-skill exact match. This prevents candidates with equivalent tech
    # stacks (e.g. Java instead of Python) from scoring near 0.
    if scoring_weights is None:
        if not lenient:
            scoring_weights = {
                'must_have_match': 0.25,      # blended required+general; was 0.40
                'relevant_experience': 0.38,  # semantic + evidence; was 0.20
                'preferred_skills': 0.15,
                'achievements_impact': 0.08,
                'industry_fit': 0.09,
                'career_progression': 0.05,
            }
        else:
            # Lenient mode: even more experience-first
            scoring_weights = {
                'must_have_match': 0.18,
                'relevant_experience': 0.45,
                'preferred_skills': 0.17,
                'achievements_impact': 0.08,
                'industry_fit': 0.07,
                'career_progression': 0.05,
            }
    else:
        if lenient and 'must_have_match' in scoring_weights:
            scoring_weights['must_have_match'] = scoring_weights.get('must_have_match', 0.25) * 0.7
            total = sum(scoring_weights.values())
            if total > 0:
                for k in scoring_weights:
                    scoring_weights[k] = scoring_weights[k] / total

    weighted_skill = calculate_weighted_skill_score(
        matched_skills=matched_skills,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        general_skills=general_skills
    )

    evidence_score = calculate_section_evidence_score(matched_skills, section_skill_map)
    support_score_raw = skill_support_score / 100.0

    # Relevant experience: semantic similarity is the most robust cross-stack signal
    relevant_experience_score = (
        0.55 * semantic_score +
        0.25 * evidence_score +
        0.20 * support_score_raw
    )

    # ── Must-have dimension: blend required + general skill coverage ──────────
    # Previously only used required_skill_score, which zeroes-out a candidate
    # who has the right general tech stack but different exact keywords.
    required_score_raw = weighted_skill["required_skill_score"] / 100.0
    general_score_raw  = weighted_skill["general_skill_score"] / 100.0
    preferred_raw      = weighted_skill["preferred_skill_score"] / 100.0
    achievements_raw   = achievements_score / 100.0
    industry_raw       = industry_fit_score / 100.0
    career_raw         = career_progression_score / 100.0

    # Penalty only applies to the required-skills portion (not general/preferred),
    # and is capped more conservatively so a missing keyword doesn't wipe out
    # credit from a broadly-matching profile.
    total_priority_skills = len(required_skills) + len(preferred_skills) + len(general_skills)
    raw_penalty = len(critical_missing_skills) / max(total_priority_skills, 1)
    required_penalty = min(raw_penalty, 0.15)  # tighter cap
    if lenient:
        required_penalty *= 0.5

    must_have_adjusted = (
        0.60 * max(0.0, required_score_raw - required_penalty) +
        0.40 * general_score_raw  # general skills credit always preserved
    )

    # Calculate overall score using recruiter-defined weights
    overall_score = (
        scoring_weights['must_have_match']    * must_have_adjusted +
        scoring_weights['relevant_experience'] * relevant_experience_score +
        scoring_weights['preferred_skills']   * preferred_raw +
        scoring_weights['achievements_impact'] * achievements_raw +
        scoring_weights['industry_fit']       * industry_raw +
        scoring_weights['career_progression'] * career_raw
    )

    # ── Floor score ───────────────────────────────────────────────────────────
    # 1) Required-skill floor: covering most required skills is unambiguous fit.
    #    A semantic score of 17% shouldn't override 100% required skill match.
    if required_score_raw >= 0.80:
        overall_score = max(overall_score, 0.60)
    elif required_score_raw >= 0.60:
        overall_score = max(overall_score, 0.54)
    elif required_score_raw >= 0.40:
        overall_score = max(overall_score, 0.46)

    # 2) Matched-skill count floor: candidate who legitimately matches several
    #    JD skills cannot score below a reasonable minimum even with missing keywords.
    if len(matched_skills) >= 7:
        overall_score = max(overall_score, 0.52)
    elif len(matched_skills) >= 4:
        overall_score = max(overall_score, 0.42)
    elif len(matched_skills) >= 2:
        overall_score = max(overall_score, 0.30)

    overall_score = max(0.0, min(overall_score, 1.0))
    overall_percent = round(overall_score * 100, 2)

    # Preserve raw_penalty for output (used by report)
    effective_penalty = required_penalty

    return {
        "required_skill_score": weighted_skill["required_skill_score"],
        "preferred_skill_score": weighted_skill["preferred_skill_score"],
        "general_skill_score": weighted_skill["general_skill_score"],
        "weighted_skill_score": weighted_skill["weighted_skill_score"],
        "semantic_score": round(semantic_score * 100, 2),
        "section_evidence_score": round(evidence_score * 100, 2),
        "skill_support_score": round(skill_support_score, 2),
        "critical_missing_penalty": round(raw_penalty * 100, 2),
        "overall_score": overall_percent,
        "fit_label": get_fit_label(overall_percent),
        # New recruiter-focused scores
        "career_progression_score": round(career_progression_score, 2),
        "achievements_score": round(achievements_score, 2),
        "industry_fit_score": round(industry_fit_score, 2),
    }
