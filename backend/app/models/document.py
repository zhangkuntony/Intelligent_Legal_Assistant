"""
文档和向量数据模型
"""

from sqlalchemy import Column, String, Text, Integer, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

# 导入pgvector扩展（如果可用）
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    # 如果没有pgvector，使用JSON字段作为备用
    from sqlalchemy import JSON as Vector

from ..core.database import Base

class Document(Base):
    """文档模型"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)             # MinIO对象路径，格式: documents/{user_id}/{uuid}.{ext}
    file_size = Column(BigInteger, nullable=False)
    file_category = Column(String(50), nullable=False)          # 关联到 document_category.category_name
    status = Column(String(20), default="processing")           # pending, processing, processed, error
    processing_error = Column(Text)
    total_chunks = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)
    meta_data = Column(JSON)                                    # 存储MinIO相关信息: {minio_bucket, minio_object, presigned_url, etc.}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系定义
    user = relationship("User", back_populates="documents")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title}, user_id={self.user_id})>"


class DocumentEmbedding(Base):
    """文档向量模型"""
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_content = Column(Text, nullable=False)

    # 使用pgvector的Vector类型，如果不可用则使用JSON作为备用
    if VECTOR_AVAILABLE:
        embedding = Column(Vector(1536))  # OpenAI embedding维度
    else:
        embedding = Column(JSON)  # 备用方案

    meta_data = Column(JSON)  # 存储分块元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系定义
    document = relationship("Document", back_populates="embeddings")

    def __repr__(self):
        return f"<DocumentEmbedding(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"