"""
聊天相关数据模型
用于存储和传递聊天请求和响应
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

from .intent import IntentClassification
from .question import QuestionAnalysis


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class RetrievedDoc(BaseModel):
    """检索到的文档片段

    属性:
        document_id: 文档ID
        document_title: 文档标题
        chunk_index: 文档分块索引
        chunk_content: 分块内容
        score: 相似度分数
        metadata: 额外的元数据
    """
    document_id: str = Field(..., description="文档ID")
    document_title: str = Field(..., description="文档标题")
    chunk_index: int = Field(..., description="分块索引")
    chunk_content: str = Field(..., description="分块内容")
    score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    metadata: Optional[dict] = Field(default_factory=dict, description="额外元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_title": "劳动合同法",
                "chunk_index": 5,
                "chunk_content": "用人单位解除劳动合同，应当向劳动者支付经济补偿...",
                "score": 0.89,
                "metadata": {"source": "法律法规", "page": 10}
            }
        }

class ChatRequest(BaseModel):
    """聊天请求模型

    属性:
        content: 用户输入的问题内容
        conversation_id: 对话ID（可选，为空则创建新对话）
        include_thinking: 是否包含思考过程
        top_k: 检索文档数量
    """
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="用户输入的问题内容"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="对话ID，为空则创建新对话"
    )
    include_thinking: bool = Field(
        default=False,
        description="是否返回AI的思考过程"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="检索相关文档的数量"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "劳动合同解除需要支付经济补偿吗？",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "include_thinking": False,
                "top_k": 5
            }
        }

class ChatResponse(BaseModel):
    """聊天响应模型

    属性:
        message_id: 消息ID
        conversation_id: 对话ID
        content: AI生成的回答内容
        intent: 意图分类结果
        analysis: 问题分析结果
        retrieved_docs: 检索到的相关文档列表
        tokens_used: 使用的token数量
        thinking_process: 思考过程（可选）
        created_at: 创建时间
    """
    message_id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    content: str = Field(..., description="AI生成的回答内容")
    intent: IntentClassification = Field(..., description="意图分类结果")
    analysis: QuestionAnalysis = Field(..., description="问题分析结果")
    retrieved_docs: List[RetrievedDoc] = Field(default_factory=list, description="检索到的相关文档")
    tokens_used: int = Field(..., ge=0, description="使用的token数量")
    thinking_process: Optional[str] = Field(None, description="AI的思考过程")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "550e8400-e29b-41d4-a716-446655440001",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "根据《劳动合同法》第四十六条规定，用人单位解除劳动合同...",
                "intent": {
                    "is_legal_related": True,
                    "legal_category": "民事",
                    "confidence": 0.95,
                    "suggested_topics": ["劳动合同", "经济补偿"]
                },
                "analysis": {
                    "core_issue": "劳动合同解除的经济补偿问题",
                    "legal_elements": ["劳动合同", "解除", "经济补偿"],
                    "key_entities": ["用人单位", "劳动者"],
                    "query_for_retrieval": "劳动合同解除 经济补偿",
                    "missing_info": []
                },
                "retrieved_docs": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_title": "劳动合同法",
                        "chunk_index": 5,
                        "chunk_content": "用人单位解除劳动合同...",
                        "score": 0.89,
                        "metadata": {}
                    }
                ],
                "tokens_used": 1250,
                "thinking_process": "用户询问关于劳动合同解除的经济补偿问题...",
                "created_at": "2024-01-27T10:30:00Z"
            }
        }

class ConversationCreate(BaseModel):
    """创建对话请求模型"""
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    description: Optional[str] = Field(None, description="对话描述")

class ConversationDetail(BaseModel):
    """对话详情模型"""
    id: str
    user_id: str
    title: str
    description: Optional[str]
    is_archived: bool
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
