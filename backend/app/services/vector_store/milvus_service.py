"""
Milvus向量数据库服务
"""
import logging
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)

from ...core.config import settings

logger = logging.getLogger(__name__)

class MilvusVectorStore:
    """Milvus向量数据库服务"""

    def __init__(self):
        """初始化Milvus连接"""
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = settings.MILVUS_DIMENSION
        self._initialized = False
        self.collection = None

    def initialize(self):
        """初始化Milvus连接和集合"""
        if self._initialized:
            return

        try:
            # 连接到Milvus
            logger.info(f"连接到Milvus:{self.host}:{self.port}")
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )

            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                logger.info(f"集合已存在：{self.collection_name}")
                self.collection = Collection(self.collection_name)
            else:
                logger.info(f"创建新集合：{self.collection_name}")
                self._create_collection()

            self._initialized = True
            logger.info("Milvus初始化成功")

        except Exception as e:
            logger.error(f"Milvus初始化失败：{str(e)}")
            raise

    def _create_collection(self):
        """创建集合"""
        try:
            # 定义集合字段
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
            ]

            # 创建集合schema
            schema = CollectionSchema(fields=fields, description="法律文档向量存储")

            # 创建集合
            self.collection = Collection(self.collection_name, schema=schema)

            # 创建索引
            index_params = {
                "metric_type": "IP",            # 内积
                "index_type": "HNSW",
                "params": {
                    "M": 16,
                    "efConstruction": 256
                }
            }

            self.collection.create_index(
                field_name="embedding",
                index_params=index_params,
            )

            logger.info(f"集合创建成功：{self.collection_name}")

        except Exception as e:
            logger.error(f"创建集合失败：{str(e)}")
            raise

    def insert_embeddings(
            self,
            embeddings: List[List[float]],
            contents: List[str],
            document_id: str,
            chunk_indices: List[int],
            metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        插入向量嵌入

        Args:
            embeddings: 向量列表
            contents: 内容列表
            document_id: 文档ID
            chunk_indices: 分块索引列表
            metadata: 元数据列表

        Returns:
            插入的ID列表
        """
        self.initialize()

        if len(embeddings) != len(contents) or len(embeddings) != len(chunk_indices):
            raise ValueError("embeddings, contents和chunk_indices长度必须一致")

        try:
            # 准备数据
            ids = []
            data = {
                "document_id": [document_id] * len(embeddings),
                "chunk_index": chunk_indices,
                "content": contents,
                "embedding": embeddings,
            }

            # 生成唯一ID
            for i in range(len(embeddings)):
                chunk_id = f"{document_id}_{chunk_indices[i]}"
                ids.append(chunk_id)

            data["id"] = ids

            # 添加元数据
            if metadata:
                data["metadata"] = metadata
            else:
                data["metadata"] = [{} for _ in range(len(embeddings))]

            # 插入数据
            logger.info(f"插入{len(embeddings)}个向量到Milvus")
            insert_result = self.collection.insert(data)

            # 刷新以确保数据持久化
            self.collection.flush()

            logger.info(f"向量插入成功：{len(ids)}个")
            logger.info(f"插入向量：{insert_result}")
            return ids

        except Exception as e:
            logger.error(f"插入向量失败:{str(e)}")
            raise

    def search_similar(
            self,
            query_embedding: List[float],
            top_k: int = 5,
            document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量

        Args:
            query_embedding: 查询向量
            top_k: 返回前K个结果
            document_id: 限制在特定文档中搜索

        Returns:
            相似结果列表
        """
        self.initialize()

        try:
            # 加载集合到内存
            self.collection.load()

            # 构建搜索表达式
            expr = None
            if document_id:
                expr = f'document_id == "{document_id}"'

            # 搜索参数
            search_params = {
                "metric_type": "IP",
                "params": {
                    "ef": 128           # 搜索时使用的参数
                }
            }

            # 执行搜索
            logger.info(f"搜索相似向量：top_k={top_k}")

            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["id", "document_id", "chunk_index", "content", "content", "metadata"]
            )

            # 处理结果
            search_results = []
            for result in results[0]:
                search_results.append({
                    "id": result.id,
                    "document_id": result.entity.get("document_id"),
                    "chunk_index": result.entity.get("chunk_index"),
                    "content": result.entity.get("content"),
                    "metadata": result.entity.get("metadata"),
                    "score": result.score
                })

            logger.info(f"搜索完成：找到{len(search_results)}个结果")
            return search_results

        except Exception as e:
            logger.error(f"搜索向量失败：{str(e)}")
            raise

    def delete_by_document(self, document_id: str) -> int:
        """
        删除指定文档的所有向量

        Args:
            document_id: 文档ID

        Returns:
            删除的向量数量
        """
        self.initialize()

        try:
            # 构建删除表达式
            expr = f'document_id == "{document_id}"'

            # 执行删除
            logger.info(f"删除文档向量: document_id={document_id}")

            self.collection.delete(expr)
            self.collection.flush()

            logger.info(f"向量删除成功: document_id={document_id}")
            return 0  # Milvus不返回删除数量

        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息
        """
        self.initialize()

        try:
            stats = self.collection.describe()
            num_entities = self.collection.num_entities

            return {
                "collection_name": self.collection_name,
                "num_entities": num_entities,
                "description": stats.get("description", ""),
                "fields": stats.get("fields", [])
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            raise


# 全局Milvus服务实例
milvus_store = MilvusVectorStore()




