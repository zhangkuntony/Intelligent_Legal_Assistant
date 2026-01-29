"""
问题理解与分析模型
用于存储和传递问题分析结果
"""

from pydantic import BaseModel, Field
from typing import List

class QuestionAnalysis(BaseModel):
    """问题分析结果

    属性:
        core_issue: 核心问题
        legal_elements: 法律要素列表
        key_entities: 关键实体（人名、地名、机构等）
        query_for_retrieval: 用于检索的优化查询
        missing_info: 缺失信息列表
    """
    core_issue: str = Field(
        ...,
        description="用户问题的核心诉求"
    )
    legal_elements: List[str] = Field(
        default_factory=list,
        description="提取的法律要素，如：主体、客体、权利义务等"
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="关键实体，如人名、地名、机构名、时间等"
    )
    query_for_retrieval: str = Field(
        ...,
        description="优化的检索查询字符串"
    )
    missing_info: List[str] = Field(
        default_factory=list,
        description="缺失的信息，需要向用户确认"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "core_issue": "劳动合同解除的经济补偿问题",
                "legal_elements": ["劳动合同", "解除", "经济补偿", "工作年限"],
                "key_entities": ["劳动合同", "用人单位", "劳动者"],
                "query_for_retrieval": "劳动合同解除 经济补偿 法律规定 工作年限计算",
                "missing_info": ["解除合同的具体原因", "工作年限"]
            }
        }

class EntityExtraction(BaseModel):
    """实体提取结果"""
    entity_type: str = Field(..., description="实体类型，如：人名、地名、机构名等")
    entity_value: str = Field(..., description="实体值")
    confidence: float = Field(..., ge=0.0, le=1.0, description="提取置信度")