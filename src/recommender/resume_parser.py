from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

KNOWN_SKILLS = [
    "Java",
    "Spring",
    "Spring Boot",
    "Kotlin",
    "Python",
    "Kafka",
    "Airflow",
    "Kubernetes",
    "Docker",
    "PostgreSQL",
    "MySQL",
    "Redis",
    "AWS",
    "GCP",
    "Azure",
    "React",
    "TypeScript",
    "LLM",
    "RAG",
    "MLOps",
    "Apache SeaTunnel",
    "Open Source",
]

PDF_MIN_EXTRACTED_CHARS = 20


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag.lower() in {"br", "p", "div", "section", "article", "header", "footer", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        lines = []
        for line in "".join(self._parts).splitlines():
            stripped = re.sub(r"\s+", " ", line).strip()
            if stripped:
                lines.append(stripped)
        return "\n".join(lines)


def _read_html_file(file_path: Path) -> str:
    parser = _TextHTMLParser()
    parser.feed(file_path.read_text(encoding="utf-8"))
    return parser.text()


def _read_pdf_file(file_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
        raise RuntimeError("PDF parsing requires pypdf. Install project dependencies with: pip install -e .") from exc

    reader = PdfReader(str(file_path))
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    compact_text = re.sub(r"\s+", "", text)
    if len(compact_text) < PDF_MIN_EXTRACTED_CHARS:
        raise ValueError(
            f"PDF text extraction produced too little text from {file_path}. "
            "This PDF may be scanned or image-based and requires OCR, which is not supported yet."
        )
    return text


def read_text_file(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    if file_path.suffix.lower() == ".pdf":
        return _read_pdf_file(file_path)
    if file_path.suffix.lower() in {".html", ".htm"}:
        return _read_html_file(file_path)
    return file_path.read_text(encoding="utf-8")


def extract_skills(text: str) -> list[str]:
    found = []
    for skill in KNOWN_SKILLS:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(skill)}(?![A-Za-z0-9])", re.IGNORECASE)
        if pattern.search(text):
            found.append(skill)
    return found


def extract_projects(text: str) -> list[str]:
    projects = []
    for line in text.splitlines():
        stripped = line.strip(" -#\t")
        if not stripped:
            continue
        if any(word in stripped.lower() for word in ["project", "프로젝트", "개발", "구축", "운영"]):
            projects.append(stripped)
    return projects[:20]


def analyze_text_profile(text: str, source: str = "inline") -> dict[str, Any]:
    return {
        "source": source,
        "text": text,
        "skills": extract_skills(text),
        "projects": extract_projects(text),
        "keywords": sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9+#.:-]{1,}|[가-힣]{2,}", text)))[:200],
    }


def load_profile_from_paths(resume_path: str | Path, portfolio_path: str | Path | None = None) -> dict[str, Any]:
    resume_text = read_text_file(resume_path)
    portfolio_text = read_text_file(portfolio_path) if portfolio_path else ""
    return analyze_text_profile("\n\n".join(part for part in [resume_text, portfolio_text] if part), source=str(resume_path))
