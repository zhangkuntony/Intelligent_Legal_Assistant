"""
MinIO对象存储服务
"""
import logging
from io import BytesIO
from datetime import timedelta

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error
from pathlib import Path
from sympy.physics.units import length
from typing import Optional, Dict, Any

from ...core.config import settings

logger = logging.getLogger(__name__)


class MinIOStorageService:
    """MinIO对象存储服务"""

    def __init__(self):
        """初始化MinIO客户端"""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._initialized = False

    def initialize(self):
        """初始化存储桶"""
        if self._initialized:
            return

        try:
            # 检查存储桶是否存在
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(f"创建MinIO存储桶：{self.bucket_name}")
                self.client.make_bucket(self.bucket_name)
            else:
                logger.info(f"MinIO存储桶已存在：{self.bucket_name}")

            self._initialized = True

        except S3Error as e:
            logger.error(f"MinIO初始化失败:{str(e)}")
            raise

    def upload_file(
            self,
            file_path: str,
            object_name: Optional[str] = None,
            metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        上传文件到MinIO

        Args:
            file_path: 本地文件路径
            object_name: MinIO中的对象名称（如果不提供，使用文件名）
            metadata: 对象元数据

        Returns:
            上传结果，包含对象信息
        """
        self.initialize()

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        # 如果没有提供对象名称，使用文件名
        if not object_name:
            object_name = file_path.name

        try:
            logger.info(f"上传文件到MinIO：{file_path} -> {object_name}")

            # 上传文件
            result = self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=str(file_path),
                metadata=metadata
            )

            logger.info(f"文件上传成功：{object_name}")

            return {
                'bucket_name': self.bucket_name,
                'object_name': object_name,
                'version_id': result.version_id,
                'etag': result.etag,
                'size': length,
                'last_modified': result.last_modified,
                'presigned_url': self.get_presigned_url(object_name)
            }

        except S3Error as e:
            logger.error(f"文件上传失败：{str(e)}")
            raise

    def upload_bytes(
            self,
            data: bytes,
            object_name: str,
            length: int,
            content_type: str = "application/octet-stream",
            metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        上传字节数据到MinIO

        Args:
            data: 字节数据
            object_name: 对象名称
            length: 数据长度
            content_type: 内容类型
            metadata: 元数据

        Returns:
            上传结果
        """
        self.initialize()

        try:
            logger.info(f"上传字节数据到MinIO：{object_name}")
            logger.info(f"Content-Type: {content_type}")
            logger.info(f"Data length: {length}")

            # 创建内存中的文件对象
            data_stream = BytesIO(data)

            # 上传数据
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=length,
                content_type=content_type,
                metadata=metadata
            )

            logger.info(f"数据上传成功：{object_name}")

            return {
                'bucket_name': self.bucket_name,
                'object_name': object_name,
                'version_id': result.version_id,
                'etag': result.etag,
                'size': length,
                'last_modified': result.last_modified,
                'presigned_url': self.get_presigned_url(object_name)
            }

        except S3Error as e:
            logger.error(f"数据上传失败：{str(e)}")
            raise


    def download_file(
            self,
            object_name: str,
            file_path: str,
    ) -> str:
        """
        从MinIO下载文件

        Args:
            object_name: 对象名称
            file_path: 本地保存路径

        Returns:
            下载后的文件路径
        """
        self.initialize()

        try:
            logger.info(f"从MinIO下载文件：{object_name} -> {file_path}")

            # 确保目标目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # 下载文件
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=str(file_path)
            )

            logger.info(f"文件下载成功：{file_path}")
            return file_path

        except S3Error as e:
            logger.error(f"文件下载失败：{str(e)}")
            raise

    def download_bytes(
            self,
            object_name: str
    ) -> bytes:
        """
        从MinIO下载数据为字节

        Args:
            object_name: 对象名称

        Returns:
            字节数据
        """
        self.initialize()

        try:
            logger.info(f"从MinIO下载数据: {object_name}")

            # 下载数据
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            data = response.read()

            logger.info(f"数据下载成功: {len(data)} 字节")
            return data

        except S3Error as e:
            logger.error(f"数据下载失败: {str(e)}")
            raise

    def delete_file(self, object_name: str) -> bool:
        """
        删除MinIO中的文件

        Args:
            object_name: 对象名称

        Returns:
            是否删除成功
        """
        self.initialize()

        try:
            logger.info(f"删除MinIO文件: {object_name}")

            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            logger.info(f"文件删除成功: {object_name}")
            return True

        except S3Error as e:
            logger.error(f"文件删除失败: {str(e)}")
            raise

    def delete_directory(self, prefix: str, recursive: bool = True) -> int:
        """
        删除MinIO中的目录及其内容

        Args:
            prefix: 对象前缀（目录路径）
            recursive: 是否递归删除子目录

        Returns:
            删除的对象数量
        """
        self.initialize()

        try:
            logger.info(f"删除MinIO目录: {prefix}")

            # 列出所有匹配的对象
            objects_list = list(self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=recursive
            ))

            if not objects_list:
                logger.info(f"目录为空或不存在: {prefix}")
                return 0

            # 获取对象列表并创建删除列表
            delete_objects_list = [DeleteObject(obj.object_name) for obj in objects_list]

            # 删除所有对象
            result = self.client.remove_objects(
                bucket_name=self.bucket_name,
                delete_object_list=delete_objects_list
            )

            delete_count = len(list(result))
            logger.info(f"目录删除成功: {prefix}, 删除了 {delete_count} 个对象")

            return delete_count

        except S3Error as e:
            logger.error(f"删除目录失败: {str(e)}")
            raise


    def get_presigned_url(
            self,
            object_name: str,
            expires: int = 3600
    ) -> str:
        """
        生成预签名URL

        Args:
            object_name: 对象名称
            expires: 过期时间（秒）

        Returns:
            预签名URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            logger.error(f"生成预签名URL失败：{str(e)}")
            raise

    def check_file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: 对象名称

        Returns:
            文件是否存在
        """
        self.initialize()

        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise

    def get_file_info(self, object_name: str) -> Dict[str, Any]:
        """
        获取文件信息

        Args:
            object_name: 对象名称

        Returns:
            文件信息
        """
        self.initialize()

        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            return {
                'object_name': object_name,
                'size': stat.size,
                'last_modified': stat.last_modified,
                'etag': stat.etag,
                'content_type': stat.content_type,
                'metadata': stat.metadata
            }

        except S3Error as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            raise

# 全局MinIO服务实例
minio_service = MinIOStorageService()


