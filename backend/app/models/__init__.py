"""
数据模型包初始化文件
导出所有模型类
"""

from .user import User
from .conversation import Conversation, Message
from .document import Document
from .document_category import DocumentCategory
from .intent import IntentClassification, LEGAL_CATEGORIES
from .question import QuestionAnalysis, EntityExtraction
from .chat import (
    MessageRole,
    RetrievedDoc,
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationDetail
)

__all__ = [
    "User",
    "Conversation",
    "Message",
    "Document",
    "DocumentCategory",
    "IntentClassification",
    "LEGAL_CATEGORIES",
    "QuestionAnalysis",
    "EntityExtraction",
    "MessageRole",
    "RetrievedDoc",
    "ChatRequest",
    "ChatResponse",
    "ConversationCreate",
    "ConversationDetail",
]
