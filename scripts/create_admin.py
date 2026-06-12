"""
Create (or update) the bootstrap superuser. SAFE FOR PRODUCTION.

Unlike seed.py this is NON-destructive: it touches only the one user row. Use it
to create the first admin on a fresh deployment (seed.py refuses to run when
ENVIRONMENT=production). A superuser bypasses branch scoping, so this account can
manage everything immediately.

Usage (inside the backend container or venv):

    ADMIN_USERNAME=admin ADMIN_EMAIL=admin@clinic.ru ADMIN_PASSWORD='<strong>' \
        python scripts/create_admin.py

    # or with flags, and reset an existing admin's password:
    python scripts/create_admin.py --username admin --email a@b.ru \
        --password '<strong>' --reset-password
"""

import argparse
import os
import sys
from pathlib import Path

# Allow running as `python scripts/create_admin.py` from the backend root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importing app.* loads settings; in production the config guard requires a real
# SECRET_KEY etc. — same requirements as running the API, which is intended.
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User

MIN_PASSWORD_LEN = 8


def main() -> int:
    ap = argparse.ArgumentParser(description="Create/update the bootstrap superuser.")
    ap.add_argument("--username", default=os.environ.get("ADMIN_USERNAME"))
    ap.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"))
    ap.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    ap.add_argument(
        "--reset-password",
        action="store_true",
        help="If the user already exists, reset their password to --password.",
    )
    args = ap.parse_args()

    if not (args.username and args.email and args.password):
        sys.exit(
            "Provide ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD "
            "(environment variables or --username/--email/--password flags)."
        )
    if len(args.password) < MIN_PASSWORD_LEN:
        sys.exit(f"ADMIN_PASSWORD must be at least {MIN_PASSWORD_LEN} characters.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == args.username).first()
        if user:
            user.is_superuser = True
            user.is_active = True
            if args.reset_password:
                user.hashed_password = get_password_hash(args.password)
            db.commit()
            note = " (password reset)" if args.reset_password else " (password unchanged)"
            print(f"[create_admin] Existing user '{args.username}' promoted to superuser{note}.")
        else:
            db.add(
                User(
                    username=args.username,
                    email=args.email,
                    hashed_password=get_password_hash(args.password),
                    full_name="Administrator",
                    is_active=True,
                    is_superuser=True,
                )
            )
            db.commit()
            print(f"[create_admin] Created superuser '{args.username}'.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
