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

            # 1.5 提取并上传图片
            logger.info("提取并上传图片")
            document_id = metadata.get('document_id') if metadata else None
            images_by_page = {}

            if hasattr(processor, 'extract_images_with_upload') and document_id:
                images_by_page = await processor.extract_images_with_upload(file_path, document_id)
                logger.info(f"提取到 {sum(len(imgs) for imgs in images_by_page.values())} 张图片")
            else:
                logger.info("当前处理器不支持图片提取或未提供document_id")

            # 2. 预处理文本
            logger.info("步骤2：预处理文本")
            preprocessed_text = await processor.preprocess_text(extracted_text)

            # 3. 分块处理（传递图片信息）
            logger.info("步骤3：分块处理")

            # 将图片信息添加到metadata中
            chunk_metadata = metadata.copy() if metadata else {}
            if images_by_page:
                chunk_metadata['images_by_page'] = images_by_page
                chunk_metadata['has_images'] = True
            else:
                chunk_metadata['has_images'] = False

            chunks = await self.chunker_adapter.chunk_document(
                text=preprocessed_text,
                strategy=strategy or self.config.get('default_strategy', 'hybrid'),
                metadata=chunk_metadata
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
            model_name = settings.EMBEDDING_MODEL
            logger.info(f"使用embedding模型: {model_name}")
            logger.info(f"要处理文本数量: {len(chunks)}")

            embeddings = []

            # 为每个chunk单独生成embedding
            for idx, chunk in enumerate(chunks):
                # 构造文本输入对象
                text_input = {
                    "text": chunk.content,
                    "type": "text"
                }

                inputs = [text_input]

                # 检查是否有图片信息（从metadata中）
                if chunk.metadata and 'image_url' in chunk.metadata:
                    # 为每张图片添加image_url输入
                    for image_url in chunk.metadata['image_urls']:
                        inputs.append({
                            "image_url": {"url": image_url},
                            "type": "image_url"
                        })

                logger.info(f"处理第{idx + 1}/{len(chunks)}个chunk，输入数量: {len(inputs)}")

                # 调用embedding API（为每个chunk单独调用）
                resp = self.ark_client.multimodal_embeddings.create(
                    model=model_name,
                    input=inputs
                )

                # 将结果添加到embedding列表
                embedding = resp.data.embedding
                embeddings.append(embedding)
                logger.info(f"第{idx + 1}个chunk的embedding维度: {len(embedding)}")

            logger.info(f"成功生成 {len(embeddings)} 个向量")
            return embeddings
        except Exception as e:
            logger.error(f"生成嵌入失败：{str(e)}")
            logger.error(f"当前使用的模型: {self.config.get('embedding_model')}")
            logger.error(f"输入数量: {len(chunks)}")
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

            # 将向量嵌入存储到Milvus
            logger.info(f"存储{len(embeddings)}个向量到Milvus")

            # 准备数据
            contents = [chunk.content for chunk in chunks]
            chunk_indices = [chunk.chunk_index for chunk in chunks]
            chunk_metadata = [chunk.metadata for chunk in chunks]

            # 插入向量
            inserted_ids = milvus_store.insert_embeddings(
                embeddings=embeddings,
                contents=contents,
                document_id=document_id,
                chunk_indices=chunk_indices,
                metadata=chunk_metadata
            )

            logger.info(f"向量存储成功：{len(inserted_ids)}个")

            # 更新元数据，包含MinIO对象信息
            metadata.update({
                'milvus_collection': self.config.get('collection_name', 'legal_documents'),
                'vector_count': len(embeddings),
            })

            # 如果metadata中包含MinIO信息，记录到日志
            if 'minio_object' in metadata:
                logger.info(f"MinIO对象: {metadata.get('minio_bucket', 'unknown')}/{metadata['minio_object']}")

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
            milvus_store.delete_by_document(document_id)

            # 从MinIO删除文件
            if minio_object:
                minio_service.delete_file(minio_object)

            logger.info(f"文档向量删除成功: document_id={document_id}")

        except Exception as e:
            logger.error(f"删除文档向量失败: {str(e)}")
            raise

    def get_available_strategies(self) -> List[str]:
        """获取可用的分块策略"""
        return self.chunker_adapter.get_available_strategies()