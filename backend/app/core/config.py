"""
应用配置管理
"""

from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    APP_NAME: str = "智能法律助手"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, production, testing

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://legal_assistant:legal_assistant_123456@localhost:5432/legal_assistant"

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # 前端开发服务器
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite默认端口
    ]

    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".doc", ".docx", ".txt"]

    # AI服务配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"

    # 向量检索配置
    VECTOR_SEARCH_TOP_K: int = 5  # 检索最相似的5个文档块
    SIMILARITY_THRESHOLD: float = 0.7  # 相似度阈值

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    # Redis配置（可选，用于缓存）
    REDIS_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()

# 环境特定配置
if settings.ENVIRONMENT == "production":
    # 生产环境配置覆盖
    settings.CORS_ORIGINS = [
        "https://your-domain.com"
    ]
    settings.LOG_LEVEL = "WARNING"

    # 确保生产环境有必要的密钥
    if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
        raise ValueError("生产环境必须设置SECRET_KEY")

elif settings.ENVIRONMENT == "testing":
    # 测试环境配置
    settings.DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/legal_assistant_test"
    settings.LOG_LEVEL = "DEBUG"