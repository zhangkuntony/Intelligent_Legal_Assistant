"""
文档管理API路由
"""
import hashlib
import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import os
import shutil
import uuid
from pathlib import Path

from ..core.database import get_db
from ..core.config import settings
from ..core.security import get_current_user
from ..models.user import User
from ..models.document import Document, DocumentEmbedding

from ..services.langchain_processor.unified_processor import UnifiedDocumentProcessor
from ..services.langchain_processor.retrieval_service import RetrievalService

router = APIRouter()

logger = logging.getLogger(__name__)

# 临时下载令牌存储
_download_tokens = {}

# 初始化统一处理器（全局单例）
unified_processor = UnifiedDocumentProcessor()
retrieval_service = RetrievalService(unified_processor)


@router.get("")
async def get_documents(
        skip: int = 0,
        limit: int = 20,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    print(f"get documents skip: {skip}, limit: {limit}")
    """获取用户文档列表"""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()

    return {
        "documents": [
            {
                "id": str(doc.id),
                "title": doc.title,
                "filename": doc.filename,
                "file_size": doc.file_size,
                "file_category": doc.file_category,
                "status": doc.status,
                "total_chunks": doc.total_chunks,
                "processed_chunks": doc.processed_chunks,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at
            }
            for doc in documents
        ],
        "total": len(documents)
    }


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        title: str = Form(None),
        file_category: str = Form(None),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """上传文档"""
    # 验证文件类型
    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型，仅支持 PDF、Word、TXT、Markdown 文件"
        )

    logger.info(f"upload {file.filename}")

    # 验证文件大小（最大50MB）
    max_size = 50 * 1024 * 1024
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置文件指针

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件大小超过限制（最大50MB）"
        )

    # 创建上传目录
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename

    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 创建文档记录
    document_title = title or Path(file.filename).stem
    category = file_category or "其他"
    document = Document(
        user_id=current_user.id,
        title=document_title,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_category=category,
        status="uploaded"
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return {
        "message": "文档上传成功",
        "document": {
            "id": str(document.id),
            "title": document.title,
            "filename": document.filename,
            "file_size": document.file_size,
            "status": document.status,
            "created_at": document.created_at
        }
    }


@router.get("/{document_id}/download")
async def download_document(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    下载文档源文件
    - 验证文档权限
    - 返回安全的下载链接
    """
    # 1. 验证文档存在性
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    # 2. 验证用户权限
    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限下载该文档"
        )

    # 3. 验证文件是否存在
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或已被删除"
        )

    # 4. 返回安全下载信息（不直接暴露文件路径）
    file_path = Path(document.file_path)
    filename = file_path.name  # 获取UUID文件名

    return {
        "download_url": f"/api/uploads/{filename}",
        "original_filename": document.filename,
        "file_size": document.file_size,
        "file_type": document.file_type,
        "expires_in": 3600  # 链接有效期1小时
    }


@router.get("/{document_id}/download/direct")
async def download_document_direct(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    直接下载文档（文件流方式）
    - 适用于需要直接下载的场景
    """
    # 1. 验证文档存在性和权限（同上）
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限下载该文档"
        )

    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或已被删除"
        )

    # 2. 直接返回文件流
    return FileResponse(
        path=document.file_path,
        filename=document.filename,  # 使用原始文件名
        media_type=document.file_type,
        headers={
            "Content-Disposition": f"attachment; filename={document.filename}",
            "Cache-Control": "no-cache"
        }
    )


@router.post("/{document_id}/download/token")
async def generate_download_token(
        document_id: str,
        expires_in: int = 3600,  # 默认1小时
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    生成有时效性的下载令牌
    - 适用于前端需要预生成下载链接的场景
    """
    # 验证文档权限（同上）
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    if str(document.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="没有下载权限")

    # 生成唯一令牌
    token_data = f"{document_id}_{current_user.id}_{time.time()}"
    token = hashlib.sha256(token_data.encode()).hexdigest()[:16]

    # 存储令牌信息
    _download_tokens[token] = {
        "document_id": document_id,
        "user_id": str(current_user.id),
        "expires_at": datetime.now() + timedelta(seconds=expires_in),
        "file_path": document.file_path,
        "original_filename": document.filename
    }

    return {
        "token": token,
        "expires_in": expires_in,
        "expires_at": _download_tokens[token]["expires_at"].isoformat(),
        "download_url": f"/api/documents/download/token/{token}"
    }


@router.get("/download/token/{token}")
async def download_with_token(token: str):
    """
    使用令牌下载文档
    - 无需认证，适合分享场景
    """
    # 验证令牌
    token_info = _download_tokens.get(token)
    if not token_info:
        raise HTTPException(status_code=404, detail="下载令牌无效或已过期")

    # 验证令牌有效期
    if datetime.now() > token_info["expires_at"]:
        del _download_tokens[token]  # 清理过期令牌
        raise HTTPException(status_code=410, detail="下载令牌已过期")

    # 验证文件存在性
    if not os.path.exists(token_info["file_path"]):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 返回文件
    return FileResponse(
        path=token_info["file_path"],
        filename=token_info["original_filename"],
        media_type="application/octet-stream",  # 通用类型
        headers={
            "Content-Disposition": f"attachment; filename={token_info['original_filename']}"
        }
    )


@router.get("/{document_id}")
async def get_document(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取文档详情"""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.embeddings))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    # 检查权限
    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问该文档"
        )

    response_data = {
        "document": {
            "id": str(document.id),
            "title": document.title,
            "filename": document.filename,
            "file_size": document.file_size,
            "file_category": document.file_category,
            "status": document.status,
            "processing_error": document.processing_error,
            "total_chunks": document.total_chunks,
            "processed_chunks": document.processed_chunks,
            "meta_data": document.meta_data,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "download_info": {
                "available": os.path.exists(document.file_path),
                "direct_download_url": f"/api/documents/{document_id}/download/direct",
                "secure_download_url": f"/api/documents/{document_id}/download",
                "file_exists": os.path.exists(document.file_path)
            }
        },
        "embeddings": [
            {
                "id": str(emb.id),
                "chunk_index": emb.chunk_index,
                "chunk_content": emb.chunk_content[:200] + "..." if len(emb.chunk_content) > 200 else emb.chunk_content,
                "created_at": emb.created_at
            }
            for emb in document.embeddings
        ]
    }

    return response_data


