# Backend Data Directory

This directory contains two kinds of JSON files:

- `jobs.json`
  - Seeded application data that should stay in source control.
- Runtime-generated files
  - `ingest_jobs.json`
  - `ingest_settings.json`
  - `recruiter_notes.json`
  - `candidate_statuses.json`
  - `visitor_count.json`

The runtime-generated files are intentionally gitignored because they contain
environment-specific state, demo activity, and recruiter interactions.

On a fresh setup, the backend recreates these files automatically when the
relevant features are used.
