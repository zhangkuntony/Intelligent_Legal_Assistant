"""
智能法律助手 - FastAPI后端主应用
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
import logging.config
from pathlib import Path

from .core.config import settings
from .core.database import engine, Base
from .api.auth import router as auth_router
from .api.users import router as users_router
from .api.conversations import router as conversations_router
from .api.document_categories import router as document_categories_router
from .api.documents import router as documents_router
from .core.security import get_current_user
from .models.user import User

# 配置日志系统
def setup_logging():
    """设置应用日志配置"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 创建日志目录
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # 日志配置字典
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': log_level,
                'class': 'logging.FileHandler',
                'formatter': 'standard',
                'filename': str(log_file),
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': True
            },
            'app': {  # 应用特定logger
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False
            }
        }
    }

    logging.config.dictConfig(logging_config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    setup_logging()
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # 注册API路由
    app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
    app.include_router(users_router, prefix="/api/users", tags=["用户"])
    app.include_router(conversations_router, prefix="/api/conversations", tags=["对话"])
    app.include_router(document_categories_router, prefix="/api/document-categories", tags=["文档分类"])
    app.include_router(documents_router, prefix="/api/documents", tags=["文档"])

    print("🚀 智能法律助手后端服务启动完成")
    yield
    # 关闭时执行（如果有需要清理的资源）

# 创建FastAPI应用实例
app = FastAPI(
    title="智能法律助手 API",
    description="基于AI技术的智能法律咨询系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan           # 添加生命周期
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查端点
@app.get("/")
async def root():
    """根端点，返回服务状态"""
    return {
        "message": "智能法律助手 API 服务运行中",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    print("health check")
    logging.info("health check log")
    return {
        "status": "healthy",
        "timestamp": "2025-01-01T00:00:00Z"
    }

# 受保护的示例端点
@app.get("/api/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """需要认证的受保护端点示例"""
    return {
        "message": "这是一个受保护的端点",
        "user": {
            "username": current_user.username,
            "email": current_user.email
        }
    }

# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常统一处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "code": exc.status_code
        }
    )

# 全局异常处理
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.ENVIRONMENT == "development" else None
        }
    )

#确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# 创建安全的静态文件服务
class SecureStaticFiles(StaticFiles):
    """安全的静态文件服务，防止目录遍历攻击"""

    async def get_response(self, path: str, scope):
        # 验证路径安全性
        if ".." in path or path.startswith("/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="非法文件路径")
        return await super().get_response(path, scope)

# 挂载安全静态文件服务
app.mount("/api/uploads", SecureStaticFiles(directory=settings.UPLOAD_DIR), name="secure_uploads")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )