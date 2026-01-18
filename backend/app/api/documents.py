"""
文档管理API路由
"""
import hashlib
import logging
import os
import shutil
import time

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from io import BytesIO
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from urllib.parse import quote

from ..core.config import settings
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.document_category import DocumentCategory
from ..models.user import User
from ..models.document import Document, DocumentEmbedding

from ..services.langchain_processor.unified_processor import UnifiedDocumentProcessor
from ..services.langchain_processor.retrieval_service import RetrievalService
from ..services.storage.minio_service import minio_service

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
    """获取用户文档列表，使用JOIN关联document_category表"""
    stmt = (
        select(
            Document.id,
            Document.title,
            Document.filename,
            Document.description,
            Document.file_size,
            Document.file_category,
            Document.status,
            Document.total_chunks,
            Document.processed_chunks,
            Document.created_at,
            Document.updated_at,
            DocumentCategory.category_name.label("file_category_name")
        )
        .outerjoin(DocumentCategory, Document.file_category == DocumentCategory.category_code)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    documents = result.all()

    count_stmt = (
        select(func.count())
        .select_from(Document)
        .where(Document.user_id == current_user.id)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # 转换为Dict格式
    result_list = []
    for doc in documents:
        result_list.append({
            "id": str(doc.id),
            "title": doc.title,
            "filename": doc.filename,
            "description": doc.description,
            "file_size": doc.file_size,
            "file_category": doc.file_category,
            "file_category_name": doc.file_category_name,
            "status": doc.status,
            "total_chunks": doc.total_chunks,
            "processed_chunks": doc.processed_chunks,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at
        })

    return {
        "documents": result_list, "total": total
    }


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        title: str = Form(None),
        file_category: str = Form(None),
        description: str = Form(None),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """上传文档到MinIO"""
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
    logger.info(f"文件类型: {file_category}")
    logger.info(f"文件描述: {description}")

    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)

    # 验证文件大小（最大50MB）
    max_size = 50 * 1024 * 1024

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件大小超过限制（最大50MB）"
        )

    try:
        # 生成唯一的MinIO对象名称
        import uuid
        file_extension = Path(file.filename).suffix
        object_name = f"documents/{current_user.id}/{uuid.uuid4()}{file_extension}"

        file_content_type = file.content_type

        # 上传到MinIO
        upload_result = minio_service.upload_bytes(
            data=file_content,
            object_name=object_name,
            length=file_size,
            content_type=file_content_type,
            metadata={
                'user_id': str(current_user.id),
                'file_category': file_category
            }
        )

        logger.info(f"文件上传到MinIO成功: {object_name}")

        # 创建文档记录 - 中文信息存储在PostgreSQL中
        document_title = title or Path(file.filename).stem
        category = file_category or "其他"
        document = Document(
            user_id=current_user.id,
            title=document_title,
            filename=file.filename,
            file_path=object_name,
            file_size=file_size,
            file_category=category,
            description=description,
            status="pending",
            meta_data={
                'minio_bucket': upload_result['bucket_name'],
                'minio_object': upload_result['object_name'],
                'minio_etag': upload_result['etag'],
                'file_category': file_category,
                'presigned_url': upload_result['presigned_url'],
                'content_type': file_content_type
            }
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        logger.info(f"文档记录创建成功: {document.id}")

        return {
            "message": "文档上传成功",
            "document": {
                "id": str(document.id),
                "title": document.title,
                "filename": document.filename,
                "file_size": document.file_size,
                "file_category": document.file_category,
                "description": document.description,
                "status": document.status,
                "created_at": document.created_at,
                "download_url": upload_result['presigned_url']
            }
        }

    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档上传失败: {str(e)}"
        )

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

    try:
        # 2. 从MinIO下载数据
        file_content = minio_service.download_bytes(document.file_path)

        logger.info(f"文件下载成功: {document.filename}, 大小: {len(file_content)}")

        # 3. 返回文件流
        file_stream = BytesIO(file_content)
        content_type = document.meta_data.get('content_type', 'application/octet-stream') if document.meta_data else 'application/octet-stream'

        # 处理文件名编码，支持中文
        filename_encoded = quote(document.filename, safe='')
        content_disposition = f"attachment; filename*=UTF-8''{filename_encoded}"

        logger.info(f"Content-Disposition: {content_disposition}")

        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": content_disposition,
                "Content-Length": str(len(file_content)),
            }
        )

    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件下载失败: {str(e)}"
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
            "description": document.description,
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
        description: str = None,
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

    if description is not None:
        document.description = description

    await db.commit()
    await db.refresh(document)

    return {
        "message": "文档信息更新成功",
        "document": {
            "id": str(document.id),
            "title": document.title,
            "description": document.description,
            "updated_at": document.updated_at
        }
    }


