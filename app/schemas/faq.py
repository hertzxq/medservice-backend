"""FAQ Pydantic schemas."""

from pydantic import field_validator

from app.schemas.common import APIModel


def _non_empty(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field} must not be empty")
    return stripped


class FaqItemResponse(APIModel):
    id: int
    question: str
    answer: str
    sort_order: int


class FaqItemCreate(APIModel):
    question: str
    answer: str
    sort_order: int = 0

    @field_validator("question")
    @classmethod
    def _check_q(cls, v: str) -> str:
        out = _non_empty(v, field="question")
        assert out is not None
        return out

    @field_validator("answer")
    @classmethod
    def _check_a(cls, v: str) -> str:
        out = _non_empty(v, field="answer")
        assert out is not None
        return out


class FaqItemUpdate(APIModel):
    question: str | None = None
    answer: str | None = None
    sort_order: int | None = None

    @field_validator("question")
    @classmethod
    def _check_q(cls, v: str | None) -> str | None:
        return _non_empty(v, field="question")

    @field_validator("answer")
    @classmethod
    def _check_a(cls, v: str | None) -> str | None:
        return _non_empty(v, field="answer")
