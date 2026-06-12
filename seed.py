"""
Seed script: полностью сбрасывает данные домена и наполняет базу
демо-данными для визуального тестирования всех трёх приложений
(backend API, admin frontend, patient mini-app).

⚠️  ДЕСТРУКТИВНО. Скрипт удаляет все строки из таблиц requests, complaints,
    reviews, employees, blacklist_users, branches и users. Используйте только
    в dev/staging.

Итог:
  - user  / 12345678  (is_superuser=False)  — вход в дашборд на /login
  - admin / 12345678  (is_superuser=True)   — вход в админку на /admin/login
  - 3 филиала с отзывами, жалобами, запросами, сотрудниками и площадками.
  - Запросы с известными токенами r{branch_id}001 / r{branch_id}002 для
    проверки потока mini-app (POST /public/requests/{token}/rating).
"""

import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.blacklist import BlacklistUser
from app.models.bonus import BonusCategory, BranchBonus, FaqItem, PartnerBonus
from app.models.branch import Branch
from app.models.complaint import Complaint
from app.models.employee import Employee
from app.models.request import Request, RequestStatusEnum
from app.models.review import PlatformEnum, Review
from app.models.user import User

DEFAULT_PASSWORD = "12345678"

random.seed(42)
NOW = datetime.utcnow()

ENABLED_PLATFORMS = [
    PlatformEnum.YANDEX_MAPS,
    PlatformEnum.GOOGLE_MAPS,
    PlatformEnum.TWO_GIS,
    PlatformEnum.PRODOCTOROV,
    PlatformEnum.NAPOPRAVKU,
]

DOCTORS = [
    "Иванова Мария Петровна",
    "Смирнов Алексей Викторович",
    "Кузнецова Ольга Сергеевна",
    "Попов Дмитрий Андреевич",
    "Васильева Екатерина Игоревна",
    "Соколов Михаил Юрьевич",
    "Морозова Анна Дмитриевна",
]

POSITIVE_SNIPPETS = [
    "Врач {doc} внимательно осмотрел, всё подробно объяснил. Очень довольны!",
    "Прекрасная клиника, {doc} — настоящий профессионал. Спасибо!",
    "Записались без очередей, {doc} подобрал отличное лечение.",
    "Чисто, вежливый персонал. {doc} ответила на все вопросы.",
    "Отличный сервис, рекомендую! Особенно доктор {doc}.",
    "Быстро и качественно. {doc} помогла решить проблему со зрением.",
]

NEUTRAL_SNIPPETS = [
    "В целом неплохо, но пришлось подождать приёма.",
    "Нормальная клиника, ничего особенного.",
    "Лечение помогло, но цены высоковаты.",
]

NEGATIVE_SNIPPETS = [
    "Долго ждал в очереди, врач торопился.",
    "Не понравилось отношение администратора на ресепшене.",
    "Назначили лишние процедуры, осталось ощущение навязывания.",
    "Записали не к тому специалисту, потерял время.",
]

CLIENT_NAMES = [
    "Александр", "Елена", "Сергей", "Наталья", "Игорь", "Татьяна",
    "Владимир", "Юлия", "Андрей", "Светлана", "Павел", "Ирина",
]


def platform_urls_for(slug: str) -> dict:
    return {
        "yandex_maps": f"https://yandex.ru/maps/org/{slug}",
        "google_maps": f"https://maps.google.com/?q={slug}",
        "2gis": f"https://2gis.ru/firm/{slug}",
        "prodoctorov": f"https://prodoctorov.ru/clinic/{slug}",
        "napopravku": f"https://napopravku.ru/clinic/{slug}",
    }


def random_phone() -> str:
    return "+7 (9" + str(random.randint(10, 99)) + ") " + \
        f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"


