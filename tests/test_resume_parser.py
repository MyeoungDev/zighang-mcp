import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from src.recommender.resume_parser import load_profile_from_paths, read_text_file


class FakePdfPage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class ResumeParserTests(unittest.TestCase):
    def test_read_text_file_reads_plain_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "resume.md"
            path.write_text("Java Spring Boot project", encoding="utf-8")

            self.assertEqual(read_text_file(path), "Java Spring Boot project")

    def test_read_text_file_extracts_pdf_text_with_pypdf(self):
        class FakePdfReader:
            def __init__(self, path):
                self.path = path
                self.pages = [
                    FakePdfPage("Java Spring Boot backend project"),
                    FakePdfPage("Kafka PostgreSQL 운영 경험"),
                ]

        fake_pypdf = types.SimpleNamespace(PdfReader=FakePdfReader)
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            path = Path(temp_dir) / "resume.pdf"
            path.write_bytes(b"%PDF-1.4 fake")

            text = read_text_file(path)

        self.assertIn("Java Spring Boot", text)
        self.assertIn("Kafka PostgreSQL", text)

    def test_read_text_file_rejects_scanned_pdf_without_text(self):
        class FakePdfReader:
            def __init__(self, path):
                self.pages = [FakePdfPage("   "), FakePdfPage(None)]

        fake_pypdf = types.SimpleNamespace(PdfReader=FakePdfReader)
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            path = Path(temp_dir) / "resume.pdf"
            path.write_bytes(b"%PDF-1.4 fake")

            with self.assertRaisesRegex(ValueError, "requires OCR"):
                read_text_file(path)

    def test_load_profile_from_paths_uses_pdf_text(self):
        class FakePdfReader:
            def __init__(self, path):
                self.pages = [FakePdfPage("Python Airflow data pipeline 프로젝트 개발")]

        fake_pypdf = types.SimpleNamespace(PdfReader=FakePdfReader)
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            path = Path(temp_dir) / "resume.pdf"
            path.write_bytes(b"%PDF-1.4 fake")

            profile = load_profile_from_paths(path)

        self.assertIn("Python", profile["skills"])
        self.assertIn("Airflow", profile["skills"])
        self.assertTrue(profile["projects"])

    def test_read_text_file_extracts_html_text_without_scripts_or_styles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "portfolio.html"
            path.write_text(
                """
                <html>
                  <head><style>.hidden { color: red; }</style></head>
                  <body>
                    <h1>React TypeScript 포트폴리오</h1>
                    <script>const secret = "Kafka";</script>
                    <p>고객 관리 프로젝트 개발</p>
                    <ul><li>Spring Boot API 연동</li></ul>
                  </body>
                </html>
                """,
                encoding="utf-8",
            )

            text = read_text_file(path)

        self.assertIn("React TypeScript 포트폴리오", text)
        self.assertIn("고객 관리 프로젝트 개발", text)
        self.assertIn("Spring Boot API 연동", text)
        self.assertNotIn("secret", text)
        self.assertNotIn("hidden", text)

    def test_load_profile_from_paths_uses_html_portfolio_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resume_path = Path(temp_dir) / "resume.md"
            portfolio_path = Path(temp_dir) / "portfolio.html"
            resume_path.write_text("Backend engineer", encoding="utf-8")
            portfolio_path.write_text("<h1>React TypeScript 프로젝트 개발</h1>", encoding="utf-8")

            profile = load_profile_from_paths(resume_path, portfolio_path)

        self.assertIn("React", profile["skills"])
        self.assertIn("TypeScript", profile["skills"])
        self.assertTrue(profile["projects"])


if __name__ == "__main__":
    unittest.main()
