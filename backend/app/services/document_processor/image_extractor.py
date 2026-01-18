"""
图片提取器 - 通用的文档图片提取和上传功能
"""
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass

import logging

from ..storage.minio_service import minio_service

logger = logging.getLogger(__name__)

@dataclass
class ExtractedImageInfo:
    """提取的图片信息"""
    page_num: int
    image_index: int
    image_type: str
    width: int
    height: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    image_url: str  # MinIO URL
    minio_object: str  # MinIO object name

class ImageExtractor:
    """通用图片提取器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化图片提取器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.minio_bucket = minio_service.bucket_name

    def extract_bbox(self, img_obj: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
        """
        从图片对象中提取bbox坐标

        Args:
            img_obj: 图片对象字典

        Returns:
            bbox元组 (x0, y0, x1, y1)，如果无法提取则返回None
        """
        # 检查是否是字典
        if not isinstance(img_obj, dict):
            logger.warning(f"图片对象不是字典类型: {type(img_obj)}")
            return None

        # 尝试从不同字段获取bbox
        if 'bbox' in img_obj:
            return img_obj['bbox']
        elif all(key in img_obj for key in ['x0', 'y0', 'x1', 'y1']):
            # 使用单独的坐标字段
            return img_obj['x0'], img_obj['y0'], img_obj['x1'], img_obj['y1']
        else:
            logger.warning("图片对象缺少bbox或坐标信息")
            return None

    def clip_bbox(
            self,
            bbox: Tuple[float, float, float, float],
            page_bbox: Tuple[float, float, float, float]
    ):
        """
        裁剪bbox，确保在页面范围内

        Args:
            bbox: 原始bbox (x0, y0, x1, y1)
            page_bbox: 页面bbox (x0, y0, x1, y1)

        Returns:
            裁剪后的bbox，如果无效则返回None
        """
        # 裁剪坐标
        x0 = max(page_bbox[0], bbox[0])
        y0 = max(page_bbox[1], bbox[1])
        x1 = min(page_bbox[2], bbox[2])
        y1 = min(page_bbox[3], bbox[3])

        # 确保bbox有效（x0 < x1 且 y0 < y1）
        if x0 >= x1 or y0 >= y1:
            logger.warning(f"裁剪后的bbox无效: ({x0}, {y0}, {x1}, {y1})")
            return None

        clipped_bbox = (x0, y0, x1, y1)
        logger.debug(f"裁剪bbox: {bbox} -> {clipped_bbox}")
        return clipped_bbox

    def extract_image_from_page(
            self,
            page,
            bbox: Tuple[float, float, float, float]
    ) -> bytes:
        """
        从页面中提取指定bbox的图片

        Args:
            page: 页面对象（支持pdfplumber的Page对象）
            bbox: 图片边界框

        Returns:
            图片字节数据
        """
        # 使用within_bbox提取图片
        page_img_obj = page.within_bbox(bbox).to_image()

        # 获取PIL Image对象
        pil_image = page_img_obj.original

        # 转换为字节数据
        img_bytes_io = BytesIO()
        pil_image.save(img_bytes_io, format='PNG')
        return img_bytes_io.getvalue()

    def upload_image_to_minio(
            self,
            image_bytes: bytes,
            document_id: str,
            page_num: int,
            image_index: int,
            file_extension: str = '.png',
            content_type: str = 'image/png'
    ) -> Dict[str, Any]:
        """
        上传图片到MinIO

        Args:
            image_bytes: 图片字节数据
            document_id: 文档ID
            page_num: 页码
            image_index: 图片索引
            file_extension: 文件扩展名
            content_type: 内容类型

        Returns:
            上传结果，包含presigned_url和object_name
        """
        object_name = f"documents/{document_id}/images/page_{page_num}_img_{image_index}{file_extension}"

        upload_result = minio_service.upload_bytes(
            data=image_bytes,
            object_name=object_name,
            length=len(image_bytes),
            content_type=content_type,
            metadata=None
        )

        return upload_result

    def create_image_info(
            self,
            img_obj: Dict[str, Any],
            upload_result: Dict[str, Any],
            page_num: int,
            image_index: int,
            clipped_bbox: Tuple[float, float, float, float]
    ) -> ExtractedImageInfo:
        """
        创建图片信息对象

        Args:
            img_obj: 原始图片对象
            upload_result: MinIO上传结果
            page_num: 页码
            image_index: 图片索引
            clipped_bbox: 裁剪后的bbox

        Returns:
            ExtractedImageInfo对象
        """
        return ExtractedImageInfo(
            page_num=page_num,
            image_index=image_index,
            image_type=img_obj.get('filter', 'Unknown'),
            width=img_obj.get('width', 0),
            height=img_obj.get('height', 0),
            bbox=clipped_bbox,
            image_url=upload_result['presigned_url'],
            minio_object=upload_result['object_name']
        )

    async def extract_images_from_pdf_pages(
            self,
            pdf,
            document_id: str,
            page_start: int = 1
    ) -> Dict[int, List[ExtractedImageInfo]]:
        """
        从PDF页面中提取图片

        Args:
            pdf: pdfplumber打开的PDF对象
            document_id: 文档ID
            page_start: 起始页码

        Returns:
            {page_num: [ExtractedImageInfo]}
        """
        images_by_page = {}

        for page_num, page in enumerate(pdf.pages, page_start):
            page_images = page.images

            if not page_images:
                continue

            page_image_list = []

            for img_index, img in enumerate(page_images):
                try:
                    logger.info(f"处理图片 page_{page_num}_img_{img_index}")

                    # 1. 提取bbox
                    bbox = self.extract_bbox(img)
                    if bbox is None:
                        logger.warning(f"无法提取bbox，跳过图片 page_{page_num}_img_{img_index}")
                        continue

                    logger.info(f"原始bbox: {bbox}")

                    # 2. 裁剪bbox
                    page_bbox = page.bbox  # (0, 0, width, height)
                    clipped_bbox = self.clip_bbox(bbox, page_bbox)

                    if clipped_bbox is None:
                        logger.warning(f"裁剪bbox失败，跳过图片 page_{page_num}_img_{img_index}")
                        continue

                    logger.info(f"裁剪后的bbox: {clipped_bbox}")

                    # 3. 提取图片字节数据
                    image_bytes = self.extract_image_from_page(page, clipped_bbox)

                    # 4. 上传到MinIO
                    upload_result = self.upload_image_to_minio(
                        image_bytes=image_bytes,
                        document_id=document_id,
                        page_num=page_num,
                        image_index=img_index
                    )

                    # 5. 创建图片信息
                    image_info = self.create_image_info(
                        img_obj=img,
                        upload_result=upload_result,
                        page_num=page_num,
                        image_index=img_index,
                        clipped_bbox=clipped_bbox
                    )

                    page_image_list.append(image_info)
                    logger.info(f"成功上传图片: page_{page_num}_img_{img_index}")

                except Exception as e:
                    # 单个图片上传失败，继续处理其他图片
                    logger.warning(f"上传图片失败 page_{page_num}_img_{img_index}: {e}")
                    import traceback
                    logger.warning(f"详细错误信息:\n{traceback.format_exc()}")
                    continue

            if page_image_list:
                images_by_page[page_num] = page_image_list

        return images_by_page

# 全局图片提取器实例
image_extractor = ImageExtractor()