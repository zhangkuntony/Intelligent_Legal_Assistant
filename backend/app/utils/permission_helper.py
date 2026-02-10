"""
权限检查工具类
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.user import User
from ..models.permissions import Permission, RolePermission
from ..models.role import Role, UserRole


async def has_permission(user: User, permission_code: str, db: AsyncSession) -> bool:
    """
    检查用户是否有指定权限

    Args:
        user: 用户对象
        permission_code: 权限代码
        db: 数据库会话

    Returns:
        bool: 用户是否有该权限
    """
    # 超级管理员拥有所有权限
    if user.is_superuser:
        return True

    # 查询用户的角色和权限
    result = await db.execute(
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
        .where(Permission.code == permission_code)
    )

    return result.scalar_one_or_none() is not None


async def has_any_permission(user: User, permission_codes: list[str], db: AsyncSession) -> bool:
    """
    检查用户是否有任一指定权限

    Args:
        user: 用户对象
        permission_codes: 权限代码列表
        db: 数据库会话

    Returns:
        bool: 用户是否有任意一个权限
    """
    # 超级管理员拥有所有权限
    if user.is_superuser:
        return True

    # 查询用户的角色和权限
    result = await db.execute(
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
        .where(Permission.code.in_(permission_codes))
    )

    return result.scalar_one_or_none() is not None


async def has_all_permissions(user: User, permission_codes: list[str], db: AsyncSession) -> bool:
    """
    检查用户是否有所有指定权限

    Args:
        user: 用户对象
        permission_codes: 权限代码列表
        db: 数据库会话

    Returns:
        bool: 用户是否有所有权限
    """
    # 超级管理员拥有所有权限
    if user.is_superuser:
        return True

    # 查询用户的角色和权限
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
        .where(Permission.code.in_(permission_codes))
        .distinct()
    )

    user_permissions = {row[0] for row in result.all()}
    return all(perm in user_permissions for perm in permission_codes)


async def get_user_permissions(user: User, db: AsyncSession) -> list[dict]:
    """
    获取用户的所有权限

    Args:
        user: 用户对象
        db: 数据库会话

    Returns:
        list[dict]: 权限字典列表
    """
    # 超级管理员拥有所有权限
    if user.is_superuser:
        result = await db.execute(select(Permission))
        return [perm.to_dict() for perm in result.scalars().all()]

    # 查询用户的角色和权限
    result = await db.execute(
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
        .distinct()
    )

    return [perm.to_dict() for perm in result.scalars().all()]
