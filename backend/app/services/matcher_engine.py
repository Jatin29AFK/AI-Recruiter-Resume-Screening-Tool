from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.services.extractor import normalize_skill


def exact_skill_match(resume_skills: list[str], jd_skills: list[str]) -> list[str]:
    resume_set = {normalize_skill(skill) for skill in resume_skills}
    jd_set = {normalize_skill(skill) for skill in jd_skills}
    return sorted(resume_set.intersection(jd_set))


def missing_skill_match(resume_skills: list[str], jd_skills: list[str]) -> list[str]:
    resume_set = {normalize_skill(skill) for skill in resume_skills}
    jd_set = {normalize_skill(skill) for skill in jd_skills}
    return sorted(jd_set - resume_set)


def fuzzy_skill_match(
    resume_skills: list[str],
    jd_skills: list[str],
    threshold: int = 85
) -> list[tuple[str, str, float]]:
    matches = []
    seen_pairs = set()

    normalized_resume = [normalize_skill(skill) for skill in resume_skills]
    normalized_jd = [normalize_skill(skill) for skill in jd_skills]

    for jd_skill in normalized_jd:
        for resume_skill in normalized_resume:
            score = fuzz.ratio(jd_skill, resume_skill)
            pair = tuple(sorted((jd_skill, resume_skill)))
            if score >= threshold and jd_skill != resume_skill and pair not in seen_pairs:
                matches.append((jd_skill, resume_skill, round(score, 2)))
                seen_pairs.add(pair)

    return matches


def semantic_text_similarity(resume_text: str, jd_text: str) -> float:
    """
    Bag-of-words cosine similarity.

    Why NOT TF-IDF on 2 documents: when there are only 2 documents, any term
    appearing in BOTH gets IDF = log(2/2) = 0 and is completely zeroed out.
    This makes every relevant shared keyword (the very terms that indicate match)
    invisible, collapsing all scores to 10-17%.

    CountVectorizer counts raw term frequencies, so shared domain vocabulary
    (e.g. "backend", "python", "api") contributes proportionally — giving
    40-60% similarity for genuinely matching pairs.
    """
    from sklearn.feature_extraction.text import CountVectorizer

    texts = [resume_text, jd_text]
    vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 1))
    try:
        matrix = vectorizer.fit_transform(texts)
        similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    except ValueError:
        similarity = 0.0
    return float(similarity)


def detect_critical_missing_skills(
    required_skills: list[str],
    missing_skills: list[str],
    required_skill_groups: list[list[str]] | None = None,
) -> list[str]:
    required_set = {normalize_skill(skill) for skill in required_skills}
    missing_set = {normalize_skill(skill) for skill in missing_skills}
    critical_missing = set(required_set.intersection(missing_set))

    group_sets = [
        {normalize_skill(skill) for skill in group if skill}
        for group in (required_skill_groups or [])
        if group
    ]
    grouped_skills = set().union(*group_sets) if group_sets else set()
    critical_missing -= grouped_skills

    for group in group_sets:
        if group and group.issubset(missing_set):
            preview = ", ".join(sorted(group)[:4])
            suffix = ", ..." if len(group) > 4 else ""
            critical_missing.add(
                f"at least one required skill from group ({preview}{suffix})"
            )

    return sorted(critical_missing)


def detect_preferred_missing_skills(
    preferred_skills: list[str],
    missing_skills: list[str]
) -> list[str]:
    preferred_set = {normalize_skill(skill) for skill in preferred_skills}
    missing_set = {normalize_skill(skill) for skill in missing_skills}
    return sorted(preferred_set.intersection(missing_set))
