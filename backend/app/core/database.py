"""
数据库连接和配置
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from .config import settings

class Base(DeclarativeBase):
    """SQLAlchemy基类"""
    pass

# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",  # 开发环境显示SQL日志
    pool_pre_ping=True,  # 连接池预检查
    pool_recycle=3600,   # 连接回收时间
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """依赖注入：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 导入所有模型以确保它们被注册
from ..models.conversation import Conversation, Message
from ..models.document import Document, DocumentEmbedding
from ..models.user import User

# 建立模型关系（避免循环导入）
User.conversations = relationship("Conversation", back_populates="user")
User.documents = relationship("Document", back_populates="user")
Conversation.user = relationship("User", back_populates="conversations")
Conversation.messages = relationship("Message", back_populates="conversation")
Message.conversation = relationship("Conversation", back_populates="messages")
Document.user = relationship("User", back_populates="documents")
Document.embeddings = relationship("DocumentEmbedding", back_populates="document")
DocumentEmbedding.document = relationship("Document", back_populates="embeddings")