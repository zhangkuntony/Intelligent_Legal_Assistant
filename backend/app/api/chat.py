"""
智能法律聊天API路由
提供对话管理、消息发送、历史查询等接口
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.chat import ChatRequest, ChatResponse, RetrievedDoc, ConversationCreate, ConversationDetail
from ..models.conversation import Conversation, Message
from ..models.user import User
from ..services.chat.chat_service import chat_service

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/send", response_model=ChatResponse)
async def send_message(
        request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    发送消息并获取AI回复

    这是聊天功能的核心接口，会执行以下流程
    1. 获取或创建对话
    2. 保存用户消息
    3. 意图识别
    4. 问题理解
    5. RAG检索（如果是法律问题）
    6. LLM生成回复
    7. 保存AI消息
    8. 返回完整响应

    Args:
        request: 聊天请求，包含消息内容、对话ID等
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ChatResponse: 包含AI回复、意图、分析结果、检索文档等完整信息
    """
    try:
        logger.info(
            f"用户发送消息：user_id={current_user.id}，"
            f"conversation_id={request.conversation_id}，"
            f"content={request.content[:50]}"
        )

        # 调用ChatService生成回复
        response = await chat_service.generate_response(
            request=request,
            user_id=str(current_user.id)
        )

        logger.info(
            f"消息处理完成：message_id={response.message_id}, "
            f"tokens_used={response.tokens_used}, "
            f"retrieved_docs={len(response.retrieved_docs)}"
        )

        return response

    except ValueError as e:
        logger.error(f"请求参数错误：{e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"消息发送失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"消息处理失败：{str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationDetail])
async def get_conversations(
        skip: int = 0,
        limit: int = 20,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取用户的对话列表

    Args:
        skip: 跳过的数量（分页用）
        limit: 返回的最大数量
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        List[ConversationDetail]: 对话列表，按更新时间倒序排列
    """
    try:
        # 验证参数
        if skip < 0:
            skip = 0
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100     # 最大限制100条

        # 使用ChatService获取对话列表
        conversations = await chat_service.get_user_conversations(
            user_id=str(current_user.id),
            limit=limit,
            offset=skip
        )

        logger.info(
            f"获取对话列表成功：user_id={current_user.id}, "
            f"count={len(conversations)}"
        )

        return conversations

    except Exception as e:
        logger.error(f"获取对话列表失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败：{str(e)}"
        )

@router.post("/conversations", response_model=ConversationDetail)
async def create_conversation(
        conversation_data: Optional[ConversationCreate] = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    创建新对话

    Args:
        conversation_data: 对话创建信息（标题、描述等，可选）
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ConversationDetail: 创建的对话详情
    """
    try:
        # 使用ChatService的对话管理功能
        # 注意：由于ChatService的generate_response会自动创建对话，
        # 这里主要用于手动创建空对话

        # 如果提供了标题和描述，使用它们
        title = conversation_data.title if conversation_data and conversation_data.title else "新对话"
        description = conversation_data.description if conversation_data else None

        # 创建对话
        conversation = Conversation(
            user_id=current_user.id,
            title=title,
            description=description,
            is_archived=False
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        # 构建响应
        result = ConversationDetail(
            id=str(conversation.id),
            user_id=str(conversation.user_id),
            title=conversation.title,
            description=conversation.description,
            is_archived=conversation.is_archived,
            message_count=0,
            last_message_at=None,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

        logger.info(
            f"创建对话成功：user_id={current_user.id}, "
            f"conversation_id={conversation.id}"
        )

        return result

    except Exception as e:
        logger.error(f"创建对话失败：{e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建对话失败：{str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=dict)
async def get_conversation(
        conversation_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取对话详情及消息历史

    Args:
        conversation_id: 对话ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 包含对话信息和消息列表
    """
    try:
        # 使用ChatService获取对话详情
        conversation = await chat_service.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )

        # 检查权限
        if conversation["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问该对话"
            )

        logger.info(
            f"获取对话详情成功：conversation_id={conversation_id}, "
            f"message_count={conversation['message_count']}"
        )

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话详情失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话详情失败：{str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
        conversation_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    删除对话

    注意：删除对话会级联删除该对话下的所有消息

    Args:
        conversation_id: 对话ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 删除结果
    """
    try:
        # 先检查对话是否存在且属于当前用户
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

        # 使用ChatService删除对话
        success = await chat_service.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )

        logger.info(
            f"删除对话成功：conversation_id={conversation.id}, "
            f"user_id={current_user.id}"
        )

        return {"message": "对话删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败：{e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对话失败：{str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
        conversation_id: str,
        limit: int = 50,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取对话的消息历史（仅消息列表）

    Args:
        conversation_id: 对话ID
        limit: 返回的最大消息数量
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 消息列表
    """
    try:
        # 验证参数
        if limit < 1:
            limit = 50
        if limit > 200:
            limit = 200  # 最大限制200条

        # 检查对话是否存在且属于当前用户
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

        # 获取消息列表（按时间正序）
        messages = conversation.messages[-limit:] if len(conversation.messages) > limit else conversation.messages

        logger.info(
            f"获取消息历史成功：conversation_id={conversation.id}, "
            f"message_count={len(messages)}"
        )

        return {
            "conversation_id": conversation_id,
            "total_messages": len(conversation.messages),
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "tokens_used": msg.tokens_used,
                    "meta_data": msg.meta_data,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息历史失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取消息历史失败：{str(e)}"
        )

@router.put("/conversations/{conversation_id}")
async def update_conversation(
        conversation_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    更新对话信息（标题、描述）

    Args:
        conversation_id: 对话ID
        title: 新标题（可选）
        description: 新描述（可选）
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 更新后的对话信息
    """
    try:
        # 获取对话
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

        logger.info(
            f"更新对话成功：conversation_id={conversation.id}, "
            f"title={title}"
        )

        return {
            "message": "对话更新成功",
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "description": conversation.description,
                "updated_at": conversation.updated_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新对话失败：{e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新对话失败：{str(e)}"
        )




