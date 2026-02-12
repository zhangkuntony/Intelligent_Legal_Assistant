"""
角色管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.permissions import RolePermission, Permission
from ..models.user import User
from ..models.role import Role, UserRole
from ..utils.permission_helper import has_permission

router = APIRouter()


# Pydantic 模型定义
class RoleCreate(BaseModel):
    """创建角色的请求模型"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    code: str = Field(..., min_length=2, max_length=50, pattern="^[a-z_]+$", description="角色代码")
    description: Optional[str] = Field(None, description="角色描述")


class RoleUpdate(BaseModel):
    """更新角色的请求模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")


class PermissionAssign(BaseModel):
    """分配权限的请求模型"""
    permission_ids: List[str] = Field(..., description="权限ID列表")


# ==================== 角色路由 ====================

@router.get("")
async def get_roles(
        skip: int = 0,
        limit: int = 100,
        include_system: bool = True,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取角色列表"""
    # 检查权限
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看角色列表"
        )

    # 构建查询
    query = select(Role)
    if not include_system:
        query = query.where(Role.is_system == False)

    # 添加用户数统计
    result = await db.execute(query.offset(skip).limit(limit))
    roles = result.scalars().all()

    # 为每个角色获取用户数
    role_list = []
    for role in roles:
        user_count_result = await db.execute(
            select(UserRole).where(UserRole.role_id == role.id)
        )
        user_count = len(user_count_result.scalars().all())

        role_dict = role.to_dict()
        role_dict["user_count"] = user_count
        role_list.append(role_dict)

    return {
        "roles": role_list,
        "total": len(role_list)
    }

@router.post("")
async def create_role(
        role_data: RoleCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """创建角色"""
    if not await has_permission(current_user, "role:create", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限创建角色"
        )

    # 检查角色代码是否已存在
    existing_result = await db.execute(select(Role).where(Role.code == role_data.code))
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色代码已存在"
        )

    # 创建角色
    role = Role(
        name=role_data.name,
        code=role_data.code,
        description=role_data.description,
        is_system=False
    )

    db.add(role)
    await db.commit()
    await db.refresh(role)

    return {
        "message": "角色创建成功",
        "role": role.to_dict()
    }

@router.get("/{role_id}")
async def get_role(
        role_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取角色详情"""
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看角色详情"
        )

    # 查询角色及其权限
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 获取用户数
    user_count_result = await db.execute(
        select(UserRole).where(UserRole.role_id == role.id)
    )
    user_count = len(user_count_result.scalars().all())

    # 构建响应
    role_dict = role.to_dict()
    role_dict["user_count"] = user_count
    role_dict["permissions"] = [
        rp.permission.to_dict() for rp in role.role_permissions
    ]

    return role_dict


@router.put("/{role_id}")
async def update_role(
        role_id: str,
        role_data: RoleUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """更新角色信息"""
    if not await has_permission(current_user, "role:update", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限编辑角色"
        )

    # 查询角色
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 系统角色不允许修改
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统内置角色不允许修改"
        )

    # 更新字段
    if role_data.name is not None:
        role.name = role_data.name
    if role_data.description is not None:
        role.description = role_data.description

    await db.commit()
    await db.refresh(role)

    return {
        "message": "角色更新成功",
        "role": role.to_dict()
    }

@router.delete("/{role_id}")
async def delete_role(
        role_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """删除角色"""
    if not await has_permission(current_user, "role:delete", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除角色"
        )

    # 查询角色
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 系统角色不允许删除
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统内置角色不允许删除"
        )

    # 检查是否有用户使用该角色
    user_role_result = await db.execute(
        select(UserRole).where(UserRole.role_id == role.id)
    )
    if user_role_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该角色下还有用户，无法删除"
        )

    # 删除角色（级联删除关联数据）
    await db.delete(role)
    await db.commit()

    return {"message": "角色删除成功"}

@router.post("/{role_id}/permissions")
async def assign_permissions(
        role_id: str,
        assign_data: PermissionAssign,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """为角色分配权限"""
    """为角色分配权限"""
    if not await has_permission(current_user, "role:update", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限分配角色权限"
        )

    # 查询角色
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 系统角色不允许修改权限
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统内置角色的权限不允许修改"
        )

    # 删除原有权限
    existing_result = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role.id)
    )
    existing_permissions = existing_result.scalars().all()
    for rp in existing_permissions:
        await db.delete(rp)

    # 添加新权限
    for perm_id in assign_data.permission_ids:
        # 验证权限是否存在
        perm_result = await db.execute(
            select(Permission).where(Permission.id == perm_id)
        )
        if perm_result.scalar_one_or_none():
            role_permission = RolePermission(
                role_id = role_id,
                permission_id = perm_id
            )
            db.add(role_permission)

    await db.commit()

    return {"message": "权限分配成功"}


@router.get("/{role_id}/permissions")
async def get_role_permissions(
        role_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取角色的权限列表"""
    if not await has_permission(current_user, "role:view", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看角色权限"
        )

    result = await db.execute(
        select(RolePermission)
        .options(selectinload(RolePermission.permission))
        .where(RolePermission.role_id == role_id)
    )
    role_permissions = result.scalars().all()

    permissions = [rp.permission.to_dict() for rp in role_permissions]

    return {
        "permissions": permissions,
        "total": len(permissions)
    }