import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.crud.user import CRUDUser
from app.models.url import URL
from app.models.user import User, UserRole
from app.schemas.auth import AdminUserResponse, UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get(
    "/stats",
    summary="Platform-wide aggregate stats",
    responses={403: {"description": "Admin access required"}},
)
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Returns total users, total links, and total clicks across the entire platform."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    result = await db.execute(
        select(func.count(URL.id), func.coalesce(func.sum(URL.clicks), 0))
    )
    total_links, total_clicks = result.one()
    logger.info(
        "admin.stats users=%s links=%s clicks=%s",
        total_users,
        total_links,
        total_clicks,
    )
    return {
        "total_users": total_users,
        "total_links": total_links,
        "total_clicks": int(total_clicks),
    }


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="List all users",
    responses={403: {"description": "Admin access required"}},
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Returns all registered users. **Admin only.**"""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    logger.info("admin.list_users count=%s", len(users))
    return users


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def set_user_role(
    user_id: int,
    role: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Set a user's role to `user` or `admin`. **Admin only.**"""
    if role not in (UserRole.USER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user' or 'admin'",
        )

    user = await CRUDUser.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.role = role
    await db.commit()
    await db.refresh(user)
    logger.info("admin.role_changed user_id=%s new_role=%s", user_id, role)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Permanently deletes a user and all their links (CASCADE). **Admin only.**"""
    user = await CRUDUser.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await db.delete(user)
    await db.commit()
    logger.info("admin.user_deleted user_id=%s", user_id)
