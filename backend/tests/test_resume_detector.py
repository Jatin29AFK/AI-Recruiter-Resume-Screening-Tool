import unittest

from app.services.resume_detector import evaluate_resume_document


class ResumeDetectorTest(unittest.TestCase):
    def test_accepts_resume_like_text_even_without_perfect_sections(self):
        text = """
        Priya Sharma
        priyasharma@email.com | +91 9999999999

        Profile
        Backend engineer with 3 years of experience building APIs.

        Work
        Jan 2022 - Present: Built Python FastAPI services and MySQL pipelines.
        - Built REST APIs and improved response latency by 30%.
        - Worked with Docker, AWS, and CI/CD.

        Tools
        Python, FastAPI, SQL, Docker, AWS, Git
        """
        result = evaluate_resume_document(text=text, filename="priya.pdf")
        self.assertIn(result["final_label"], {"accept", "accept_with_warning"})
        self.assertGreater(result["positive_resume_score"], 0.2)

    def test_rejects_invoice_style_document(self):
        text = """
        INVOICE
        Bill To: ACME Corp
        GST: 29ABCDE1234F2Z5
        Subtotal: ₹12000
        Tax: ₹2160
        Total Amount: ₹14160
        Terms and Conditions apply.
        """
        result = evaluate_resume_document(text=text, filename="invoice.pdf")
        self.assertEqual(result["final_label"], "reject")
        self.assertTrue(result["hard_reject"])

    def test_rejects_hotel_booking_receipt(self):
        text = """
        Hotel Booking Confirmation
        Booking Reference: HB-482910
        Guest Name: Priya Sharma
        Hotel: Ocean View Residency, Goa
        Check-in: 12 Jun 2026
        Check-out: 15 Jun 2026
        Room Type: Deluxe King
        Nights: 3
        Fare: ₹18,000
        Taxes and fees: ₹2,160
        Total Amount: ₹20,160
        """
        result = evaluate_resume_document(text=text, filename="hotel-booking.pdf")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "travel_booking_match")

    def test_rejects_flight_booking_itinerary(self):
        text = """
        Flight Itinerary and E-ticket
        PNR: X7H2KL
        Passenger: Rahul Mehta
        Airline: Indigo
        Flight Number: 6E 203
        Departure: DEL - BOM, 21 May 2026, Terminal 2
        Arrival: Mumbai, Terminal 1
        Gate: B12
        Fare: ₹6,400
        Booking confirmation sent to passenger email.
        """
        result = evaluate_resume_document(text=text, filename="flight-ticket.pdf")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "travel_booking_match")

    def test_accepts_travel_industry_resume_with_booking_terms(self):
        text = """
        Aditi Rao
        aditi.rao@email.com | +91 9000000000

        Summary
        Travel operations specialist with 4 years of experience managing hotel
        booking workflows, flight itinerary changes, passenger support, and vendor escalations.

        Experience
        Jan 2021 - Present: Travel Desk Executive, Global Tours
        - Managed corporate booking confirmations and itinerary updates for 300+ monthly travelers.
        - Coordinated hotel reservation changes, airline fare checks, and passenger communication.

        Skills
        Vendor management, customer support, operations, Excel, CRM, reporting
        """
        result = evaluate_resume_document(text=text, filename="aditi-rao.pdf")
        self.assertIn(result["final_label"], {"accept", "accept_with_warning"})

    def test_rejects_installation_guide_document(self):
        text = """
        FreeCAD MCP Setup Guide
        Beginner-friendly installation and troubleshooting guide for Ubuntu.

        1. What this setup actually does
        This setup connects FreeCAD, the MCP addon, Claude Desktop, and uvx.

        2. Final folder structure
        /home/<your-username>/
        ~/.local/share/FreeCAD/v1-1/Mod/
        ~/.config/Claude/claude_desktop_config.json

        3. Prerequisites
        Ubuntu machine with terminal access.

        4. Step-by-step installation
        cd ~/Downloads
        chmod +x FreeCAD*.AppImage
        git clone https://github.com/example/freecad-mcp.git
        mkdir -p ~/.config/Claude
        nano ~/.config/Claude/claude_desktop_config.json

        5. Common issues and troubleshooting
        Restart the application after changing the config file.
        """
        result = evaluate_resume_document(text=text, filename="FreeCAD_MCP_Installation_Guide.pdf")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "installation_guide_match")

    def test_accepts_engineer_resume_with_installation_terms(self):
        text = """
        Neha Singh
        neha.singh@email.com | +91 9111111111

        Summary
        CAD automation engineer with 5 years of experience supporting FreeCAD,
        Python scripting, installation troubleshooting, and Linux workstation setup.

        Experience
        Mar 2020 - Present: CAD Automation Engineer, DesignWorks
        - Built Python macros for FreeCAD and automated model validation workflows.
        - Created internal setup guides for engineering tools and reduced onboarding time by 30%.
        - Troubleshot Ubuntu configuration issues across 80 engineering workstations.

        Skills
        Python, FreeCAD, Linux, Git, CAD automation, documentation
        """
        result = evaluate_resume_document(text=text, filename="neha-singh.pdf")
        self.assertIn(result["final_label"], {"accept", "accept_with_warning"})

    def test_rejects_ai_agent_learning_notes(self):
        text = """
        An Agent is an AI model capable of reasoning, planning, and interacting with its environment.
        What type of AI Models do we use for Agents?
        The most common AI model found in Agents is an LLM, which takes text as input and outputs text.
        How does an AI take action on its environment?
        LLMs can only generate text, but tools let them perform actions.
        Example 1: Personal Virtual Assistants
        Example 2: Customer Service Chatbots
        These examples demonstrate the core principles of an agent in action.
        """
        result = evaluate_resume_document(text=text, filename="HF AI Agent.docx")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "learning_notes_match")

    def test_rejects_langchain_learning_notes(self):
        text = """
        GenAI is a type of artificial intelligence that creates new content.
        Foundation model is the center of GenAI and requires huge amounts of data and GPUs.
        RAG lets us use our own documents and private data with an LLM.
        Let's start with user perspective, we will look to LangChain.
        LangChain is an open source framework that helps in building LLM based applications.
        Core features include integrations, question answering systems, semantic search, embeddings,
        vector DB storage, chunks, query processing, and chatbot workflows.
        """
        result = evaluate_resume_document(text=text, filename="Langchain 2.docx")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "learning_notes_match")

    def test_rejects_rag_learning_notes(self):
        text = """
        RAG, or Retrieval Augmented Generation, optimizes the output of a large language model.
        LLM hallucination happens when models produce plausible but incorrect information.
        Fine tuning is expensive, so vector DB retrieval can help answer questions from documents.
        The query is converted into embeddings, searched against chunks, and passed to the LLM.
        This course note explains chatbot architecture and question answering over private data.
        """
        result = evaluate_resume_document(text=text, filename="RAG_KRishNaik.docx")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "learning_notes_match")

    def test_rejects_hr_feedback_notes(self):
        text = """
        [4/24 10:34 AM] Christina Das
        Preliminary shortlisting pointers from Recruiter's POV:
        JD is the core, then the resume.
        First rejection is on non-negotiables.
        HR usually looks for relevance of past experience, matching technical skills,
        education fit, achievements, industry exposure, and career progression.
        For a scoring system:
        Must-have match - 40%
        Relevant experience - 20%
        Preferred skills - 15%
        Red flags, but not over filtering.
        The tool should answer: How well does this candidate match the job?
        [Wednesday 5:13 PM] Satheesh Babu
        Can we add option for review if the candidate holds any certificate?
        """
        result = evaluate_resume_document(text=text, filename="HR_Feedbacks.docx")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "feedback_document_match")

    def test_accepts_recruiter_resume_with_feedback_terms(self):
        text = """
        Riya Menon
        riya.menon@email.com | +91 9888888888

        Summary
        Technical recruiter with 6 years of experience building structured screening
        processes, candidate feedback loops, and interview scorecards.

        Experience
        Jan 2020 - Present: Senior Recruiter, TalentBridge
        - Designed must-have and preferred skills scorecards for engineering roles.
        - Improved human review workflows and reduced screening bias across hiring teams.
        - Partnered with hiring managers on red flags, positive signals, and candidate feedback.

        Skills
        Technical recruiting, stakeholder management, ATS, interview coordination, analytics
        """
        result = evaluate_resume_document(text=text, filename="riya-menon.pdf")
        self.assertIn(result["final_label"], {"accept", "accept_with_warning"})

    def test_rejects_code_heavy_document(self):
        text = """
        import os
        import json

        def build_app():
            data = {"name": "demo"}
            return data

        class Service:
            pass
        """
        result = evaluate_resume_document(text=text, filename="snippet.docx")
        self.assertEqual(result["final_label"], "reject")

    def test_rejects_too_short_text_in_layer_one(self):
        text = "Short text with no detail"
        result = evaluate_resume_document(text=text, filename="a.pdf")
        self.assertEqual(result["final_label"], "reject")
        self.assertFalse(result["layer_1_pass"])

    def test_rejects_student_evaluation_template(self):
        text = """
        Student Evaluation Template
        1. Student Information
        - Student Name : Shailendra Jangir
        - Roll Number : 2024PDE5041
        - Department : Mechanical Design
        - Date of Submission : 06-11-2025

        2. Problem Statement / Objectives
        A cast-aluminium bracket in a ceiling-mounted appliance cracks near the fillet radius under cyclic loading
        """
        result = evaluate_resume_document(text=text, filename="eval.pdf")
        self.assertEqual(result["final_label"], "reject")

    def test_rejects_simple_notes_file(self):
        text = """
        Notes:
        - Discuss project timeline
        - Action items: assign tasks to team
        - Next steps: finalize scope
        Date: 10-05-2025
        """
        result = evaluate_resume_document(text=text, filename="notes.pdf")
        self.assertEqual(result["final_label"], "reject")

    def test_rejects_agent_change_log_document(self):
        text = """
        Created 8 todos
        Read , lines 1 to 100
        Read , lines 100 to 300
        Starting: Design advanced evaluation architecture (2/8)
        Current system limitations identified:
        SYSTEM_PROMPT is 3 sentences
        dummy_score is purely length-based heuristics
        No confidence scoring, no student feedback, no analytics aggregation
        Starting: Create evaluation_engine.py module (3/3)
        Completed: Create evaluation_engine.py module (3/4)
        Now update app.py and replace the call_llm function
        Searched for text def call_llm
        Replacing 73 lines with 36 lines in app.py
        Ran terminal command: import ast; ast.parse(open('app.py').read())
        """
        result = evaluate_resume_document(text=text, filename="Evaluation_Agent_Changes.docx")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "agent_change_log_match")

    def test_rejects_evaluation_change_report_without_resume_structure(self):
        text = """
        Current system limitations identified:
        SYSTEM_PROMPT is 3 sentences — no semantic guidance
        dummy_score is purely length-based heuristics
        No confidence scoring, no student feedback, no analytics aggregation

        Step 1 — Analysis: Limitations of the Basic System
        Feature 1 — Semantic Evaluation
        The LLM evaluates whether the student understands the concept.
        Student evaluation, rubric, methodology, objective, course code, and assignment
        feedback are used to explain the grading workflow.
        The rubric YAML includes accepted approaches per criterion.
        The Excel export includes full reasoning and approach-detected columns.
        Improvement vs basic: the student gets fair credit.
        Trade-off: the LLM may occasionally be too generous.
        """
        result = evaluate_resume_document(text=text, filename="Evaluation_Agent_Changes.docx")
        self.assertEqual(result["final_label"], "reject")
        self.assertEqual(result["decision_reason"], "strong_form_template_match")


if __name__ == "__main__":
    unittest.main()
