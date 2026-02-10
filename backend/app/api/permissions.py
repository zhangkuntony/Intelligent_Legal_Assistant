"""
权限管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.permissions import Permission, RolePermission
from ..models.role import Role
from ..utils.permission_helper import has_permission

router = APIRouter()


# ==================== 权限路由 ====================
@router.get("/stats")
async def get_permission_stats(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取权限统计信息"""
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看权限统计"
        )

    # 获取权限总数
    total_permissions_result = await db.execute(select(Permission))
    total_permissions = len(total_permissions_result.scalars().all())

    # 获取模块数量
    module_result = await db.execute(select(Permission.module).distinct())
    modules = [row[0] for row in module_result.all()]
    total_modules = len(modules)

    # 获取角色数量
    total_roles_result = await db.execute(select(Role))
    total_roles = len(total_roles_result.scalars().all())

    return {
        "total_permissions": total_permissions,
        "total_modules": total_modules,
        "total_roles": total_roles,
        "modules": modules
    }


@router.get("")
async def get_permissions(
        module: Optional[str] = None,
        include_roles: bool = False,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取权限列表"""
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看权限列表"
        )

    # 构建查询
    query = select(Permission)
    if module:
        query = query.where(Permission.module == module)

    result = await db.execute(query)
    permissions = result.scalars().all()

    # 如果需要包含角色信息
    if include_roles:
        permissions_with_roles = []
        for perm in permissions:
            # 查询拥有该权限的角色
            role_permission_result = await db.execute(
                select(RolePermission)
                .options(selectinload(RolePermission.role))
                .where(RolePermission.permission_id == perm.id)
            )
            role_permissions = role_permission_result.scalars().all()

            perm_dict = perm.to_dict()
            perm_dict["roles"] = [
                {
                    "id": str(rp.role_id),
                    "name": rp.role.name,
                    "code": rp.role.code,
                    "is_system": rp.role.is_system
                }
                for rp in role_permissions
            ]
            perm_dict["role_count"] = len(role_permissions)
            permissions_with_roles.append(perm_dict)

        return {
            "permissions": permissions_with_roles,
            "total": len(permissions_with_roles)
        }

    return {
        "permissions": [perm.to_dict() for perm in permissions],
        "total": len(permissions)
    }


@router.get("/all")
async def get_all_permissions(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取所有权限列表"""
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看权限列表"
        )

    result = await db.execute(select(Permission))
    permissions = result.scalars().all()

    return {
        "permissions": [perm.to_dict() for perm in permissions],
        "total": len(permissions)
    }


@router.get("/{permission_id}")
async def get_permission(
        permission_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取权限详情"""
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看权限详情"
        )

    # 查询权限
    result = await db.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="权限不存在"
        )

    # 查询拥有该权限的角色
    role_permission_result = await db.execute(
        select(RolePermission)
        .options(selectinload(RolePermission.role))
        .where(RolePermission.permission_id == permission.id)
    )
    role_permissions = role_permission_result.scalars().all()

    # 构建响应
    perm_dict = permission.to_dict()
    perm_dict["roles"] = [
        {
            "id": str(rp.role.id),
            "name": rp.role.name,
            "code": rp.role.code,
            "is_system": rp.role.is_system,
            "user_count": None
        }
        for rp in role_permissions
    ]
    perm_dict["role_count"] = len(role_permissions)

    return perm_dict