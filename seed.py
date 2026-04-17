"""
Seed script for populating database with test data.
Создает admin пользователя, филиалы, отзывы, жалобы и запросы.
"""

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.branch import Branch
from app.models.review import Review, PlatformEnum
from app.models.request import Request, RequestStatusEnum


def seed_database():
    """Заполнить БД тестовыми данными."""
    db: Session = SessionLocal()

    print("🌱 Seeding database...")

    # 1. Создать admin пользователя
    # ❗ ВНИМАНИЕ: Смените пароль перед использованием в production!
    default_password = "12345678"
    admin = User(
        email="admin@medservice.com",
        username="admin",
        hashed_password=get_password_hash(default_password),
        full_name="Сергей П.",
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()
    print(f"✅ Admin user created (username: admin, password: {default_password})")
    print("⚠️  ОБЯЗАТЕЛЬНО смените пароль для production!")

    # 2. Создать 5 филиалов (как в frontend mock)
    branches_data = [
        {
            "name": "Счастливый взгляд, Лиговский просп., 52К",
            "city": "Санкт-Петербург",
            "avg_rating": 5.0,
            "nps_score": 80,
        },
        {
            "name": "Счастливый взгляд, Кирочная ул., 26",
            "city": "Санкт-Петербург",
            "avg_rating": 4.9,
            "nps_score": 70,
        },
        {
            "name": "Счастливый взгляд, 7-я линия Васильевского острова, 42",
            "city": "Санкт-Петербург",
            "avg_rating": 4.5,
            "nps_score": 60,
        },
    ]

    branches = []
    for data in branches_data:
        branch = Branch(**data)
        db.add(branch)
        branches.append(branch)

    db.commit()
    print(f"✅ Created {len(branches)} branches")

    # 3. Создать отзывы для каждого филиала (10-20 на филиал)
    platforms = [
        PlatformEnum.YANDEX_MAPS,
        PlatformEnum.GOOGLE_MAPS,
        PlatformEnum.TWO_GIS,
        PlatformEnum.PRODOCTOROV,
    ]

    for branch in branches:
        review_count = random.randint(10, 20)
        for i in range(review_count):
            # Рейтинг зависит от avg_rating филиала (только целые 2..5)
            if branch.avg_rating >= 4.5:
                rating = random.choice([4, 5])
            elif branch.avg_rating >= 3.5:
                rating = random.choice([3, 4, 5])
            elif branch.avg_rating >= 2.5:
                rating = random.choice([2, 3, 4])
            else:
                rating = random.choice([2, 3])

            review = Review(
                branch_id=branch.id,
                reviewer_name=f"Клиент {i + 1}",
                rating=rating,
                text=f"Тестовый отзыв #{i + 1} для {branch.name[:30]}...",
                platform=random.choice(platforms),
                published_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            )
            db.add(review)

    db.commit()
    print("✅ Created reviews")

    # 4. Создать запросы (20-30 на филиал)
    statuses = list(RequestStatusEnum)
    for branch in branches:
        request_count = random.randint(20, 30)
        for i in range(request_count):
            request = Request(
                branch_id=branch.id,
                client_name=f"Клиент {i + 1}",
                client_phone=f"+7 (9XX) XXX-XX-{i:02d}",
                status=random.choice(statuses),
                sent_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
            )
            db.add(request)

    db.commit()
    print("✅ Created requests")

    db.close()
    print("\n🎉 Database seeding completed!")
    print(f"👤 Login credentials: username=admin, password={default_password}")


if __name__ == "__main__":
    seed_database()
