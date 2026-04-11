"""
Unified Pydantic models for parsed review data.

These models act as the bridge between raw parser output
and the backend's SQLAlchemy Review model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ParsedReview(BaseModel):
    """A single review from any platform, normalised to a common shape."""

    author: str = Field(default="")
    rating: int = Field(ge=1, le=5, default=5)
    date: str = Field(default="")
    text: str = Field(default="")
    response: str | None = Field(default=None)
    # Prodoctorov-specific extra fields (merged into text when saving)
    pros: str | None = Field(default=None)
    cons: str | None = Field(default=None)


class ParsedBusiness(BaseModel):
    """Metadata about the business/organisation scraped from the page."""

    name: str = Field(default="")
    address: str = Field(default="")
    overall_rating: float | None = Field(default=None)
    total_reviews_on_page: int | None = Field(default=None)


class ParseResult(BaseModel):
    """Complete result of a single parse run."""

    business_info: ParsedBusiness
    reviews: list[ParsedReview]
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    total_parsed: int = Field(default=0)
    source_url: str = Field(default="")
    platform: str = Field(default="other")  # yandex_maps | google_maps | 2gis | prodoctorov
