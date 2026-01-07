"""
文档处理服务 - 与现有API集成
"""

import os
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .base_processor import ProcessedDocument
from .processor_factory import DocumentProcessorFactory, ProcessorConfig
from .batch_processor import BatchProcessor
from .document_cache import DocumentCache
from .processing_monitor import ProcessingMonitor
from ...models.document import Document, DocumentEmbedding


class DocumentProcessorService:
    """文档处理服务（与现有API集成）"""

    def __init__(self, db_session: AsyncSession, config: Dict[str, Any] = None):
        self.db = db_session
        self.config = config or {}

        # 初始化组件
        self.processor_factory = DocumentProcessorFactory
        self.batch_processor = BatchProcessor(config)
        self.document_cache = DocumentCache(
            cache_dir=self.config.get('cache_dir'),
            ttl=self.config.get('cache_ttl', 3600)
        )
        self.processing_monitor = ProcessingMonitor(
            log_file=self.config.get('log_file'),
            enable_console_log=self.config.get('enable_console_log', True)
        )

    async def process_document(self, document_id: str) -> ProcessedDocument:
        """处理文档"""
        # 从数据库获取文档信息
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"文档不存在: {document_id}")

        # 检查文档状态
        if document.status == 'processing':
            raise ValueError("文档正在处理中")

        if document.status == 'completed':
            # 如果文档已处理完成，直接返回缓存结果
            cached_result = await self.document_cache.get_cached_result(document.file_path)
            if cached_result:
                return cached_result

        # 更新文档状态为处理中
        document.status = 'processing'
        await self.db.commit()

        try:
            # 记录处理开始
            self.processing_monitor.log_processing_start(
                document.file_path,
                {'document_id': str(document.id), 'title': document.title}
            )

            # 创建适合的处理器
            processor = self.processor_factory.create_processor(
                file_path=document.file_path,
                config=self.config
            )

            # 处理文档
            result = await processor.process_file(document.file_path)

            # 缓存处理结果
            await self.document_cache.cache_result(document.file_path, result)

            # 更新数据库
            await self._update_document_after_processing(document, result)

            # 记录处理完成
            self.processing_monitor.log_processing_end(document.file_path, result.processing_stats)

            return result

        except Exception as e:
            # 处理失败
            await self._handle_processing_error(document, str(e))
            self.processing_monitor.log_error(document.file_path, e)
            raise

    async def process_document_batch(self, document_ids: list) -> Dict[str, Any]:
        """批量处理文档"""
        # 获取文档信息
        documents = []
        file_paths = []

        for doc_id in document_ids:
            result = await self.db.execute(
                select(Document).where(Document.id == doc_id)
            )
            document = result.scalar_one_or_none()

            if document:
                documents.append(document)
                file_paths.append(document.file_path)

        if not documents:
            return {'success': False, 'message': '没有找到有效的文档'}

        # 更新文档状态
        for document in documents:
            document.status = 'processing'
        await self.db.commit()

        try:
            # 批量处理
            results = await self.batch_processor.process_batch(
                file_paths,
                progress_callback=self._batch_progress_callback
            )

            # 更新数据库
            successful_docs = []
            failed_docs = []

            for document, result in zip(documents, results):
                if result.status.value == 'completed':
                    await self._update_document_after_processing(document, result)
                    successful_docs.append(document)
                else:
                    await self._handle_processing_error(
                        document,
                        result.processing_stats.errors[0] if result.processing_stats.errors else 'Unknown error'
                    )
                    failed_docs.append(document)

            # 获取统计信息
            stats = self.batch_processor.get_processing_stats(results)

            return {
                'success': True,
                'total_documents': len(documents),
                'successful_documents': len(successful_docs),
                'failed_documents': len(failed_docs),
                'stats': stats
            }

        except Exception as e:
            # 批量处理失败
            for document in documents:
                await self._handle_processing_error(document, str(e))

            return {
                'success': False,
                'message': f'批量处理失败: {str(e)}',
                'total_documents': len(documents),
                'successful_documents': 0,
                'failed_documents': len(documents)
            }

    async def _update_document_after_processing(self, document: Document, result: ProcessedDocument):
        """处理完成后更新文档"""
        # 更新文档状态
        document.status = 'completed'
        document.total_chunks = len(result.chunks)
        document.processed_chunks = len(result.chunks)

        # 保存元数据
        if result.metadata:
            document.meta_data = result.metadata

        # 创建向量嵌入记录
        for chunk in result.chunks:
            embedding = DocumentEmbedding(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                chunk_content=chunk.content,
                meta_data=chunk.metadata
            )
            self.db.add(embedding)

        await self.db.commit()

    async def _handle_processing_error(self, document: Document, error_message: str):
        """处理错误"""
        document.status = 'failed'
        document.processing_error = error_message
        await self.db.commit()

    async def _batch_progress_callback(self, processed: int, total: int, file_path: str,
                                       status: str, failed_files: list):
        """批量处理进度回调"""
        # 可以在这里实现进度通知、日志记录等
        progress_percent = (processed / total) * 100

        self.processing_monitor.log_progress(
            file_path,
            progress_percent / 100,
            f"已处理 {processed}/{total} 个文件"
        )

    async def get_processing_summary(self) -> Dict[str, Any]:
        """获取处理摘要"""
        return self.processing_monitor.get_processing_summary()

    async def clear_cache(self) -> Dict[str, Any]:
        """清理缓存"""
        expired_count = await self.document_cache.clear_expired_cache()
        all_count = await self.document_cache.clear_all_cache()

        return {
            'expired_files_cleared': expired_count,
            'all_files_cleared': all_count
        }

    async def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的文件格式"""
        return self.processor_factory.get_supported_formats()

    async def validate_document(self, document_id: str) -> Dict[str, Any]:
        """验证文档"""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            return {'valid': False, 'errors': ['文档不存在']}

        # 检查文件是否存在
        if not os.path.exists(document.file_path):
            return {'valid': False, 'errors': ['文件不存在']}

        # 检查文件格式支持
        if not self.processor_factory.is_format_supported(document.file_path):
            return {'valid': False, 'errors': ['不支持的文件格式']}

        # 检查文件大小
        file_size = os.path.getsize(document.file_path)
        max_size = self.config.get('max_file_size', 50 * 1024 * 1024)

        if file_size > max_size:
            return {
                'valid': False,
                'errors': [f'文件大小超过限制 ({file_size} > {max_size})']
            }

        return {
            'valid': True,
            'file_path': document.file_path,
            'file_size': file_size,
            'file_type': document.file_type
        }


# 使用示例
async def example_usage():
    """使用示例"""
    from ...core.database import AsyncSessionLocal

    # 配置
    config = ProcessorConfig(
        default_chunk_size=1000,
        default_overlap=100,
        max_file_size=50 * 1024 * 1024,
        enable_cache=True,
        cache_ttl=3600
    ).to_dict()

    async with AsyncSessionLocal() as session:
        # 创建服务实例
        service = DocumentProcessorService(session, config)

        # 处理单个文档
        try:
            result = await service.process_document("document_id_here")
            print(f"处理完成: {result.status}")
            print(f"总字符数: {len(result.extracted_text)}")
            print(f"总分块数: {len(result.chunks)}")

        except Exception as e:
            print(f"处理失败: {str(e)}")

        # 批量处理
        batch_result = await service.process_document_batch(["doc1", "doc2", "doc3"])
        print(f"批量处理结果: {batch_result}")

        # 获取处理摘要
        summary = await service.get_processing_summary()
        print(f"处理摘要: {summary}")

        # 获取支持的文件格式
        formats = await service.get_supported_formats()
        print(f"支持的文件格式: {formats}")