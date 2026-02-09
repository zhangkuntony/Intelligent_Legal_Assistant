"""
文档类型管理API路由
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..core.database import get_db
from ..models.document import Document
from ..models.document_category import DocumentCategory

router = APIRouter()

# 临时下载令牌存储
_download_tokens = {}

@router.get("")
async def get_document_categories(
        db: AsyncSession = Depends(get_db)
):
    print("get document categories")
    # 1. 查询所有分类
    categories_result = await db.execute(
        select(DocumentCategory)
    )
    document_categories = categories_result.scalars().all()

    # 2. 统计每个分类的文档数量
    # 通过 documents.file_category 与 document_category.category_name 匹配
    document_counts_result = await db.execute(
        select(
            Document.file_category,
            func.count(Document.id).label('count')
        )
        .group_by(Document.file_category)
    )

    # 将统计结果转换为字典 {分类名称: 文档数量}
    count_dict = { row.file_category: row.count for row in document_counts_result }

    # 3. 组装返回数据
    return {
        "success": True,
        "data": {
            "document_categories": [
                {
                    "id": str(category.id),
                    "category_name": category.category_name,
                    "category_code": category.category_code,
                    "description": category.description,
                    "document_count": count_dict.get(category.category_code, 0),  # 根据category_name统计
                    "created_at": category.created_at,
                    "updated_at": category.updated_at
                }
                for category in document_categories
            ]
        }
    }