@router.put("/{document_id}")
async def update_document(
        document_id: str,
        title: str = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """更新文档信息"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    # 检查权限
    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改该文档"
        )

    # 更新字段
    if title is not None:
        document.title = title

    await db.commit()
    await db.refresh(document)

    return {
        "message": "文档信息更新成功",
        "document": {
            "id": str(document.id),
            "title": document.title,
            "updated_at": document.updated_at
        }
    }


@router.delete("/{document_id}")
async def delete_document(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """删除文档"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    # 检查权限
    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除该文档"
        )

    try:
        # 获取MinIO对象名称（从元数据中）
        minio_object = None
        if document.meta_data and isinstance(document.meta_data, dict):
            minio_object = document.meta_data.get("minio_object")

        # 删除Milvus中的向量数据
        await unified_processor.delete_document_vectors(
            document_id=str(document.id),
            minio_object=minio_object
        )
    except Exception as e:
        logger.error(f"删除Milvus向量失败：{str(e)}")

    # 删除本地文件
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    await db.delete(document)
    await db.commit()

    return {"message": "文档删除成功"}


@router.post("/{document_id}/process")
async def process_document(
        document_id: str,
        strategy: str = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """处理文档（生成向量嵌入）- 使用LangChain集成"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    # 检查权限
    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限处理该文档"
        )

    # 检查文档状态
    if document.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档正在处理中"
        )

    if document.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档已处理完成"
        )

    try:
        # 更新状态为处理中
        document.status = "processing"
        await db.commit()

        # 使用统一处理器处理文档
        processed_result = await unified_processor.process_document(
            file_path=document.file_path,
            strategy=strategy,
            metadata={
                'document_id': str(document.id),
                'user_id': str(current_user.id),
                'file_category': document.file_category,
                'title': document.title
            }
        )

        # 更新文档信息
        if processed_result.status.value == "completed":
            document.status = "completed"
            document.total_chunks = processed_result.processing_stats.total_chunks
            document.processed_chunks = processed_result.processing_stats.total_chunks
            document.meta_data = processed_result.metadata
        else:
            document.status = "failed"
            document.processing_error = str(processed_result.processing_stats.errors[0])

        await db.commit()
        await db.refresh(document)

        return {
            "message": "文档处理完成",
            "document_id": str(document.id),
            "status": document.status,
            "total_chunks": document.total_chunks,
            "processing_time": processed_result.processing_stats.processing_time,
            "strategy": strategy or "hybrid"
        }

    except Exception as e:
        document.status = "failed"
        document.processing_error = str(e)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档处理失败: {str(e)}"
        )


@router.post("/search")
async def search_documents(
        query: str = Form(...),
        strategy: str = Form("hybrid"),
        top_k: int = Form(5),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """搜索相关文档内容"""
    try:
        # 检索相关文档
        results = await retrieval_service.retrieve(
            query=query,
            strategy=strategy,
            top_k=top_k
        )

        return {
            "query": query,
            "strategy": strategy,
            "results": results,
            "total": len(results)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )



@router.get("/{document_id}/embeddings")
async def get_document_embeddings(
        document_id: str,
        skip: int = 0,
        limit: int = 50,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """获取文档的向量嵌入列表"""
    # 检查文档权限
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )

    if str(document.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问该文档的嵌入信息"
        )

    # 获取嵌入列表
    result = await db.execute(
        select(DocumentEmbedding)
        .where(DocumentEmbedding.document_id == document_id)
        .order_by(DocumentEmbedding.chunk_index)
        .offset(skip)
        .limit(limit)
    )
    embeddings = result.scalars().all()

    return {
        "embeddings": [
            {
                "id": str(emb.id),
                "chunk_index": emb.chunk_index,
                "chunk_content": emb.chunk_content,
                "embedding": emb.embedding[:10] if emb.embedding else None,  # 只返回前10个维度作为预览
                "meta_data": emb.meta_data,
                "created_at": emb.created_at
            }
            for emb in embeddings
        ],
        "total": len(embeddings)
    }