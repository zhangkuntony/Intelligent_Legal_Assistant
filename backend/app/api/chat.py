"""
智能法律聊天API路由
提供对话管理、消息发送、历史查询等接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional

from ..core.database import get_db
from ..core.security import get_current_user
from ..models import Message, Document
from ..models.chat import ChatRequest, ChatResponse, ConversationCreate, ConversationDetail, ConversationsListResponse
from ..models.conversation import Conversation
from ..models.user import User
from ..services.chat.chat_service import chat_service
from ..utils.permission_helper import has_permission

import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== 辅助函数 ====================
def _validate_pagination_params(skip: int, limit: int) -> tuple[int, int]:
    """
        验证和规范化分页参数

        Args:
            skip: 跳过的数量
            limit: 返回的最大数量

        Returns:
            (skip, limit) 验证后的参数
        """
    if skip < 0:
        skip = 0
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100
    return skip, limit

def _build_conversation_count_query(
        user_id: Optional[str],
        db: AsyncSession
):
    """
        构建对话总数查询

        Args:
            user_id: 用户ID（None 表示查询所有用户）
            db: 数据库会话

        Returns:
            查询结果
        """
    from sqlalchemy import func
    if user_id is None:
        # 查询所有用户的对话总数
        return db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.is_archived == False)
        )
    else:
        # 查询指定用户的对话总数
        return db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.user_id == user_id)
            .where(Conversation.is_archived == False)
        )

async def _determine_conversation_scope(
        current_user: User,
        db: AsyncSession,
        for_history_page: bool = False
) -> tuple[bool, Optional[str]]:
    """
        确定查询对话的范围

        Args:
            current_user: 当前登录用户
            db: 数据库会话
            for_history_page: 是否从历史记录页面调用

        Returns:
            (can_view_all, user_id) 是否可以查看所有，以及用户ID
        """
    # 检查是否有 chat:view 权限
    can_view_all = for_history_page and await has_permission(current_user, "chat:view", db)

    # 如果可以查看所有，返回 None（表示所有用户），否则返回当前用户ID
    user_id = None if can_view_all else str(current_user.id)

    return can_view_all, user_id


# ==================== 路由定义 ====================
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

@router.post("/send/stream")
async def send_message_stream(
        request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    发送消息并获取AI回复（流式）

    这是聊天功能的核心接口，会执行以下流程
    1. 获取或创建对话
    2. 保存用户消息
    3. 意图识别
    4. 问题理解
    5. RAG检索（如果是法律问题）
    6. LLM生成回复
    7. 保存AI消息
    8. 返回完整响应

    使用 Server-Sent Events (SSE) 流式返回数据
    实时显示AI生成的每个字
    返回类型包括：intent, analysis, retrieved_docs, content, done, error

    Args:
        request: 聊天请求，包含消息内容、对话ID等
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流式响应
    """
    async def generate() :
        try:
            logger.info(
                f"用户发送流式消息：user_id={current_user.id}，"
                f"conversation_id={request.conversation_id}，"
                f"content={request.content[:50]}"
            )

            # 调用ChatService的流式生成方法
            async for chunk in chat_service.generate_response_stream(
                request=request,
                user_id=str(current_user.id)
            ):
                yield chunk

        except Exception as e:
            logger.error(f"流式消息处理失败：{e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"           # 禁用Nginx缓冲
        }
    )

