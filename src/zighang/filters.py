from __future__ import annotations

SORT_OPTIONS = {
    "recommended": "ZIGHANG_SCORE",
    "latest": "LATEST",
    "views": "VIEWS",
    "deadline": "DEADLINE",
    "ZIGHANG_SCORE": "ZIGHANG_SCORE",
    "LATEST": "LATEST",
    "VIEWS": "VIEWS",
    "DEADLINE": "DEADLINE",
}

EMPLOYMENT_TYPES = [
    "체험형인턴",
    "전환형인턴",
    "정규직",
    "계약직",
    "일용직",
    "프리랜서",
    "병역특례",
]

REGIONS = [
    "서울",
    "경기",
    "인천",
    "부산",
    "대구",
    "광주",
    "대전",
    "울산",
    "세종",
    "강원",
    "경남",
    "경북",
    "전남",
    "전북",
    "충남",
    "충북",
    "제주",
    "해외",
]

EDUCATION_LEVELS = ["무관", "고졸", "전문대졸", "학사", "석사", "박사"]

COMPANY_TYPES = ["대기업", "유니콘", "스타트업", "중견기업", "중소기업", "공공기관", "외국계"]

DEADLINE_TYPES = ["마감일", "상시채용", "채용시마감"]

AFFILIATE_GROUPS = {
    "민간 플랫폼": ["V1", "원티드", "로켓펀치", "그룹바이", "랠릿"],
    "협회": [
        "아이원잡",
        "금융투자협회",
        "여신금융협회",
        "한국관세사회",
        "한국공인회계사회",
        "한국보험계리사회",
        "한국상담학회",
    ],
    "공공기관": [
        "고용24",
        "중소벤처기업진흥공단",
        "잡알리오",
        "나라일터",
        "농촌일자리플러스",
        "도농인력중개플랫폼",
        "클린아이",
        "아트모아",
        "복지넷",
        "병역일터",
    ],
}


def normalize_sort(sort: str | None) -> str:
    if not sort:
        return "ZIGHANG_SCORE"
    if sort not in SORT_OPTIONS:
        raise ValueError(f"Unsupported sort option: {sort}")
    return SORT_OPTIONS[sort]


def order_for_sort(sort_condition: str) -> str:
    return "ASC" if sort_condition == "DEADLINE" else "DESC"


def static_filter_options() -> dict:
    return {
        "employment_types": EMPLOYMENT_TYPES,
        "regions": REGIONS,
        "education_levels": EDUCATION_LEVELS,
        "company_types": COMPANY_TYPES,
        "deadline_types": DEADLINE_TYPES,
        "affiliates": AFFILIATE_GROUPS,
        "sort_options": SORT_OPTIONS,
        "tags": {"nekara_kube": "NEKARA_KUBE"},
        "career": {"min": 0, "max": 10, "open_ended_sentinel": 100},
    }

