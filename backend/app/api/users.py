"""
用户管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from spacy.lang import ur
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, List

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.role import Role, UserRole

router = APIRouter()


# Pydantic 模型定义
class CreateUser(BaseModel):
    """创建用户的请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    full_name: Optional[str] = Field(None, description="全名")


class UpdateUser(BaseModel):
    """更新用户的请求模型"""
    full_name: Optional[str] = Field(None, description="全名")


class AssignRoles(BaseModel):
    """为用户分配角色的请求模型"""
    role_ids: List[str] = Field(..., description="角色ID列表")


@router.get("")
async def get_users(
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取用户列表（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问用户列表"
        )

    result = await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "roles": [
                    {
                        "id": str(ur.role.id),
                        "name": ur.role.name,
                        "code": ur.role.code,
                        "is_system": ur.role.is_system
                    }
                    for ur in user.user_roles
                ],
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            for user in users
        ],
        "total": len(users)
    }


@router.get("/{user_id}")
async def get_user(
        user_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取用户详情"""
    # 普通用户只能查看自己的信息，管理员可以查看所有用户信息
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问该用户信息"
        )

    result = await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": [
            {
                "id": str(ur.role.id),
                "name": ur.role.name,
                "code": ur.role.code,
                "is_system": ur.role.is_system
            }
            for ur in user.user_roles
        ],
        "last_login": user.last_login,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }


@router.post("")
async def create_user(
        user_data: CreateUser,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """创建用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限创建用户"
        )

    # 检查用户名是否已存在
    existing_username = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    existing_email = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用"
        )

    # 创建用户
    from ..core.security import get_password_hash
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "用户创建成功",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@router.put("/{user_id}")
async def update_user(
        user_id: str,
        user_data: UpdateUser,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """更新用户信息"""
    # 只能修改自己的信息或管理员可以修改所有用户
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己的用户信息"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新字段
    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    await db.commit()
    await db.refresh(user)

    return {
        "message": "用户信息更新成功",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@router.patch("/{user_id}/status")
async def update_user_status(
        user_id: str,
        is_active: bool,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """更新用户状态"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改用户状态"
        )

    # 不能禁用自己
    if str(current_user.id) == user_id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账户"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    user.is_active = is_active
    await db.commit()
    await db.refresh(user)

    return {
        "message": "用户状态更新成功",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "is_active": user.is_active
        }
    }


@router.delete("/{user_id}")
async def delete_user(
        user_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """删除用户（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除用户"
        )

    # 不能删除自己
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    await db.delete(user)
    await db.commit()

    return {"message": "用户删除成功"}


@router.post("/{user_id}/roles")
async def assign_user_roles(
        user_id: str,
        role_data: AssignRoles,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """为用户分配角色"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限分配用户角色"
        )

    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 删除原有角色
    existing_result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    existing_roles = existing_result.scalars().all()
    for ur in existing_roles:
        await db.delete(ur)

    # 添加角色
    for role_id in role_data.role_ids:
        # 验证角色是否存在
        role_result = await db.execute(
            select(Role).where(Role.id == role_id)
        )
        if role_result.scalar_one_or_none():
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by=current_user.id
            )
            db.add(user_role)

    await db.commit()

    return {"message": "角色分配成功"}


@router.get("/{user_id}/roles")
async def get_user_roles(
        user_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取用户的角色列表"""
    # 普通用户只能查看自己的角色，管理员可以查看所有用户的角色
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看该用户的角色"
        )

    result = await db.execute(
        select(UserRole)
        .options(selectinload(UserRole.role))
        .where(UserRole.user_id == user_id)
    )
    user_roles = result.scalars().all()

    return {
        "roles": [
            {
                "id": str(ur.role.id),
                "name": ur.role.name,
                "code": ur.role.code,
                "is_system": ur.role.is_system,
                "assigned_at": ur.assigned_at
            }
            for ur in user_roles
        ],
        "total": len(user_roles)
    }
