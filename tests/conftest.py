import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# App settings are loaded on import, so env vars must exist first.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.main import app
from app.core.database import Base, get_db
from app.core.rate_limit import limiter
from app.core.security import get_password_hash

# Rate limiting is disabled during tests — many tests hit /auth/login via the
# auth_headers fixture, which would otherwise trip the 5/minute limit.
limiter.enabled = False
from app.models.branch import Branch
from app.models.complaint import Complaint
from app.models.request import Request, RequestStatusEnum
from app.models.review import PlatformEnum, Review
from app.models.user import User
from app.models.employee import Employee  # noqa: F401 — needed for table creation
from app.models.blacklist import BlacklistUser  # noqa: F401 — needed for table creation


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield test_engine
    test_engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_data(session) -> None:
    now = datetime.utcnow()

    admin = User(
        email="admin@medservice.com",
        username="admin",
        hashed_password=get_password_hash("password123"),
        full_name="Test Admin",
        is_active=True,
        is_superuser=True,
    )
    regular = User(
        email="user@medservice.com",
        username="user",
        hashed_password=get_password_hash("password123"),
        full_name="Regular User",
        is_active=True,
        is_superuser=False,
    )
    session.add_all([admin, regular])

    branch_1 = Branch(
        name="Счастливый взгляд, Сенная ул. 10",
        city="Санкт-Петербург",
        avg_rating=4.8,
        nps_score=65,
    )
    branch_2 = Branch(
        name="Счастливый взгляд, Невский пр. 12",
        city="Санкт-Петербург",
        avg_rating=4.2,
        nps_score=45,
    )
    session.add_all([branch_1, branch_2])
    session.flush()

    reviews = [
        Review(
            branch_id=branch_1.id,
            reviewer_name="Иван",
            rating=5,
            text="Отлично",
            platform=PlatformEnum.YANDEX_MAPS,
            published_at=now - timedelta(days=3),
        ),
        Review(
            branch_id=branch_1.id,
            reviewer_name="Мария",
            rating=3,
            text="Нормально",
            platform=PlatformEnum.GOOGLE_MAPS,
            published_at=now - timedelta(days=40),
        ),
        Review(
            branch_id=branch_2.id,
            reviewer_name="Олег",
            rating=4,
            text="Хорошо",
            platform=PlatformEnum.YANDEX_MAPS,
            published_at=now - timedelta(days=2),
        ),
    ]
    session.add_all(reviews)

    complaints = [
        Complaint(
            branch_id=branch_1.id,
            client_name="Петр",
            client_phone="+79990000001",
            rating=2,
            text="Долго ждал",
            intercepted=True,
            resolved=False,
            created_at=now - timedelta(days=4),
        ),
        Complaint(
            branch_id=branch_1.id,
            client_name="Анна",
            client_phone="+79990000002",
            rating=2,
            text="Плохой сервис",
            intercepted=True,
            resolved=True,
            created_at=now - timedelta(days=50),
        ),
        Complaint(
            branch_id=branch_2.id,
            client_name="Елена",
            client_phone="+79990000003",
            rating=3,
            text="Грубый персонал",
            intercepted=True,
            resolved=False,
            created_at=now - timedelta(days=1),
        ),
    ]
    session.add_all(complaints)

    requests = [
        Request(
            branch_id=branch_1.id,
            client_name="Клиент 1",
            client_phone="+79990000011",
            client_email="c1@example.com",
            status=RequestStatusEnum.SENT,
            request_link="https://example.com/r/1",
            sent_at=now - timedelta(days=2),
        ),
        Request(
            branch_id=branch_1.id,
            client_name="Клиент 2",
            client_phone="+79990000012",
            client_email="c2@example.com",
            status=RequestStatusEnum.OPENED,
            request_link="https://example.com/r/2",
            sent_at=now - timedelta(days=45),
        ),
        Request(
            branch_id=branch_2.id,
            client_name="Клиент 3",
            client_phone="+79990000013",
            client_email="c3@example.com",
            status=RequestStatusEnum.PUBLISHED,
            request_link="https://example.com/r/3",
            sent_at=now - timedelta(days=1),
        ),
    ]
    session.add_all(requests)

    session.commit()


@pytest.fixture()
def client(session_factory, engine):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    seed_session = session_factory()
    seed_data(seed_session)
    seed_session.close()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password123"},
    )
    assert response.status_code == 200

    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_auth_headers(client):
    """Токен обычного (не superuser) пользователя — для тестов 403."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "password123"},
    )
    assert response.status_code == 200

    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}
