import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import email_ingest


class EmailIngestTargetJobTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        base_path = Path(self.temp_dir.name)
        self.upload_dir = base_path / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = base_path / "ingest_jobs.json"
        self.settings_file = base_path / "ingest_settings.json"

        self.upload_patch = patch.object(email_ingest, "INGEST_UPLOAD_DIR", self.upload_dir)
        self.jobs_patch = patch.object(email_ingest, "INGEST_JOBS_FILE", self.jobs_file)
        self.settings_patch = patch.object(email_ingest, "INGEST_SETTINGS_FILE", self.settings_file)

        self.upload_patch.start()
        self.jobs_patch.start()
        self.settings_patch.start()

        self.addCleanup(self.upload_patch.stop)
        self.addCleanup(self.jobs_patch.stop)
        self.addCleanup(self.settings_patch.stop)

    def test_process_file_uses_active_job_for_imap_analysis(self):
        email_ingest.set_active_job_id("job-123")

        saved_job = SimpleNamespace(
            job_id="job-123",
            title="Backend Engineer",
            description="Need Python and FastAPI experience.",
        )

        with patch("app.services.parser.extract_resume_text", return_value="resume text"), \
             patch("app.services.resume_detector.evaluate_resume_document", return_value={"final_label": "accept"}), \
             patch("app.services.jd_guardrails.validate_job_description_input", return_value=saved_job.description), \
             patch("app.routes.jobs.load_job_by_id", return_value=saved_job), \
             patch(
                 "app.services.analyzer.analyze_resume_against_jd",
                 return_value={"filename": "resume.pdf", "scores": {"overall_score": 82}},
             ) as analyze_mock:
            result = email_ingest.process_file(
                file_bytes=b"fake pdf bytes",
                original_filename="resume.pdf",
                source="imap",
                recruiter_email="recruiter@example.com",
                metadata={"subject": "Candidate"},
            )

        self.assertEqual("analyzed", result["status"])
        self.assertEqual("job-123", result["job_id"])
        self.assertEqual(82, result["analysis"]["scores"]["overall_score"])
        analyze_mock.assert_called_once()

    def test_active_job_id_round_trips_from_settings_store(self):
        self.assertEqual("", email_ingest.get_active_job_id())

        email_ingest.set_active_job_id("job-789")

        self.assertEqual("job-789", email_ingest.get_active_job_id())


if __name__ == "__main__":
    unittest.main()