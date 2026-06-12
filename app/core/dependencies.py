"""
FastAPI dependencies for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency для получения текущего пользователя из JWT token.

    Args:
        credentials: HTTP Bearer credentials (JWT token)
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: 401 if token is invalid or user not found
        HTTPException: 403 if user is inactive
    """
    from app.models.user import User  # Import here to avoid circular imports

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    return user


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Return the decoded JWT claims for the current request."""
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )
    return payload


async def get_current_superuser(
    current_user=Depends(get_current_user),
    payload: dict = Depends(get_token_payload),
):
    """
    FastAPI dependency для проверки прав суперпользователя.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current superuser

    Raises:
        HTTPException: 403 if user is not a superuser, or if this is an
            impersonation token (which must never reach privileged routes).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )
    # An impersonation token carries the TARGET user's `sub`; it must not be
    # usable to reach superuser routes (re-impersonate, manage users, etc.).
    if payload.get("typ") == "impersonation":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Действие недоступно в режиме просмотра аккаунта",
        )
    return current_user


def accessible_branch_ids(user) -> set[int] | None:
    """Branch ids `user` may access; ``None`` means ALL (superuser).

    Use the None sentinel to skip branch filtering for superusers entirely.
    """
    if user.is_superuser:
        return None
    return {b.id for b in user.branches}


def require_branch_access(branch_id: int, user, db=None) -> None:
    """Authorize `user` for `branch_id` (membership check), else raise 404.

    Multi-tenancy guard: superusers may touch any branch; a non-superuser may
    only touch branches assigned to them. For a non-member the response is 404
    (same as a missing branch) so branch-id existence isn't disclosed across
    tenants. Existence of the branch itself is the endpoint's concern (list
    endpoints return empty; detail endpoints 404) — this helper only authorizes.
    """
    if user.is_superuser:
        return

    if branch_id not in {b.id for b in user.branches}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Филиал не найден")
