"""
Pydantic schemas for analytics endpoints.
"""

from pydantic import BaseModel


class AnalyticsResponse(BaseModel):
    """
    Schema for single branch analytics.
    Endpoint: GET /api/v1/analytics/{branch_id}
    """

    sent: int  # Кол-во отправленных запросов
    reviews: int  # Новые отзывы
    complaints: int  # Жалобы
    avg_rating: float  # Средний рейтинг (0.0 - 5.0)


class BranchAnalyticsRow(BaseModel):
    """
    Schema for single row in branches analytics table.
    Endpoint: GET /api/v1/analytics/branches
    """

    id: int
    name: str
    requests: int  # Отправленные запросы
    new_reviews: int  # Новые отзывы
    intercepted_complaints: int  # Перехваченные жалобы
    avg_rating: float  # Средний рейтинг
    nps: int  # Net Promoter Score

    class Config:
        # Для совместимости с camelCase в frontend
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Счастливый взгляд, Сенная ул. 10",
                "requests": 40,
                "new_reviews": 7,
                "intercepted_complaints": 3,
                "avg_rating": 4.5,
                "nps": 60,
            }
        }


class BranchesAnalyticsResponse(BaseModel):
    """
    Schema for branches analytics response.
    Endpoint: GET /api/v1/analytics/branches
    """

    rows: list[BranchAnalyticsRow]