def seed_database() -> None:
    # Destructive + creates a known-password superuser — never run in production.
    if settings.environment == "production":
        raise SystemExit(
            "seed.py отказывается работать при ENVIRONMENT=production "
            "(деструктивно и создаёт админа с дефолтным паролем)."
        )

    db: Session = SessionLocal()
    try:
        print("[cleanup] Очистка таблиц домена...")
        for model in (
            PartnerBonus, FaqItem, BonusCategory, BranchBonus,
            Request, Complaint, Review, Employee, BlacklistUser, Branch, User,
        ):
            deleted = db.query(model).delete()
            print(f"  - {model.__tablename__}: удалено {deleted}")
        db.commit()

        # ── Users ────────────────────────────────────────────────────────────
        print("[seed] Пользователи...")
        hashed = get_password_hash(DEFAULT_PASSWORD)
        db.add_all([
            User(email="user@medservice.com", username="user", hashed_password=hashed,
                 full_name="Пользователь сервиса", role="Менеджер",
                 is_active=True, is_superuser=False),
            User(email="admin@medservice.com", username="admin", hashed_password=hashed,
                 full_name="Администратор", role="Руководитель",
                 is_active=True, is_superuser=True),
        ])
        db.commit()

        # ── Branches ─────────────────────────────────────────────────────────
        print("[seed] Филиалы...")
        branch_defs = [
            dict(name="Счастливый взгляд, Сенная ул. 10", city="Санкт-Петербург",
                 address="Сенная ул., 10", phone="+7 (812) 401-11-22",
                 specialization="Офтальмология", slug="schastlivyy-vzglyad-sennaya"),
            dict(name="Счастливый взгляд, Невский пр. 88", city="Санкт-Петербург",
                 address="Невский пр., 88", phone="+7 (812) 401-33-44",
                 specialization="Офтальмология", slug="schastlivyy-vzglyad-nevsky"),
            dict(name="Зоркий мир, Ленина 42", city="Москва",
                 address="ул. Ленина, 42", phone="+7 (495) 777-88-99",
                 specialization="Офтальмология", slug="zorkiy-mir-lenina"),
        ]
        branches: list[Branch] = []
        for d in branch_defs:
            b = Branch(
                name=d["name"], city=d["city"], address=d["address"], phone=d["phone"],
                timezone="Московское время - UTC +3", specialization=d["specialization"],
                request_frequency_days=14,
                complaint_emails=["director@medservice.com"],
                reminder_emails=["manager@medservice.com"],
                platform_urls=platform_urls_for(d["slug"]),
                is_active=True,
                paid_until=(NOW + timedelta(days=180)).date(),
            )
            db.add(b)
            branches.append(b)
        db.commit()
        for b in branches:
            db.refresh(b)

        # Grant the demo non-superuser access to every branch (multi-tenancy).
        # The superuser bypasses this; a real deployment would assign branches
        # per user, but for the demo `user` should see everything.
        demo_user = db.query(User).filter(User.username == "user").first()
        if demo_user:
            demo_user.branches = list(branches)
            db.commit()

        # ── Employees ────────────────────────────────────────────────────────
        print("[seed] Сотрудники...")
        for b in branches:
            for i, name in enumerate(random.sample(DOCTORS, k=4)):
                db.add(Employee(
                    branch_id=b.id, name=name, active=(i != 3),
                    profiles=[f"https://prodoctorov.ru/doctor/{i}-{b.id}"],
                ))
        db.commit()

        # ── Bonus catalog ────────────────────────────────────────────────────
        # Real DB rows (ported from the former hardcoded demo in public.py).
        print("[seed] Бонусы клиник...")
        today = NOW.date()
        end_90 = (NOW + timedelta(days=90)).date()
        end_120 = (NOW + timedelta(days=120)).date()
        for b in branches:
            db.add_all([
                BranchBonus(
                    branch_id=b.id, is_published=True, discount_percent=20,
                    description="Скидка 20% на повторный приём офтальмолога в течение месяца после визита.",
                    start_date=today, end_date=end_90, promo_code="ZRENIE20", sort_order=1,
                ),
                BranchBonus(
                    branch_id=b.id, is_published=True, discount_percent=15,
                    description="−15% на комплексную диагностику зрения по предъявлению купона.",
                    start_date=today, end_date=end_90, promo_code=None, sort_order=2,
                ),
            ])

        print("[seed] Партнёрские категории и бонусы...")
        catalog = [
            ("Оптика и аксессуары", 1, [
                ("Очкарик", 10, "Скидка 10% на оправы и солнцезащитные очки.", "OPT10", "https://ochkarik.ru"),
                ("Линзомат", 15, "−15% на контактные линзы и растворы.", None, "https://linzomat.ru"),
            ]),
            ("Здоровье и красота", 2, [
                ("Аптека Здоровье", 7, "Скидка 7% на витамины для глаз.", "ZDOROVIE7", "https://apteka-zdorovie.ru"),
                ("СПА-центр Релакс", 20, "−20% на программу «Отдых для глаз».", "RELAX20", "https://spa-relax.ru"),
            ]),
            ("Кафе и отдых", 3, [
                ("Кофейня Bean", 12, "Скидка 12% на кофе и десерты.", "BEAN12", "https://bean-coffee.ru"),
            ]),
        ]
        for cat_name, cat_order, partners in catalog:
            cat = BonusCategory(name=cat_name, sort_order=cat_order, is_published=True)
            db.add(cat)
            db.flush()
            for i, (company, pct, desc, promo, site) in enumerate(partners, start=1):
                db.add(PartnerBonus(
                    category_id=cat.id, is_published=True, company_name=company,
                    logo_url=None, city="Санкт-Петербург", discount_percent=pct,
                    description=desc, start_date=today, end_date=end_120,
                    promo_code=promo, website_url=site, sort_order=i,
                ))

        print("[seed] FAQ...")
        db.add_all([
            FaqItem(sort_order=1, is_published=True,
                    question="Как воспользоваться бонусом?",
                    answer="Покажите промокод или этот экран на кассе партнёра — скидка применится автоматически."),
            FaqItem(sort_order=2, is_published=True,
                    question="Действует ли скидка на повторный приём?",
                    answer="Да, скидка на повторный приём действует в течение месяца после первого визита."),
            FaqItem(sort_order=3, is_published=True,
                    question="Можно ли совмещать несколько бонусов?",
                    answer="Бонусы клиники и партнёров не суммируются между собой, но вы можете использовать их по очереди."),
        ])
        db.commit()

        # ── Reviews + per-branch metrics ─────────────────────────────────────
        print("[seed] Отзывы...")
        rating_pool = [5, 5, 5, 5, 5, 4, 4, 4, 4, 3, 3, 2, 1]
        reviews_by_branch: dict[int, list[Review]] = {b.id: [] for b in branches}
        for b in branches:
            n_reviews = random.randint(38, 52)
            for _ in range(n_reviews):
                rating = random.choice(rating_pool)
                doc = random.choice(DOCTORS)
                if rating >= 4:
                    text = random.choice(POSITIVE_SNIPPETS).format(doc=doc)
                elif rating == 3:
                    text = random.choice(NEUTRAL_SNIPPETS)
                else:
                    text = random.choice(NEGATIVE_SNIPPETS)
                published = NOW - timedelta(
                    days=random.randint(0, 89), hours=random.randint(0, 23)
                )
                r = Review(
                    branch_id=b.id,
                    reviewer_name=random.choice(CLIENT_NAMES),
                    reviewer_phone=random_phone(),
                    rating=rating,
                    text=text,
                    platform=random.choice(ENABLED_PLATFORMS),
                    response_text="Спасибо за ваш отзыв!" if rating >= 4 and random.random() < 0.4 else None,
                    external_url=f"https://yandex.ru/maps/review/{b.id}/{random.randint(1000, 9999)}",
                    published_at=published,
                )
                db.add(r)
                reviews_by_branch[b.id].append(r)
            # cached metrics
            ratings = [r.rating for r in reviews_by_branch[b.id]]
            avg = round(sum(ratings) / len(ratings), 2)
            promoters = sum(1 for x in ratings if x == 5)
            detractors = sum(1 for x in ratings if x <= 3)
            b.avg_rating = avg
            b.nps_score = int(round((promoters - detractors) / len(ratings) * 100))
        db.commit()
        for b in branches:
            for r in reviews_by_branch[b.id]:
                db.refresh(r)

        # ── Complaints ───────────────────────────────────────────────────────
        print("[seed] Жалобы...")
        complaints_by_branch: dict[int, list[Complaint]] = {b.id: [] for b in branches}
        for b in branches:
            for _ in range(random.randint(5, 9)):
                rating = random.choice([1, 2, 3])
                c = Complaint(
                    branch_id=b.id,
                    client_name=random.choice(CLIENT_NAMES),
                    client_phone=random_phone(),
                    client_email=None,
                    rating=rating,
                    text=random.choice(NEGATIVE_SNIPPETS),
                    intercepted=True,
                    resolved=random.random() < 0.5,
                    created_at=NOW - timedelta(days=random.randint(0, 55)),
                )
                db.add(c)
                complaints_by_branch[b.id].append(c)
        db.commit()
        for b in branches:
            for c in complaints_by_branch[b.id]:
                db.refresh(c)

        # ── Blacklist ────────────────────────────────────────────────────────
        print("[seed] Чёрный список...")
        for b in branches:
            db.add(BlacklistUser(
                branch_id=b.id, last_name="Спамов", first_name="Спам",
                phone="+7 (900) 000-00-00", reason="Оставляет фейковые отзывы",
            ))
        db.commit()

        # ── Requests ─────────────────────────────────────────────────────────
        print("[seed] Запросы...")
        statuses = [
            RequestStatusEnum.SENT, RequestStatusEnum.OPENED, RequestStatusEnum.RATED,
            RequestStatusEnum.VISITED, RequestStatusEnum.PUBLISHED, RequestStatusEnum.COMPLAINT,
        ]
        demo_tokens: list[tuple[int, str]] = []
        for b in branches:
            # Two SENT requests for the mini-flow demo. Tokens are full-entropy
            # uuid4 hex (not guessable) — printed at the end so you can open the
            # demo link manually; never ship predictable r{branch}00{n} tokens.
            for n in (1, 2):
                sent = NOW - timedelta(days=n, hours=2)
                token = uuid.uuid4().hex
                demo_tokens.append((b.id, token))
                db.add(Request(
                    branch_id=b.id,
                    client_name=random.choice(CLIENT_NAMES),
                    client_phone=random_phone(),
                    status=RequestStatusEnum.SENT,
                    request_link=token,
                    sent_at=sent,
                ))

            for _ in range(random.randint(18, 26)):
                status = random.choice(statuses)
                sent = NOW - timedelta(days=random.randint(0, 40), hours=random.randint(0, 23))
                opened = sent + timedelta(hours=random.randint(1, 12)) if status != RequestStatusEnum.SENT else None
                rated = (opened + timedelta(hours=random.randint(1, 6))) if status in (
                    RequestStatusEnum.RATED, RequestStatusEnum.VISITED,
                    RequestStatusEnum.PUBLISHED, RequestStatusEnum.COMPLAINT,
                ) and opened else None
                published = None
                review_id = None
                complaint_id = None
                if status == RequestStatusEnum.PUBLISHED:
                    published = (rated or sent) + timedelta(hours=random.randint(1, 24))
                    review_id = random.choice(reviews_by_branch[b.id]).id
                elif status == RequestStatusEnum.COMPLAINT and complaints_by_branch[b.id]:
                    complaint_id = random.choice(complaints_by_branch[b.id]).id

                db.add(Request(
                    branch_id=b.id,
                    client_name=random.choice(CLIENT_NAMES),
                    client_phone=random_phone(),
                    status=status,
                    request_link=uuid.uuid4().hex,
                    sent_at=sent,
                    opened_at=opened,
                    rated_at=rated,
                    published_at=published,
                    review_id=review_id,
                    complaint_id=complaint_id,
                ))
        db.commit()

        # ── Summary ──────────────────────────────────────────────────────────
        print("\n[done] Демо-данные созданы:")
        print(f"   Филиалы   : {db.query(Branch).count()}")
        print(f"   Отзывы    : {db.query(Review).count()}")
        print(f"   Жалобы    : {db.query(Complaint).count()}")
        print(f"   Запросы   : {db.query(Request).count()}")
        print(f"   Сотрудники: {db.query(Employee).count()}")
        print(f"   Бонусы клиник : {db.query(BranchBonus).count()}")
        print(f"   Категории     : {db.query(BonusCategory).count()}")
        print(f"   Партн. бонусы : {db.query(PartnerBonus).count()}")
        print(f"   FAQ           : {db.query(FaqItem).count()}")
        print("\n   Учётки:")
        print(f"     Dashboard   : user  / {DEFAULT_PASSWORD}")
        print(f"     Admin panel : admin / {DEFAULT_PASSWORD}")
        print("   Mini-токены для потока отзыва (SENT):")
        for branch_id, token in demo_tokens:
            print(f"     /r/{branch_id}/{token}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
