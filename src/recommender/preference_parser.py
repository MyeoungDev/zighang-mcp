from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from src.storage.db import DEFAULT_STATE


REGIONS = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "경남", "경북", "전남", "전북", "충남", "충북", "제주", "해외"]
EMPLOYMENT_TYPES = ["정규직", "계약직", "일용직", "프리랜서", "병역특례", "체험형인턴", "전환형인턴"]
INTERNSHIP_TERMS = ["인턴", "인턴십", "채용연계형", "체험형인턴", "전환형인턴"]

SUBCATEGORY_PATTERNS = [
    ("서버_백엔드", ["백엔드", "서버", "spring", "spring boot", "java", "kotlin"]),
    ("데이터엔지니어", ["데이터 엔지니어", "데이터엔지니어", "데이터 플랫폼", "데이터플랫폼", "데이터 파이프라인", "파이프라인", "etl", "airflow"]),
    ("DevOps_SRE", ["devops", "sre", "인프라", "클라우드", "kubernetes", "docker", "온프레미스", "온프렘"]),
    ("정보보호_보안", ["보안", "security", "정보보호"]),
    ("RAG", ["rag"]),
    ("LLM", ["llm", "생성형ai", "생성형 ai"]),
]

SKILL_TERMS = [
    "Spring Boot",
    "Spring",
    "Java",
    "Kotlin",
    "Python",
    "FastAPI",
    "Airflow",
    "Kafka",
    "Kubernetes",
    "Docker",
    "PostgreSQL",
    "MySQL",
    "RDBMS",
    "LLM",
    "RAG",
]

KEYWORD_TERMS = ["오픈소스", "데이터 플랫폼", "데이터 파이프라인", "온프레미스", "온프렘", "플랫폼", "마이크로서비스"]
EXCLUDABLE_TERMS = ["프론트엔드", "영업", "마케팅", "기획", "디자인", "QA", "인턴"]
NEGATION_HINTS = ["제외", "빼", "싫", "비선호", "원하지"]


def _contains(text_lower: str, term: str) -> bool:
    return term.lower() in text_lower


def _append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def _merge_list(base: list[Any], additions: list[Any]) -> list[Any]:
    merged = list(base)
    for item in additions:
        _append_unique(merged, item)
    return sorted(merged, key=str)


def _is_negated_near(text_lower: str, term: str) -> bool:
    for match in re.finditer(re.escape(term.lower()), text_lower):
        window = text_lower[match.start() : match.end() + 16]
        if any(hint in window for hint in NEGATION_HINTS):
            return True
    return False


def infer_preferences_from_text(text: str) -> dict[str, Any]:
    """Infer local user preference fields from Korean/English preference text."""
    normalized = re.sub(r"\s+", " ", text.strip())
    text_lower = normalized.lower()
    extracted = deepcopy(DEFAULT_STATE["user_preferences"])
    unmatched_terms: list[str] = []

    for subcategory, patterns in SUBCATEGORY_PATTERNS:
        if any(_contains(text_lower, pattern) for pattern in patterns):
            _append_unique(extracted["preferred_job_categories"], "IT_개발")
            _append_unique(extracted["preferred_job_subcategories"], subcategory)

    for region in REGIONS:
        if region in normalized:
            _append_unique(extracted["preferred_regions"], region)

    for employment_type in EMPLOYMENT_TYPES:
        if employment_type in normalized:
            _append_unique(extracted["preferred_employment_types"], employment_type)
    if "인턴" in normalized and not _is_negated_near(text_lower, "인턴"):
        _append_unique(extracted["preferred_employment_types"], "체험형인턴")
        _append_unique(extracted["preferred_employment_types"], "전환형인턴")

    for term in INTERNSHIP_TERMS:
        if _contains(text_lower, term) and _is_negated_near(text_lower, term):
            extracted["default_exclude_internships"] = True
            for internship_term in INTERNSHIP_TERMS:
                _append_unique(extracted["excluded_keywords"], internship_term)

    for term in EXCLUDABLE_TERMS:
        if _contains(text_lower, term) and _is_negated_near(text_lower, term):
            _append_unique(extracted["excluded_keywords"], term)
            _append_unique(extracted["disliked_keywords"], term)

    for skill in SKILL_TERMS:
        if _contains(text_lower, skill):
            _append_unique(extracted["preferred_skills"], skill)

    for keyword in KEYWORD_TERMS:
        if _contains(text_lower, keyword):
            _append_unique(extracted["preferred_keywords"], keyword)

    if "정규직" not in extracted["preferred_employment_types"] and any(term in normalized for term in ["정규", "풀타임"]):
        _append_unique(extracted["preferred_employment_types"], "정규직")

    meaningful_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#._-]{1,}|[가-힣]{2,}", normalized)
    known_text = " ".join(
        [*REGIONS, *EMPLOYMENT_TYPES, *INTERNSHIP_TERMS, *KEYWORD_TERMS, *EXCLUDABLE_TERMS, *SKILL_TERMS]
        + [pattern for _, patterns in SUBCATEGORY_PATTERNS for pattern in patterns]
        + NEGATION_HINTS
        + ["위주", "선호", "좋아", "경험", "공고", "직무", "개발", "쪽도", "살릴", "있는"]
    ).lower()
    for token in meaningful_tokens:
        if token.lower() not in known_text and len(unmatched_terms) < 10:
            _append_unique(unmatched_terms, token)

    return {"extracted": extracted, "unmatched_terms": unmatched_terms}


def merge_preferences(current: dict[str, Any] | None, extracted: dict[str, Any], merge: bool = True) -> dict[str, Any]:
    base = deepcopy(current if merge and current is not None else DEFAULT_STATE["user_preferences"])
    for key, value in extracted.items():
        if isinstance(value, list):
            base[key] = _merge_list(list(base.get(key) or []), value)
        elif value is not None:
            base[key] = value
    return base
