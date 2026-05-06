def build_keyword_coverage_report(
    jd_requirements: dict,
    evidence_summary: dict,
    skill_evidence_map: dict,
    missing_skills: list[str],
) -> dict:
    strong = set(skill.lower() for skill in evidence_summary.get("strong_evidence_skills", []))
    medium = set(skill.lower() for skill in evidence_summary.get("medium_evidence_skills", []))
    weak = set(skill.lower() for skill in evidence_summary.get("weak_evidence_skills", []))
    missing = set(skill.lower() for skill in missing_skills)

    priority_rank = {
        "required": 3,
        "preferred": 2,
        "general": 1,
    }

    items_by_skill = {}

    def resolve_status(normalized: str) -> str:
        if normalized in missing:
            return "missing"
        if normalized in strong:
            return "strong"
        if normalized in medium:
            return "medium"
        if normalized in weak or normalized in skill_evidence_map:
            return "weak"
        return "missing"

    def add_items(skills: list[str], priority: str):
        for skill in skills:
            normalized = skill.lower()
            status = resolve_status(normalized)

            evidence_sections = []
            supporting_lines = []
            if normalized in skill_evidence_map:
                ev = skill_evidence_map[normalized]
                evidence_sections = ev.get("mentioned_in", [])
                supporting_lines = ev.get("supporting_lines", [])[:3]  # cap at 3 lines

            item = {
                "skill": skill,
                "priority": priority,
                "status": status,
                "evidence_sections": evidence_sections,
                "supporting_lines": supporting_lines,
            }

            if normalized not in items_by_skill:
                items_by_skill[normalized] = item
            else:
                existing = items_by_skill[normalized]
                if priority_rank[priority] > priority_rank[existing["priority"]]:
                    items_by_skill[normalized] = item

    add_items(jd_requirements.get("required_skills", []), "required")
    add_items(jd_requirements.get("preferred_skills", []), "preferred")
    add_items(jd_requirements.get("general_skills", []), "general")

    items = list(items_by_skill.values())

    items.sort(
        key=lambda x: (
            -priority_rank[x["priority"]],
            x["status"] != "missing",
            x["skill"].lower(),
        )
    )

    summary = {
        "strong_count": len([x for x in items if x["status"] == "strong"]),
        "medium_count": len([x for x in items if x["status"] == "medium"]),
        "weak_count": len([x for x in items if x["status"] == "weak"]),
        # Headline missing count should reflect only required/preferred tiers.
        "missing_count": len([
            x for x in items
            if x["status"] == "missing" and x["priority"] in ("required", "preferred")
        ]),
        "optional_missing_count": len([
            x for x in items
            if x["status"] == "missing" and x["priority"] == "general"
        ]),
    }

    return {
        "items": items,
        "summary": summary,
    }