@router.get("/conversations", response_model=ConversationsListResponse)
async def get_conversations(
        skip: int = 0,
        limit: int = 20,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取所有用户的对话列表（历史记录页面专用）

    需要 chat:view 权限才能查看所有用户的对话，否则只返回当前用户自己的对话

    Args:
        skip: 跳过的数量（分页用）
        limit: 返回的最大数量
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ConversationsListResponse: 对话列表和总数，按更新时间倒序排列
    """
    try:
        # 验证分页参数
        skip, limit = _validate_pagination_params(skip, limit)

        # 确定查询范围（这是历史记录页面，传入 for_history_page=True）
        can_view_all, user_id = await _determine_conversation_scope(
            current_user, db, for_history_page=True
        )

        # 使用ChatService获取对话列表
        conversations = await chat_service.get_user_conversations(
            user_id=user_id,
            limit=limit,
            offset=skip
        )

        # 获取总数
        total_result = await _build_conversation_count_query(user_id, db)
        total_count = total_result.scalar() or 0

        logger.info(
            f"获取对话列表成功：user_id={current_user.id}, "
            f"can_view_all={can_view_all}, "
            f"count={len(conversations)}, total={total_count}"
        )

        return {
            "conversations": conversations,
            "total": total_count
        }

    except Exception as e:
        logger.error(f"获取对话列表失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败：{str(e)}"
        )


@router.get("/my-conversations", response_model=ConversationsListResponse)
async def get_my_conversations(
        skip: int = 0,
        limit: int = 20,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的对话列表（对话页面专用）

    只返回当前登录用户自己的对话，不受 chat:view 权限影响

    Args:
        skip: 跳过的数量（分页用）
        limit: 返回的最大数量
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ConversationsListResponse: 对话列表和总数，按更新时间倒序排列
    """
    try:
        # 验证分页参数
        skip, limit = _validate_pagination_params(skip, limit)

        # 只查询当前用户的对话（不需要权限检查）
        user_id = str(current_user.id)

        # 使用ChatService获取对话列表
        conversations = await chat_service.get_user_conversations(
            user_id=user_id,
            limit=limit,
            offset=skip
        )

        # 获取当前用户的对话总数
        total_result = await _build_conversation_count_query(user_id, db)
        total_count = total_result.scalar() or 0

        logger.info(
            f"对话页面-获取对话列表成功：user_id={current_user.id}, "
            f"count={len(conversations)}, total={total_count}"
        )

        return {
            "conversations": conversations,
            "total": total_count
        }

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

    需要有 chat:view 权限或者是对话的创建者才能访问

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

        # 检查权限：有 chat:view 权限或者是对话的创建者才能访问
        can_view_all = await has_permission(current_user, "chat:view", db)
        if conversation["user_id"] != str(current_user.id) and not can_view_all:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问该对话"
            )

        logger.info(
            f"获取对话详情成功：conversation_id={conversation_id}, "
            f"user_id={conversation['user_id']}, message_count={conversation['message_count']}"
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


@router.get("/analytics")
async def get_conversation_analytics(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取会话分析统计数据

    需要 chat:view 权限才能查看所有用户的统计数据

    Args:
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 会话统计数据
    """
    try:
        # 检查权限
        can_view_all = await has_permission(current_user, "chat:view", db)

        from sqlalchemy import func, select, and_, desc
        from datetime import datetime, timedelta

        # 确定查询范围
        user_filter = None if can_view_all else Conversation.user_id == current_user.id

        # 1. 总对话数（未归档的）
        total_stmt = (
            select(func.count(Conversation.id))
            .where(Conversation.is_archived == False)
        )
        if user_filter:
            total_stmt = total_stmt.where(user_filter)
        total_result = await db.execute(total_stmt)
        total_conversations = total_result.scalar() or 0

        # 2. 活跃用户数（最近30天有对话的用户）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        active_users_stmt = (
            select(func.count(func.distinct(Conversation.user_id)))
            .where(Conversation.is_archived == False)
            .where(Conversation.created_at >= thirty_days_ago)
        )
        if user_filter:
            active_users_stmt = active_users_stmt.where(user_filter)
        active_users_result = await db.execute(active_users_stmt)
        active_users = active_users_result.scalar() or 0

        # 3. 平均对话时长（分钟）
        # 计算方法：每个对话的最后一条消息时间 - 第一条消息时间
        conversations_with_messages_stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.is_archived == False)
        )
        if user_filter:
            conversations_with_messages_stmt = conversations_with_messages_stmt.where(user_filter)
        conversations_result = await db.execute(conversations_with_messages_stmt)
        conversations_list = conversations_result.scalars().all()

        total_duration = 0
        valid_conversations = 0
        for conv in conversations_list:
            if len(conv.messages) >= 2:
                first_msg_time = conv.messages[0].created_at
                last_msg_time = conv.messages[-1].created_at
                duration_minutes = (last_msg_time - first_msg_time).total_seconds() / 60
                total_duration += duration_minutes
                valid_conversations += 1

        avg_duration = round(total_duration / valid_conversations) if valid_conversations > 0 else 0

        # 4. 对话趋势（按日期分组统计，最近7天）
        seven_days_ago = datetime.now() - timedelta(days=7)
        trend_stmt = (
            select(
                func.date(Conversation.created_at).label("date"),
                func.count(Conversation.id).label("count")
            )
            .where(Conversation.is_archived == False)
            .where(Conversation.created_at >= seven_days_ago)
            .group_by(func.date(Conversation.created_at))
            .order_by(func.date(Conversation.created_at))
        )
        if user_filter:
            trend_stmt = trend_stmt.where(user_filter)

        trend_result = await db.execute(trend_stmt)
        trend_data = [
            {
                "date": str(row.date),
                "count": row.count
            }
            for row in trend_result.all()
        ]

        # 5. 热门话题（基于对话标题的关键词统计，取前10）
        # 简单实现：按标题的词频统计
        import re
        from collections import Counter

        titles_stmt = (
            select(Conversation.title)
            .where(Conversation.is_archived == False)
            .where(Conversation.title.isnot(None))
            .where(Conversation.title != '')
        )
        if user_filter:
            titles_stmt = titles_stmt.where(user_filter)

        titles_result = await db.execute(titles_stmt)
        titles = [row[0] for row in titles_result.all()]

        # 使用TextAnalyzer提取关键词
        from ..utils.text_analyzer import text_analyzer

        hot_topics = text_analyzer.extract_keywords_from_texts(
            texts=titles,
            top_k=10,
            min_word_length=2,
            max_word_length=4,
            use_stop_words=True,
            domain='legal'  # 使用法律领域停用词
        )

        # 6. 最近对话记录（前10条）
        recent_conversations_stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages), selectinload(Conversation.user))
            .where(Conversation.is_archived == False)
            .order_by(desc(Conversation.updated_at))
            .limit(10)
        )
        if user_filter:
            recent_conversations_stmt = recent_conversations_stmt.where(user_filter)

        recent_result = await db.execute(recent_conversations_stmt)
        recent_conversations_list = recent_result.scalars().all()

        recent_conversations_data = []
        for conv in recent_conversations_list:
            # 计算对话时长
            duration_minutes = 0
            if len(conv.messages) >= 2:
                first_msg_time = conv.messages[0].created_at
                last_msg_time = conv.messages[-1].created_at
                duration_minutes = round((last_msg_time - first_msg_time).total_seconds() / 60)

            recent_conversations_data.append({
                "id": str(conv.id),
                "user_id": str(conv.user_id),
                "user_name": conv.user.display_name,
                "title": conv.title,
                "duration": duration_minutes,
                "messages": len(conv.messages),
                "time": conv.updated_at.isoformat()
            })

        logger.info(
            f"获取会话分析数据成功：total={total_conversations}, "
            f"active_users={active_users}, avg_duration={avg_duration}"
        )

        return {
            "stats": {
                "total_conversations": total_conversations,
                "active_users": active_users,
                "avg_duration": avg_duration
            },
            "trend": trend_data,
            "hot_topics": hot_topics,
            "recent_conversations": recent_conversations_data
        }

    except Exception as e:
        logger.error(f"获取会话分析数据失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话分析数据失败：{str(e)}"
        )


@router.get("/dashboard-stats")
async def get_dashboard_stats(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    获取Dashboard统计数据

    包括：
    - 对话记录总数
    - 文档数量
    - 使用时长（小时）

    Args:
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: Dashboard统计数据
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # 检查权限：有 chat:view 权限的用户可以看到所有数据，否则只看自己的
        can_view_all = await has_permission(current_user, "chat:view", db)
        user_filter = None if can_view_all else Conversation.user_id == current_user.id

        # 1. 获取对话总数（未归档的）
        total_conv_stmt = (
            select(func.count(Conversation.id))
            .where(Conversation.is_archived == False)
        )
        if user_filter:
            total_conv_stmt = total_conv_stmt.where(user_filter)

        total_conv_result = await db.execute(total_conv_stmt)
        total_conversations = total_conv_result.scalar() or 0

        # 2. 获取文档总数
        if can_view_all:
            # 管理员可以看到所有用户的文档
            total_docs_stmt = select(func.count(Document.id))
        else:
            # 普通用户只看自己的文档
            total_docs_stmt = (
                select(func.count(Document.id))
                .where(Document.user_id == current_user.id)
            )

        total_docs_result = await db.execute(total_docs_stmt)
        total_documents = total_docs_result.scalar() or 0

        # 3. 计算使用时长（小时）
        # 计算方法：所有有消息的对话的（最后一条消息时间 - 第一条消息时间）之和
        conversations_with_messages_stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.is_archived == False)
        )
        if user_filter:
            conversations_with_messages_stmt = conversations_with_messages_stmt.where(user_filter)

        conversations_result = await db.execute(conversations_with_messages_stmt)
        conversations_list = conversations_result.scalars().all()

        total_duration_seconds = 0
        for conv in conversations_list:
            if len(conv.messages) >= 2:
                first_msg_time = conv.messages[0].created_at
                last_msg_time = conv.messages[-1].created_at
                duration_seconds = (last_msg_time - first_msg_time).total_seconds()
                total_duration_seconds += duration_seconds

        # 转换为小时，保留一位小数
        total_hours = round(total_duration_seconds / 3600, 1)

        # 4. 获取最近对话记录（最近5条）
        recent_conv_stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages), selectinload(Conversation.user))
            .where(Conversation.is_archived == False)
            .order_by(desc(Conversation.updated_at))
            .limit(5)
        )
        if user_filter:
            recent_conv_stmt = recent_conv_stmt.where(user_filter)

        recent_result = await db.execute(recent_conv_stmt)
        recent_conversations_list = recent_result.scalars().all()

        recent_conversations = []
        for conv in recent_conversations_list:
            # 格式化时间
            updated_at = conv.updated_at.strftime('%Y-%m-%d %H:%M')

            recent_conversations.append({
                "id": str(conv.id),
                "title": conv.title,
                "time": updated_at
            })

        logger.info(
            f"获取Dashboard统计数据成功：user_id={current_user.id}, "
            f"conversations={total_conversations}, "
            f"documents={total_documents}, "
            f"hours={total_hours}"
        )

        return {
            "stats": {
                "conversations": total_conversations,
                "documents": total_documents,
                "totalTime": total_hours
            },
            "recent_conversations": recent_conversations
        }

    except Exception as e:
        logger.error(f"获取Dashboard统计数据失败：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Dashboard统计数据失败：{str(e)}"
        )


