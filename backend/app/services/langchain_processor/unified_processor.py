"""
统一文档处理器 - 协调LangChain和现有文档处理流程
"""
from pathlib import Path
from typing import Dict, Any, List
import logging
from datetime import datetime

from volcenginesdkarkruntime import Ark
from .chunker_adapter import ChunkerAdapter
from ..document_processor.base_processor import DocumentChunk, ProcessedDocument, ProcessingStats, ProcessingStatus
from ..document_processor.processor_factory import DocumentProcessorFactory
from ...core.config import settings
from ...core.langchain_config import default_langchain_config
from ..storage.minio_service import minio_service
from ..vector_store.milvus_service import milvus_store

logger = logging.getLogger(__name__)

class UnifiedDocumentProcessor:
    """统一文档处理器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化统一处理器

        Args:
            config: 配置字典
        """
        self.config = config or default_langchain_config.to_dict()

        # 初始化分块器适配器
        self.chunker_adapter = ChunkerAdapter(self.config)

        logger.info(f"Config: {self.config}")
        logger.info(f"API Key: {self.config.get('api_key')}" )

        # 初始化嵌入模型
        self.ark_client = Ark(api_key=settings.LLM_API_KEY)

        # 初始化文档处理器工厂
        self.processor_factory = DocumentProcessorFactory

        # 向量存储（将在需要时初始化）
        self.vector_store = None

    async def process_document(
            self,
            file_path: str,
            strategy: str = None,
            metadata: Dict[str, Any] = None
    ) -> ProcessedDocument:
        """
        处理文档的完整流程

        Args:
            file_path: 文件路径
            strategy: 分块策略
            metadata: 文档元数据

        Returns:
            处理后的文档
        """
        start_time = datetime.now()
        logger.info(f"开始处理文档：{file_path}")

        try:
            # 1. 提取文本
            logger.info("步骤1：提取文本")
            processor = self.processor_factory.create_processor(
                file_path=file_path,
                config=self.config
            )

            extracted_text = await processor.extract_text(file_path)

            # 2. 预处理文本
            logger.info("步骤2：预处理文本")
            preprocessed_text = await processor.preprocess_text(extracted_text)

            # 3. 分块处理
            logger.info("步骤3：分块处理")
            chunks = await self.chunker_adapter.chunk_document(
                text=preprocessed_text,
                strategy=strategy or self.config.get('default_strategy', 'hybrid'),
                metadata=metadata or {}
            )

            # 4. 生成向量嵌入
            logger.info("步骤4：生成向量嵌入")
            embeddings = await self._generate_embeddings(chunks)

            # 5. 存储到向量数据库
            logger.info("步骤5：存储向量")
            await self._store_vectors(file_path, chunks, embeddings, metadata)

            # 6. 创建处理结果
            processing_stats = ProcessingStats(
                start_time=start_time,
                end_time=datetime.now(),
                total_chars=len(extracted_text),
                total_chunks=len(chunks)
            )

            result = ProcessedDocument(
                original_path=file_path,
                extracted_text=extracted_text,
                chunks=chunks,
                metadata=metadata or {},
                processing_stats=processing_stats,
                status=ProcessingStatus.COMPLETED
            )

            logger.info(f"文档处理完成：{file_path}，共生成{len(chunks)}个分块")
            return result

        except Exception as e:
            logger.error(f"文档处理失败: {file_path}, 错误: {str(e)}")
            processing_stats = ProcessingStats(
                start_time=start_time,
                end_time=datetime.now(),
                errors=[str(e)]
            )

            return ProcessedDocument(
                original_path=file_path,
                extracted_text="",
                chunks=[],
                metadata={},
                processing_stats=processing_stats,
                status=ProcessingStatus.FAILED
            )

    async def _generate_embeddings(self, chunks: List[DocumentChunk]) -> List[List[float]]:
        """
        生成向量嵌入

        Args:
            chunks: 文档分块列表

        Returns:
            向量列表
        """
        try:
            # 批量生成嵌入
            texts = [chunk.content for chunk in chunks]
            resp = self.ark_client.embeddings.create(
                model=self.config.get('embedding_model', 'doubao-embedding-text-240715'),
                input=texts,
            )

            embeddings = [item.embedding for item in resp.data]
            return embeddings
        except Exception as e:
            logger.error(f"生成嵌入失败：{str(e)}")
            raise

    async def _store_vectors(
            self,
            file_path: str,
            chunks: List[DocumentChunk],
            embeddings: List[List[float]],
            metadata: Dict[str, Any]
    ):
        """
        存储向量到Milvus并上传文件到MinIO

        Args:
            file_path: 文件路径
            chunks: 文档分块
            embeddings: 向量列表
            metadata: 元数据
        """
        try:
            document_id = metadata.get("document_id")
            if not document_id:
                raise ValueError("元数据中必须包含document_id")

            # 步骤1：上传源文件到MinIO
            logger.info(f"上传源文件到MinIO：{file_path}")

            file_path_obj = Path(file_path)
            object_name = f"documents/{document_id}/{file_path_obj.name}"

            # 上传文件到MinIO
            upload_result = await minio_service.upload(
                file_path=file_path,
                object_name=object_name,
                metadata={
                    'document_id': document_id,
                    'title': metadata.get('title', ''),
                    'file_category': metadata.get('file_category', ''),
                }
            )
            logger.info(f"文件上传成功：{upload_result['object_name']}")

            # 步骤2：将向量嵌入存储到Milvus
            logger.info(f"存储{len(embeddings)}个向量到Milvus")

            # 准备数据
            contents = [chunk.content for chunk in chunks]
            chunk_indices = [chunk.chunk_index for chunk in chunks]
            chunk_metadata = [chunk.metadata for chunk in chunks]

            # 插入向量
            inserted_ids = await milvus_store.insert_documents(
                embeddings=embeddings,
                contents=contents,
                document_id=document_id,
                chunk_indices=chunk_indices,
                metadata=chunk_metadata
            )

            logger.info(f"向量存储成功：{len(inserted_ids)}个")

            # 步骤3：更新元数据，包含MinIO对象信息
            metadata.update({
                'minio_bucket': upload_result['bucket_name'],
                'minio_object': upload_result['object_name'],
                'minio_etag': upload_result['etag'],
                'milvus_collection': self.config.get('collection_name', 'legal_documents'),
                'vector_count': len(embeddings),
            })

            logger.info("向量存储和文件上传完成")

        except Exception as e:
            logger.error(f"存储向量失败: {str(e)}")
            raise

    def search_similar_chunks(
            self,
            query: str,
            top_k: int = None,
            threshold: float = None,
            document_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似的分块

        Args:
            query: 查询文本
            top_k: 返回前K个结果
            threshold: 相似度阈值
            document_id: 限制在特定文档中搜索

        Returns:
            相似分块列表
        """
        top_k = top_k or self.config.get('similarity_top_k', 5)
        threshold = threshold or self.config.get('similarity_threshold', 0.6)

        try:
            # 使用豆包SDK生成查询嵌入
            resp = self.ark_client.embeddings.create(
                model=self.config.get('embedding_model', 'doubao-embedding-text-240715'),
                input=[query]
            )
            query_embedding = resp.data[0].embedding

            # 在Milvus中搜索
            logger.info(f"搜索相似分块：query={query}, top_k={top_k}")

            results = milvus_store.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                document_id=document_id
            )

            # 过滤低于阈值的结果
            filtered_results = [
                {
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'document_id': result['document_id'],
                    'chunk_index': result['chunk_index'],
                    'score': result['score'],
                    'strategy': 'vector'
                } for result in results
                if result['score'] >= threshold
            ]

            logger.info(f"搜索完成：找到{len(filtered_results)}个结果")
            return filtered_results

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise

    async def delete_document_vectors(self, document_id: str, minio_object: str = None):
        """
        删除文档的向量数据

        Args:
            document_id: 文档ID
            minio_object: MinIO对象名称（可选）
        """
        try:
            logger.info(f"删除文档向量: document_id={document_id}")

            # 从Milvus删除向量
            await milvus_store.delete_by_document(document_id)

            # 从MinIO删除文件
            if minio_object:
                await minio_service.delete_file(minio_object)

            logger.info(f"文档向量删除成功: document_id={document_id}")

        except Exception as e:
            logger.error(f"删除文档向量失败: {str(e)}")
            raise

    def get_available_strategies(self) -> List[str]:
        """获取可用的分块策略"""
        return self.chunker_adapter.get_available_strategies()