# 项目详细结构设计

## 后端服务架构 (backend/)

### 核心目录结构
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── config.py              # 配置文件
│   ├── api/                   # API路由层
│   │   ├── __init__.py
│   │   ├── auth.py            # 认证相关API
│   │   ├── conversations.py   # 对话相关API
│   │   ├── documents.py       # 文档管理API
│   │   └── users.py           # 用户管理API
│   ├── core/                  # 核心组件
│   │   ├── __init__.py
│   │   ├── auth.py            # 认证逻辑
│   │   ├── database.py        # 数据库连接
│   │   ├── security.py        # 安全相关
│   │   └── settings.py        # 应用设置
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py            # 用户模型
│   │   ├── conversation.py    # 对话模型
│   │   ├── message.py         # 消息模型
│   │   └── document.py        # 文档模型
│   ├── schemas/               # Pydantic模型
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── document.py
│   ├── services/              # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py    # 认证服务
│   │   ├── conversation_service.py
│   │   ├── document_service.py
│   │   ├── rag_service.py     # RAG核心服务
│   │   └── ai_service.py      # AI集成服务
│   ├── utils/                 # 工具函数
│   │   ├── __init__.py
│   │   ├── file_processor.py  # 文件处理
│   │   ├── embedding.py       # 向量化工具
│   │   └── logger.py          # 日志工具
│   └── dependencies.py        # 依赖注入
├── tests/                     # 测试文件
│   ├── __init__.py
│   ├── test_api.py
│   └── test_services.py
├── requirements.txt           # Python依赖
├── Dockerfile                # Docker配置
└── alembic/                  # 数据库迁移
    ├── env.py
    ├── script.py.mako
    └── versions/
```

## 前端应用架构 (frontend/)

### 核心目录结构
```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── main.ts               # 应用入口
│   ├── App.vue               # 根组件
│   ├── router/               # 路由配置
│   │   ├── index.ts
│   │   └── routes.ts
│   ├── stores/               # 状态管理 (Pinia)
│   │   ├── index.ts
│   │   ├── auth.ts           # 认证状态
│   │   ├── conversation.ts   # 对话状态
│   │   └── document.ts       # 文档状态
│   ├── services/             # API服务
│   │   ├── api.ts            # Axios配置
│   │   ├── auth.ts           # 认证API
│   │   ├── conversation.ts   # 对话API
│   │   └── document.ts       # 文档API
│   ├── components/           # 通用组件
│   │   ├── common/           # 基础组件
│   │   │   ├── Layout.vue
│   │   │   ├── Header.vue
│   │   │   └── Sidebar.vue
│   │   ├── auth/             # 认证相关组件
│   │   │   ├── LoginForm.vue
│   │   │   └── RegisterForm.vue
│   │   ├── chat/             # 聊天相关组件
│   │   │   ├── ChatWindow.vue
│   │   │   ├── MessageList.vue
│   │   │   └── MessageInput.vue
│   │   └── document/         # 文档相关组件
│   │       ├── DocumentList.vue
│   │       ├── UploadModal.vue
│   │       └── SearchBox.vue
│   ├── views/                # 页面组件
│   │   ├── Login.vue         # 登录页
│   │   ├── Dashboard.vue     # 仪表板
│   │   ├── Chat.vue          # 聊天页
│   │   ├── Documents.vue     # 文档管理页
│   │   └── History.vue       # 历史记录页
│   ├── types/                # TypeScript类型定义
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── conversation.ts
│   │   └── document.ts
│   ├── utils/                # 工具函数
│   │   ├── request.ts        # HTTP请求封装
│   │   ├── storage.ts        # 本地存储
│   │   └── validation.ts     # 表单验证
│   └── assets/               # 静态资源
│       ├── styles/
│       └── images/
├── package.json
├── vite.config.ts           # Vite配置
├── tsconfig.json           # TypeScript配置
└── Dockerfile
```

## 数据库设计 (database/)

### 表结构设计
```
database/
├── migrations/              # 数据库迁移脚本
│   ├── 001_init_tables.sql
│   ├── 002_add_vector_extension.sql
│   └── 003_seed_data.sql
├── init.sql                # 数据库初始化脚本
├── schema.sql             # 完整表结构定义
└── seed_data.sql          # 测试数据
```

### 核心数据表
1. **users** - 用户表
2. **conversations** - 对话会话表
3. **messages** - 消息记录表
4. **documents** - 文档元数据表
5. **document_embeddings** - 文档向量表 (pgvector)

## 配置和部署文件

### Docker配置
```
├── docker-compose.yml      # 开发环境Docker编排
├── docker-compose.prod.yml # 生产环境编排
├── nginx/
│   ├── nginx.conf          # Nginx配置
│   └── ssl/                # SSL证书
└── .env.example           # 环境变量模板
```

## 文档目录 (docs/)

```
docs/
├── api/                    # API文档
│   ├── auth-api.md
│   ├── conversation-api.md
│   └── document-api.md
├── deployment/             # 部署文档
│   ├── local-setup.md
│   ├── docker-deployment.md
│   └── production.md
├── development/            # 开发文档
│   ├── backend-guide.md
│   ├── frontend-guide.md
│   └── database-guide.md
└── architecture/           # 架构文档
    ├── system-design.md
    ├── database-design.md
    └── api-design.md
```

## 关键文件说明

### 后端核心文件
- `backend/app/main.py` - FastAPI应用入口
- `backend/app/config.py` - 应用配置管理
- `backend/app/services/rag_service.py` - RAG核心逻辑
- `backend/app/services/ai_service.py` - AI集成服务

### 前端核心文件
- `frontend/src/App.vue` - 根组件
- `frontend/src/router/routes.ts` - 路由配置
- `frontend/src/stores/conversation.ts` - 对话状态管理
- `frontend/src/views/Chat.vue` - 聊天主界面

### 数据库核心文件
- `database/schema.sql` - 完整数据库设计
- `database/migrations/` - 数据库版本管理

这个项目结构设计支持模块化开发、易于维护和扩展，符合现代Web应用的最佳实践。