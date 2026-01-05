"""
智能法律助手 - FastAPI后端主应用
"""

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
from .api import auth, conversations, documents, users
from .core.security import get_current_user
from .models.user import User

# 创建FastAPI应用实例
app = FastAPI(
    title="智能法律助手 API",
    description="基于AI技术的智能法律咨询系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# 创建数据库表（开发环境使用）
@app.on_event("startup")
async def startup_event():
    """应用启动时创建数据库表和日志配置"""
    setup_logging()
    """应用启动时创建数据库表"""
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    print("🚀 智能法律助手后端服务启动完成")

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
    return {
        "status": "healthy",
        "timestamp": "2025-01-01T00:00:00Z"
    }

# 注册API路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["对话"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档"])

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