@router.delete("/{document_id}")
async def delete_document(
        document_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """删除文档（从MinIO和数据库中删除"""
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
        # 步骤1：删除Milvus中的向量数据（如果已处理）
        if document.status == "processed" or document.status == "processing":
            try:
                minio_object = None
                if document.meta_data and isinstance(document.meta_data, dict):
                    minio_object = document.meta_data.get("minio_object")

                await unified_processor.delete_document_vectors(
                    document_id=str(document.id),
                    minio_object=minio_object or document.file_path
                )
                logger.info(f"Milvus向量删除成功: {document_id}")
            except Exception as e:
                logger.error(f"删除Milvus向量失败: {str(e)}")

        # 步骤2：从MinIO删除文件
        try:
            # 删除PDF文件本身
            minio_service.delete_file(document.file_path)
            logger.info(f"MinIO文件删除成功: {document.file_path}")

            # 删除PDF提取的图片(如果存在), 图片保存咋documents/{document_id}/images/下
            image_prefix = f"documents/{document.id}/images/"
            try:
                deleted_images = minio_service.delete_directory(image_prefix)
                logger.info(f"MinIO图片目录删除成功: {image_prefix}, 删除了 {deleted_images} 个图片")
            except Exception as e:
                # 图片删除失败不影响主要流程
                logger.warning(f"删除MinIO图片目录失败: {str(e)}")
        except Exception as e:
            logger.error(f"删除MinIO文件失败: {str(e)}")

        # 步骤3：删除数据库记录
        await db.delete(document)
        await db.commit()

        logger.info(f"文档删除成功: {document_id}")

        return {"message": "文档删除成功"}

    except Exception as e:
        logger.error(f"文档删除失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档删除失败: {str(e)}"
        )


@router.post("/{document_id}/process")
async def process_document(
        document_id: str,
        strategy: str = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """处理文档（生成向量嵌入）- 从MinIO下载文件后处理"""
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

    if document.status == "processed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档已处理完成"
        )

    # 创建临时目录用于处理
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    temp_file_path = None

    try:
        # 更新状态为处理中
        document.status = "processing"
        await db.commit()

        # 从MinIO下载文件到临时目录
        temp_file_path = temp_dir / Path(document.filename).name
        minio_service.download_file(
            object_name=document.file_path,
            file_path=str(temp_file_path)
        )
        logger.info(f"文件从MinIO下载成功: {temp_file_path}")

        # 使用统一处理器处理文档
        processed_result = await unified_processor.process_document(
            file_path=str(temp_file_path),
            strategy=strategy or "hybrid",
            metadata={
                'document_id': str(document.id),
                'user_id': str(current_user.id),
                'file_category': document.file_category,
                'title': document.title,
                'minio_object': document.file_path,
                'minio_bucket': settings.MINIO_BUCKET_NAME
            }
        )

        # 更新文档信息
        if processed_result.status.value == "completed":
            document.status = "processed"
            document.total_chunks = processed_result.processing_stats.total_chunks
            document.processed_chunks = processed_result.processing_stats.total_chunks
            # 合并元数据
            existing_meta = document.meta_data or {}
            existing_meta.update(processed_result.metadata)
            document.meta_data = existing_meta
        else:
            document.status = "failed"
            document.processing_error = str(processed_result.processing_stats.errors[0]) if processed_result.processing_stats.errors else "处理失败"

        await db.commit()
        await db.refresh(document)

        logger.info(f"文档处理完成: {document.id}, 状态: {document.status}")

        return {
            "message": "文档处理完成",
            "document_id": str(document.id),
            "status": document.status,
            "total_chunks": document.total_chunks,
            "processing_time": processed_result.processing_stats.processing_time,
            "strategy": strategy or "hybrid"
        }

    except Exception as e:
        document.status = "error"
        document.processing_error = str(e)
        await db.commit()

        logger.error(f"文档处理失败: {document_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档处理失败: {str(e)}"
        )

    finally:
        # 清理临时文件
        if temp_file_path and temp_file_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"临时文件已清理: {temp_dir}")


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