"""
对话管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.conversation import Conversation, Message

router = APIRouter()


@router.get("")
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户对话列表"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .where(Conversation.is_archived == False)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    return {
        "conversations": [
            {
                "id": str(conv.id),
                "title": conv.title,
                "description": conv.description,
                "message_count": len(conv.messages),
                "created_at": conv.created_at,
                "updated_at": conv.updated_at
            }
            for conv in conversations
        ],
        "total": len(conversations)
    }


@router.post("")
async def create_conversation(
    title: str = "新对话",
    description: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新对话"""
    conversation = Conversation(
        user_id=current_user.id,
        title=title,
        description=description
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return {
        "message": "对话创建成功",
        "conversation": {
            "id": str(conversation.id),
            "title": conversation.title,
            "description": conversation.description,
            "created_at": conversation.created_at
        }
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取对话详情及消息列表"""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    # 检查权限
    if str(conversation.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问该对话"
        )
    
    return {
        "conversation": {
            "id": str(conversation.id),
            "title": conversation.title,
            "description": conversation.description,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        },
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "tokens_used": msg.tokens_used,
                "meta_data": msg.meta_data,
                "created_at": msg.created_at
            }
            for msg in conversation.messages
        ]
    }


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    title: str = None,
    description: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新对话信息"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    # 检查权限
    if str(conversation.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改该对话"
        )
    
    # 更新字段
    if title is not None:
        conversation.title = title
    if description is not None:
        conversation.description = description
    
    await db.commit()
    await db.refresh(conversation)
    
    return {
        "message": "对话更新成功",
        "conversation": {
            "id": str(conversation.id),
            "title": conversation.title,
            "description": conversation.description,
            "updated_at": conversation.updated_at
        }
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除对话"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    # 检查权限
    if str(conversation.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除该对话"
        )
    
    await db.delete(conversation)
    await db.commit()
    
    return {"message": "对话删除成功"}


@router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    tokens_used: int = 0,
    meta_data: dict = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """向对话添加消息"""
    # 验证角色
    if role not in ["user", "assistant", "system"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色必须是 user, assistant 或 system"
        )
    
    # 检查对话是否存在且属于当前用户
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    if str(conversation.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限向该对话添加消息"
        )
    
    # 创建消息
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        tokens_used=tokens_used,
        meta_data=meta_data
    )
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    return {
        "message": "消息添加成功",
        "message_data": {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "tokens_used": message.tokens_used,
            "created_at": message.created_at
        }
    }