from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _list(value: Any) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value]


def tiptap_to_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(part for part in (tiptap_to_text(item) for item in node) if part)
    if not isinstance(node, dict):
        return ""
    node_type = node.get("type")
    text = node.get("text")
    if text:
        return str(text)
    content = tiptap_to_text(node.get("content", []))
    if node_type in {"heading", "paragraph", "listItem"}:
        return content
    return content


@dataclass
class Company:
    id: str
    name: str
    image: str | None = None
    has_detail_info: bool | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Company":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            image=data.get("image"),
            has_detail_info=data.get("hasDetailInfo"),
        )


@dataclass
class JobSummary:
    id: str
    affiliate: str | None
    company: Company
    title: str
    created_at: str | None = None
    end_date: str | None = None
    deadline_type: str | None = None
    career_min: int | None = None
    career_max: int | None = None
    regions: list[str] = field(default_factory=list)
    employee_types: list[str] = field(default_factory=list)
    educations: list[str] = field(default_factory=list)
    depth_ones: list[str] = field(default_factory=list)
    depth_twos: list[str] = field(default_factory=list)
    depth_threes: list[str] = field(default_factory=list)
    views: int = 0
    bookmarked: bool = False
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    badges: list[Any] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "JobSummary":
        return cls(
            id=str(data["id"]),
            affiliate=data.get("affiliate"),
            company=Company.from_api(data.get("company") or {}),
            title=str(data.get("title") or ""),
            created_at=data.get("createdAt"),
            end_date=data.get("endDate"),
            deadline_type=data.get("deadlineType"),
            career_min=data.get("careerMin"),
            career_max=data.get("careerMax"),
            regions=_list(data.get("regions")),
            employee_types=_list(data.get("employeeTypes")),
            educations=_list(data.get("educations")),
            depth_ones=_list(data.get("depthOnes")),
            depth_twos=_list(data.get("depthTwos")),
            depth_threes=_list(data.get("depthThrees")),
            views=int(data.get("views") or 0),
            bookmarked=bool(data.get("bookmarked")),
            tags=_list(data.get("tags")),
            keywords=_list(data.get("keywords")),
            badges=list(data.get("badges") or []),
        )

    @property
    def source_url(self) -> str:
        return f"https://zighang.com/recruitment/{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_name": self.company.name,
            "title": self.title,
            "affiliate": self.affiliate,
            "jobs": self.depth_twos or self.depth_ones,
            "regions": self.regions,
            "career": {"min": self.career_min, "max": self.career_max},
            "deadline": {"type": self.deadline_type, "end_date": self.end_date},
            "employment_types": self.employee_types,
            "education_levels": self.educations,
            "keywords": self.keywords,
            "original_url": self.source_url,
            "summary": " / ".join(part for part in [self.company.name, self.title, ", ".join(self.regions)] if part),
        }


@dataclass
class JobDetail(JobSummary):
    summary_text: str = ""
    content_text: str = ""
    redirect_url: str | None = None
    status: str | None = None
    pinned: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "JobDetail":
        summary = JobSummary.from_api(data)
        return cls(
            **summary.__dict__,
            summary_text=tiptap_to_text(data.get("summary")),
            content_text=tiptap_to_text(data.get("content")),
            redirect_url=data.get("redirectUrl"),
            status=data.get("status"),
            pinned=bool(data.get("pinned")),
        )

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "detail": self.summary_text or self.content_text,
                "content": self.content_text,
                "redirect_url": self.redirect_url,
                "status": self.status,
                "pinned": self.pinned,
            }
        )
        return base


@dataclass
class PaginatedJobs:
    content: list[JobSummary]
    page: int
    size: int
    total_elements: int
    total_pages: int
    last: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "PaginatedJobs":
        return cls(
            content=[JobSummary.from_api(item) for item in data.get("content", [])],
            page=int(data.get("page") or 0),
            size=int(data.get("size") or 0),
            total_elements=int(data.get("totalElements") or 0),
            total_pages=int(data.get("totalPages") or 0),
            last=bool(data.get("last")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobs": [job.to_dict() for job in self.content],
            "page": self.page,
            "size": self.size,
            "total_elements": self.total_elements,
            "total_pages": self.total_pages,
            "last": self.last,
        }

