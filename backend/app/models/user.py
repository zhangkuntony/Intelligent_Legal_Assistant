"""
用户数据模型
"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base

import uuid

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系定义
    conversations = relationship("Conversation", back_populates="user")
    documents = relationship("Document", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

    @property
    def display_name(self):
        """获取显示名称"""
        return self.full_name or self.username

    @property
    def roles(self):
        """获取用户的角色列表"""
        return [ur.role for ur in self.user_roles]

    @property
    def permissions(self):
        """获取用户的权限列表"""
        if self.is_superuser:
            return []

        # 这里需要在实际查询时动态获取
        return []

    async def has_permission(self, permission_code: str, db: AsyncSession) -> bool:
        """检查用户是否有指定权限"""
        # 超级管理员拥有所有权限
        if self.is_superuser:
            return True

        # 查询用户的角色和权限
        # 需要在方法内部导入以避免循环导入
        from .role import Permission, RolePermission, Role, UserRole

        result = await db.execute(
            select(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(Role, RolePermission.role_id == Role.id)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == self.id)
            .where(Permission.code == permission_code)
        )

        return result.scalar_one_or_none() is not None