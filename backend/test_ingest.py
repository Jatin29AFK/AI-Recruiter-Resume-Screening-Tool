#!/usr/bin/env python3
"""
test_ingest.py
--------------
Quick test to verify email ingest endpoint is working.

Usage:
    python3 test_ingest.py <path-to-test-resume.pdf>

Requirements:
    - Backend server running (uvicorn app.main:app --reload)
    - INGEST_SECRET set in backend/.env
    - Test resume file (PDF or DOCX)
"""

import sys
import os
import requests
from pathlib import Path

__test__ = False

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000')
INGEST_SECRET = os.getenv('INGEST_SECRET', '')

def test_ingest(resume_path: str):
    """Test the /ingest/upload endpoint with a sample resume."""
    
    if not INGEST_SECRET:
        print("❌ Error: INGEST_SECRET environment variable not set")
        print("   Set it in backend/.env or export it:")
        print("   export INGEST_SECRET='your-secret'")
        return False
    
    resume_file = Path(resume_path)
    if not resume_file.exists():
        print(f"❌ Error: File not found: {resume_path}")
        return False
    
    if resume_file.suffix.lower() not in ['.pdf', '.docx']:
        print(f"❌ Error: Unsupported file type: {resume_file.suffix}")
        print("   Only PDF and DOCX are supported")
        return False
    
    print(f"📤 Testing ingest endpoint...")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   File: {resume_file.name}")
    print()
    
    try:
        with open(resume_file, 'rb') as f:
            response = requests.post(
                f'{BACKEND_URL}/ingest/upload',
                headers={'X-Ingest-Secret': INGEST_SECRET},
                files={'file': (resume_file.name, f, 'application/pdf' if resume_file.suffix == '.pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},
                data={
                    'recruiter_email': 'test@example.com',
                    'subject': 'Test Resume Submission',
                },
                timeout=30
            )
        
        print(f"📊 Response: HTTP {response.status_code}")
        print()
        
        if response.status_code == 401:
            print("❌ Authentication failed")
            print("   Check that INGEST_SECRET matches backend .env")
            return False
        
        if response.status_code == 503:
            print("❌ Ingest endpoint not configured")
            print("   Set INGEST_SECRET in backend/.env")
            return False
        
        result = response.json()
        
        if response.status_code == 200:
            print("✅ Success! Resume ingested")
            print(f"   Ingest ID: {result.get('ingest_id')}")
            print(f"   Filename: {result.get('filename')}")
            print(f"   Status: {result.get('status')}")
            if result.get('serve_id'):
                print(f"   Serve ID: {result.get('serve_id')}")
            if result.get('analysis'):
                score = result['analysis'].get('scores', {}).get('overall_score') or result['analysis'].get('overall_score')
                if score is not None:
                    print(f"   Overall Score: {score}")
            print()
            print("🎯 Test the UI:")
            print("   1. Open frontend in browser")
            print("   2. Click '📥 Email Intake' button")
            print("   3. You should see the uploaded resume in the table")
            return True
        
        elif response.status_code == 422:
            print("⚠️  Resume was rejected")
            print(f"   Reason: {result.get('rejection_reason', 'Unknown')}")
            print()
            print("   Common reasons:")
            print("   - File is not a resume (invoice, receipt, itinerary, etc.)")
            print("   - File is corrupted or unreadable")
            return False
        
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   {result}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed")
        print(f"   Is the backend running at {BACKEND_URL}?")
        print("   Start it with: uvicorn app.main:app --reload")
        return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_jobs():
    """Test the /ingest/jobs endpoint."""
    if not INGEST_SECRET:
        return
    
    print("📋 Testing list endpoint...")
    try:
        response = requests.get(
            f'{BACKEND_URL}/ingest/jobs?limit=5',
            headers={'X-Ingest-Secret': INGEST_SECRET},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"✅ List endpoint OK — {count} job(s) in history")
            if count > 0:
                print("   Most recent:")
                for job in data.get('jobs', [])[:3]:
                    print(f"   - {job.get('filename')} ({job.get('status')})")
        else:
            print(f"⚠️  List endpoint returned {response.status_code}")
    except Exception as e:
        print(f"⚠️  List test failed: {e}")
    print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_ingest.py <path-to-resume.pdf>")
        print()
        print("Example:")
        print("  python3 test_ingest.py sample-resumes/john_doe.pdf")
        sys.exit(1)
    
    resume_path = sys.argv[1]
    
    print("=" * 60)
    print("Email Ingest Endpoint Test")
    print("=" * 60)
    print()
    
    success = test_ingest(resume_path)
    print()
    test_list_jobs()
    
    sys.exit(0 if success else 1)
