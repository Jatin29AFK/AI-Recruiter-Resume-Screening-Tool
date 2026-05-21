import unittest
from pathlib import Path

from app.services.career_analyzer import (
    analyze_timeline_gaps,
    check_education_fit,
    detect_red_flags,
)
from app.services.analyzer import analyze_resume_text_against_jd
from app.services.extractor import extract_skills_from_text
from app.services.experience_estimator import (
    estimate_total_experience_years,
    extract_professional_experience_ranges,
)
from app.services.jd_parser import parse_jd_requirements
from app.services.parser import extract_resume_text, is_likely_resume_text
from app.services.section_parser import split_resume_into_sections


ROOT = Path(__file__).resolve().parents[2]


class ExperienceExtractionRegressionTest(unittest.TestCase):
    def _sections_for_sample(self, filename: str) -> tuple[str, dict[str, str]]:
        path = ROOT / "sample-resumes" / filename
        text = extract_resume_text(str(path), filename)
        return text, split_resume_into_sections(text)

    def _sections_for_sample_path(self, relative_path: str) -> tuple[str, dict[str, str]]:
        path = ROOT / relative_path
        text = extract_resume_text(str(path), path.name)
        return text, split_resume_into_sections(text)

    def _load_backend_havells_jd(self) -> str:
        import json

        jobs = json.loads((ROOT / "backend" / "data" / "jobs.json").read_text())
        return jobs["c60616ed-3b08-4ac3-bc0e-d4096e66e643"]["description"]

    def test_vinitha_project_and_education_dates_do_not_create_job_hopping(self):
        text, sections = self._sections_for_sample("VINITHAK.pdf")
        experience = sections.get("experience", "")
        education = sections.get("education", "")

        ranges = extract_professional_experience_ranges(experience)
        timeline = analyze_timeline_gaps(experience, education)
        estimate = estimate_total_experience_years(
            experience,
            full_resume_text=text,
            summary_text=sections.get("summary", ""),
        )
        flags = detect_red_flags(text, [], experience, education)

        self.assertEqual(1, len(ranges))
        self.assertEqual([], timeline["short_tenure_flags"])
        self.assertEqual([], timeline["gaps"])
        self.assertEqual([], flags)
        self.assertIn(estimate["source"], {"summary", "explicit_resume_text"})

    def test_vinitha_pdf_sections_are_recovered_from_visual_text_order(self):
        _, sections = self._sections_for_sample("VINITHAK.pdf")

        self.assertIn("over 2 years of experience", sections.get("summary", "").lower())
        self.assertIn("AI ML Engineer, Tata Elxsi", sections.get("experience", ""))
        self.assertIn("Cochin University", sections.get("education", ""))
        self.assertIn("Computer vision master class", sections.get("certifications", ""))
        self.assertIn("Vehicle parked on Bus stop detection", sections.get("projects", ""))
        self.assertGreaterEqual(len(sections.get("projects", "")), 1000)

    def test_sachin_contiguous_same_company_roles_are_not_job_hopping(self):
        text, sections = self._sections_for_sample("SACHINSONI.pdf")
        experience = sections.get("experience", "")
        education = sections.get("education", "")

        ranges = extract_professional_experience_ranges(experience)
        timeline = analyze_timeline_gaps(experience, education)
        flags = detect_red_flags(text, [], experience, education)

        self.assertEqual(3, len(ranges))
        self.assertEqual(1, len(timeline["tenures"]))
        self.assertEqual([], timeline["short_tenure_flags"])
        self.assertEqual([], timeline["gaps"])
        self.assertEqual([], flags)

    def test_sachin_education_section_is_parsed(self):
        _, sections = self._sections_for_sample("SACHINSONI.pdf")

        education = sections.get("education", "")
        self.assertIn("National Institute of Technology", education)
        self.assertIn("Master of Computer Applications", education)
        self.assertIn("Harish Chandra", education)
        self.assertIn("BSc Maths", education)

    def test_sachin_education_matches_common_jd_degree_phrasing(self):
        _, sections = self._sections_for_sample("SACHINSONI.pdf")

        for requirements in [
            ["Bachelors"],
            ["Bachelor degree"],
            ["degree"],
            ["Computer Science"],
            ["MCA"],
            ["BE/B.Tech/MCA"],
            ["B.Tech/M.Tech/BCA/MCA"],
            ["Bachelor degree in Computer Science"],
        ]:
            with self.subTest(requirements=requirements):
                result = check_education_fit(sections, requirements)
                self.assertIs(result["meets_requirement"], True)

    def test_sidebar_style_resume_is_not_rejected_by_upload_guardrail(self):
        text, sections = self._sections_for_sample_path(
            "sample-resumes/Resume and JD/AML Rejected cvs/KhushbuParmar.pdf"
        )

        is_likely, warning = is_likely_resume_text(text)

        self.assertIs(is_likely, True, warning)
        self.assertIn("Master of Technology", sections.get("education", ""))
        self.assertIn("Data Scientist at Siemens", sections.get("experience", ""))
        self.assertIn("Deep Learning", sections.get("skills", ""))
        self.assertIn("Birds Audio Identification", sections.get("projects", ""))

    def test_khushbu_from_month_year_current_role_counts_in_experience(self):
        text, sections = self._sections_for_sample_path(
            "sample-resumes/Resume and JD/AML Rejected cvs/KhushbuParmar.pdf"
        )

        estimate = estimate_total_experience_years(
            sections.get("experience", ""),
            full_resume_text=text,
            summary_text=sections.get("summary", ""),
        )

        # Regression: resumes with "From Sep 2024" style current-role dates
        # used to miss the ongoing role and undercount tenure (~1.3-1.5y).
        self.assertEqual("experience_section", estimate["source"])
        self.assertGreaterEqual(estimate["estimated_years"], 3.0)
        self.assertGreaterEqual(estimate["estimated_months"], 36)

    def test_utkarsh_month_name_to_ranges_are_counted_as_full_experience(self):
        text, sections = self._sections_for_sample_path(
            "sample-resumes/Resume and JD/AML Rejected cvs/UtkarshPrakash.pdf"
        )
        experience = sections.get("experience", "")
        education = sections.get("education", "")

        ranges = extract_professional_experience_ranges(experience)
        timeline = analyze_timeline_gaps(experience, education)
        estimate = estimate_total_experience_years(
            experience,
            full_resume_text=text,
            summary_text=sections.get("summary", ""),
        )

        self.assertEqual(5, len(ranges))
        self.assertEqual(1, len(timeline["tenures"]))
        self.assertEqual([], timeline["short_tenure_flags"])
        self.assertEqual([], timeline["gaps"])
        self.assertEqual("experience_section", estimate["source"])
        self.assertGreaterEqual(estimate["estimated_years"], 6.0)

    def test_backend_havells_jd_keeps_nested_must_have_skills_required(self):
        jd_text = self._load_backend_havells_jd()

        info = parse_jd_requirements(jd_text, "backend")

        self.assertIn("python", info["required_skills"])
        self.assertIn("node.js", info["required_skills"])
        self.assertIn("typescript", info["required_skills"])
        self.assertIn("mongodb", info["required_skills"])
        self.assertIn("mysql", info["required_skills"])
        self.assertIn("spring boot", info["preferred_skills"])
        self.assertIn("go", info["preferred_skills"])
        self.assertIn("rust", info["preferred_skills"])
        self.assertIn(
            {"aws", "azure", "gcp"},
            [set(group) for group in info["required_skill_groups"]],
        )
        self.assertIn(
            {"mongodb", "mysql", "sql"},
            [set(group) for group in info["required_skill_groups"]],
        )

    def test_react_and_react_native_are_distinct_skills(self):
        react_native_skills = extract_skills_from_text(
            "Built production mobile apps using React Native and TypeScript.",
            "software_web",
        )
        react_web_skills = extract_skills_from_text(
            "Built production web apps using React and TypeScript.",
            "software_web",
        )

        self.assertIn("react native", react_native_skills)
        self.assertNotIn("react", react_native_skills)
        self.assertIn("react", react_web_skills)
        self.assertNotIn("react native", react_web_skills)

    def test_or_skill_group_scores_candidate_with_either_mobile_framework(self):
        jd_text = """
        Job Description
        Must have:
        Mobile app development experience with Flutter OR React Native
        """
        resume_text = """
        Asha Kumar
        asha@example.com | +91 9876543210

        Summary
        Mobile developer with 4 years of experience building production apps.

        Experience
        Jan 2021 - Present: Mobile Developer, AppWorks
        - Built Flutter applications with offline sync, push notifications, and REST API integrations.

        Skills
        Flutter, Dart, mobile app development, REST APIs, Git
        """

        info = parse_jd_requirements(jd_text, "software_web")
        result = analyze_resume_text_against_jd(
            resume_text,
            jd_text,
            filename="asha.pdf",
            include_llm_explanation=False,
        )

        self.assertIn(
            {"flutter", "react native"},
            [set(group) for group in info["required_skill_groups"]],
        )
        self.assertEqual(result["scores"]["required_skill_score"], 100.0)
        self.assertEqual(result["critical_missing_skills"], [])
        self.assertIn("flutter", result["matched_skills"])
        self.assertNotIn("react native", result["missing_skills"])

    def test_backend_havells_scoring_rewards_evidence_when_must_haves_are_equal(self):
        jd_text = self._load_backend_havells_jd()
        sufaid_text, _ = self._sections_for_sample_path(
            "sample-resumes/Resume and JD/Backend Rejected cvs/SufaidPP.pdf"
        )
        vijay_text, _ = self._sections_for_sample_path(
            "sample-resumes/Resume and JD/Backend selected cvs/VijayPrakash.pdf"
        )

        sufaid = analyze_resume_text_against_jd(
            sufaid_text,
            jd_text,
            filename="SufaidPP.pdf",
            include_llm_explanation=False,
        )
        vijay = analyze_resume_text_against_jd(
            vijay_text,
            jd_text,
            filename="VijayPrakash.pdf",
            include_llm_explanation=False,
        )

        self.assertEqual(vijay["scores"]["required_skill_score"], 100.0)
        self.assertEqual(sufaid["scores"]["required_skill_score"], 100.0)
        self.assertGreater(
            vijay["scores"]["skill_support_score"],
            sufaid["scores"]["skill_support_score"],
        )
        self.assertGreater(
            vijay["scores"]["overall_score"],
            sufaid["scores"]["overall_score"],
        )


if __name__ == "__main__":
    unittest.main()
