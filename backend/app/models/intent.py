"""
意图分类数据模型
用于存储和传递意图识别结果
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class IntentClassification(BaseModel):
    """意图分类结果

    属性:
        is_legal_related: 是否为法律相关问题
        legal_category: 法律领域（民事、刑事、商事等）
        confidence: 置信度 (0-1)
        suggested_topics: 建议的相关话题列表
    """
    is_legal_related: bool = Field(
        ...,
        description="用户输入是否为法律相关问题"
    )
    legal_category: Optional[str] = Field(
        None,
        description="法律领域分类，如：民事、刑事、行政、知识产权等"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="分类置信度，范围0-1"
    )
    suggested_topics: List[str] = Field(
        default_factory=list,
        description="建议的相关法律话题"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "is_legal_related": True,
                "legal_category": "民事",
                "confidence": 0.92,
                "suggested_topics": ["劳动合同", "解除合同", "经济补偿"]
            }
        }

# 法律领域常量
LEGAL_CATEGORIES = {
    "civil": "民事",
    "criminal": "刑事",
    "commercial": "商事",
    "administrative": "行政",
    "intellectual_property": "知识产权",
    "labor": "劳动",
    "family": "婚姻家庭",
    "real_estate": "房地产",
    "tort": "侵权",
    "contract": "合同",
    "other": "其他"
}