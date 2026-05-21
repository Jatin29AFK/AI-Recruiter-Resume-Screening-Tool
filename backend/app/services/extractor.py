import re
from app.utils.constants import DOMAIN_SKILL_PACKS, SKILL_CATEGORIES, SKILL_ALIASES


def get_domain_pack(domain_name: str | None):
    if domain_name and domain_name in DOMAIN_SKILL_PACKS:
        return DOMAIN_SKILL_PACKS[domain_name]

    return {
        "categories": SKILL_CATEGORIES,
        "aliases": SKILL_ALIASES,
    }


def get_all_skills(domain_name: str | None = None) -> list[str]:
    pack = get_domain_pack(domain_name)
    all_skills = []

    for category_skills in pack["categories"].values():
        all_skills.extend(category_skills)

    return sorted(set(all_skills))


def get_aliases(domain_name: str | None = None) -> dict:
    pack = get_domain_pack(domain_name)
    return pack["aliases"]


def normalize_skill(skill: str, domain_name: str | None = None) -> str:
    skill = skill.lower().strip()
    aliases = get_aliases(domain_name)
    return aliases.get(skill, skill)


def _build_skill_pattern(skill: str) -> str:
    normalized = skill.lower().strip()

    strict_special_patterns = {
        "c": r"(?<![a-z0-9+#.])c(?![a-z0-9+#.])",
        "r": r"(?<![a-z0-9+#.])r(?![a-z0-9+#.])",
        "go": r"(?<![a-z0-9+#.])go(?![a-z0-9+#.])",
        "java": r"\bjava\b(?!\s*-?\s*script\b)",
        "react": r"\breact\b(?!\s*-?\s*native\b)",
        "react native": r"\breact\s*-?\s*native\b",
        "c++": r"(?<![a-z0-9+#.])c\+\+(?![a-z0-9+#.])",
        "c#": r"(?<![a-z0-9+#.])c#(?![a-z0-9+#.])",
        ".net": r"(?<![a-z0-9+#.])\.net(?![a-z0-9+#.])",
        "node.js": r"(?<![a-z0-9+#.])node\.js(?![a-z0-9+#.])",
        "next.js": r"(?<![a-z0-9+#.])next\.js(?![a-z0-9+#.])",
        "vue.js": r"(?<![a-z0-9+#.])vue\.js(?![a-z0-9+#.])",
        "star-ccm+": r"(?<![a-z0-9+#.])star\-ccm\+(?![a-z0-9+#.])",
    }

    if normalized in strict_special_patterns:
        return strict_special_patterns[normalized]

    if " " in normalized:
        parts = [re.escape(part) for part in normalized.split()]
        joined_parts = r"\s+".join(parts)
        return rf"\b{joined_parts}\b"

    return rf"\b{re.escape(normalized)}\b"


def _contains_skill(text: str, skill: str) -> bool:
    pattern = _build_skill_pattern(skill)
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def extract_skills_from_text(text: str, domain_name: str | None = None) -> list[str]:
    text = (text or "").lower()
    found_skills = set()

    for skill in get_all_skills(domain_name):
        if _contains_skill(text, skill):
            found_skills.add(normalize_skill(skill, domain_name))

    for alias, canonical in get_aliases(domain_name).items():
        if _contains_skill(text, alias):
            found_skills.add(normalize_skill(canonical, domain_name))

    return sorted(found_skills)


def categorize_extracted_skills(skills: list[str], domain_name: str | None = None) -> dict:
    pack = get_domain_pack(domain_name)
    categorized = {category: [] for category in pack["categories"]}

    for skill in skills:
        normalized = normalize_skill(skill, domain_name)
        for category, category_skills in pack["categories"].items():
            normalized_category_skills = [normalize_skill(s, domain_name) for s in category_skills]
            if normalized in normalized_category_skills:
                categorized[category].append(normalized)

    for category in categorized:
        categorized[category] = sorted(set(categorized[category]))

    return categorized


def extract_skills_from_sections(sections: dict[str, str], domain_name: str | None = None) -> dict[str, list[str]]:
    section_skills = {}

    for section_name, section_text in sections.items():
        extracted = extract_skills_from_text(section_text, domain_name)
        section_skills[section_name] = extracted

    return section_skills
