# 智能法律助手 (Intelligent Legal Assistant)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-yellow.svg)
![Vue.js](https://img.shields.io/badge/vue.js-3.3+-4FC08D.svg)

基于AI技术的智能法律咨询系统，采用RAG（检索增强生成）架构，提供专业的法律问题解答、文档管理和智能对话功能。

## ✨ 核心特性

- 🤖 **智能法律问答** - 基于大语言模型的专业法律咨询
- 📚 **RAG知识库系统** - 支持多种格式文档的智能检索
- 🔍 **语义搜索** - 基于向量相似度的精准文档检索
- 💬 **多轮对话** - 上下文感知的智能对话管理
- 👥 **用户权限管理** - 完整的RBAC角色权限系统
- 📊 **数据统计分析** - 全面的系统数据监控和分析
- 🎨 **现代化UI** - 基于Element Plus的专业界面设计

## 🏗️ 系统架构

### 技术栈

#### 后端
- **框架**: FastAPI 0.100+
- **语言**: Python 3.9+
- **数据库**: PostgreSQL 16 + pgvector
- **向量数据库**: Milvus 2.3.3
- **对象存储**: MinIO
- **AI模型**: 豆包大模型（火山引擎）
- **文档处理**: PyPDF2, pdfplumber, python-docx
- **中文分词**: jieba

#### 前端
- **框架**: Vue 3.3+
- **语言**: TypeScript 5.0+
- **构建工具**: Vite 4.3+
- **UI组件**: Element Plus 2.3+
- **状态管理**: Pinia 2.1+
- **路由**: Vue Router 4.2+
- **HTTP客户端**: Axios

#### 部署
- **容器化**: Docker + Docker Compose
- **Web服务器**: Nginx
- **缓存**: Redis 7

### 核心功能模块

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 聊天界面  │ │ 文档管理  │ │ 用户管理  │ │ 数据统计  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 认证授权  │ │ 对话管理  │ │ 文档处理  │ │ RAG服务  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    数据存储层                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │PostgreSQL│ │  Milvus  │ │  MinIO   │ │  Redis   │      │
│  │  +pgvector│ │Vector DB │ │Object S3 │ │  Cache   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   AI服务层                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │ 豆包LLM  │ │Embedding │ │意图识别   │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
Intelligent_Legal_Assistant/
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── api/                   # API路由
│   │   │   ├── auth.py           # 认证授权
│   │   │   ├── chat.py           # 聊天对话
│   │   │   ├── documents.py      # 文档管理
│   │   │   └── admin.py          # 管理后台
│   │   ├── core/                  # 核心配置
│   │   │   ├── config.py         # 配置管理
│   │   │   ├── database.py       # 数据库连接
│   │   │   ├── security.py       # 安全认证
│   │   │   └── langchain_config.py # LangChain配置
│   │   ├── models/                # SQLAlchemy模型
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── document.py
│   │   │   └── role.py
│   │   ├── services/              # 业务逻辑
│   │   │   ├── auth_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── document_service.py
│   │   │   ├── rag_service.py    # RAG核心服务
│   │   │   ├── document_processor/ # 文档处理
│   │   │   └── langchain_processor/ # LangChain集成
│   │   └── utils/                 # 工具函数
│   │       └── text_analyzer.py   # 文本分析
│   ├── requirements.txt            # Python依赖
│   └── Dockerfile
├── frontend/                       # 前端应用
│   ├── src/
│   │   ├── api/                   # API接口
│   │   ├── components/            # Vue组件
│   │   ├── layouts/               # 布局组件
│   │   ├── router/                # 路由配置
│   │   ├── services/              # 服务层
│   │   │   ├── auth.ts
│   │   │   ├── chat.ts
│   │   │   └── document.ts
│   │   ├── stores/                # Pinia状态管理
│   │   │   ├── auth.ts
│   │   │   └── chat.ts
│   │   ├── types/                 # TypeScript类型
│   │   ├── utils/                 # 工具函数
│   │   ├── views/                 # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── Chat.vue
│   │   │   ├── Documents.vue
│   │   │   └── admin/             # 管理后台
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.ts
├── database/                       # 数据库脚本
│   └── schema.sql                 # 数据库结构
├── docs/                          # 项目文档
│   ├── INSTALLATION.md           # 安装部署指南
│   ├── CHAT_DEVELOPMENT_PLAN.md  # 聊天功能开发计划
│   └── *.md                       # 其他文档
├── installation/                   # 独立安装配置
│   ├── pgvector/                 # PostgreSQL配置
│   │   └── docker-compose.yml
│   └── milvus/                   # Milvus配置
│       └── docker-compose.yml
├── knowledge_document/            # 知识库文档
├── docker-compose.yml             # Docker编排
├── .env.example                   # 环境变量模板
└── README.md                      # 项目说明
```

## 🚀 快速开始

### 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.9+ | 3.11 |
| Node.js | 16+ | 18 LTS |
| Docker | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |
| 内存 | 8GB | 16GB+ |
| 磁盘空间 | 40GB | 100GB SSD |

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/zhangkuntony/Intelligent_Legal_Assistant
cd Intelligent_Legal_Assistant
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件，填入必要的配置
nano .env
```

**关键配置项**：
```bash
# AI服务配置（必填）
LLM_API_KEY=your-doubao-api-key
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-1-5-pro-32k-250115

# Embedding模型配置
EMBEDDING_MODEL_URL=https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal
EMBEDDING_MODEL=doubao-embedding-vision-250615

# 数据库配置
DATABASE_URL=postgresql+asyncpg://legal_assistant:legal_assistant_123456@localhost:5432/legal_assistant

# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=legal_documents
```

#### 3. 启动基础设施服务

```bash
# 启动PostgreSQL（独立配置）
cd installation/pgvector
docker-compose up -d

# 初始化数据库（首次运行必须执行）
cd ../..
docker exec -i legal_assistant_db psql -U legal_assistant -d legal_assistant < database/schema.sql

# 启动Milvus向量数据库
cd installation/milvus
docker-compose up -d
cd ../..

# 验证服务状态
docker ps
```

#### 4. 启动应用服务

**方式一：Docker容器部署（推荐生产环境）**

```bash
# 启动Redis、后端、前端
docker-compose up -d redis backend frontend

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

**方式二：本地服务启动（推荐开发环境）**

```bash
# 终端1：启动后端
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2：启动前端
cd frontend
npm install
npm run dev
```

#### 5. 访问应用

- **前端应用**: http://localhost:3000
- **后端API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **MinIO控制台**: http://localhost:9001

### 默认用户账号

系统初始化后会创建默认用户：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | 123456 | 超级管理员 |
| testuser | 123456 | 普通用户 |

⚠️ **安全提示**: 生产环境请务必修改默认密码！

## 📚 功能说明

### 1. 智能法律聊天

- **意图识别**: 自动判断用户问题是否为法律相关
- **问题理解**: 分析问题的核心诉求和法律要素
- **RAG检索**: 基于向量相似度检索相关法律文档
- **智能回答**: 结合检索结果生成专业建议
- **上下文保持**: 支持多轮对话历史管理
- **来源引用**: 显示参考的法律法规和案例

### 2. 文档管理

- **多格式支持**: PDF、Word、TXT等格式
- **智能分块**: 支持多种分块策略（固定长度、语义、混合）
- **向量化存储**: 自动生成文档向量并存储到Milvus
- **图片提取**: 支持PDF中的图片提取和存储
- **文档分类**: 支持按类别组织文档
- **全文检索**: 基于向量相似度的语义搜索

### 3. 用户权限管理

- **RBAC模型**: 基于角色的访问控制
- **角色管理**: 创建、编辑、删除角色
- **权限分配**: 灵活的权限配置系统
- **用户管理**: 用户注册、角色分配、权限继承
- **审计日志**: 记录所有关键操作

### 4. 数据统计分析

- **会话趋势**: 会话数量和活跃用户统计
- **知识库分析**: 文档访问排行和热门话题
- **用户行为**: 用户活跃度和满意度分析
- **关键词提取**: 基于TF-IDF的智能关键词提取

## 🔌 API接口

### 认证接口

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/verify-code` - 验证码验证
- `POST /api/auth/logout` - 用户登出

### 聊天接口

- `GET /api/chat/conversations` - 获取对话列表
- `POST /api/chat/conversations` - 创建对话
- `GET /api/chat/conversations/{id}` - 获取对话详情
- `POST /api/chat/send` - 发送消息
- `GET /api/chat/messages/{conversation_id}` - 获取消息历史
- `DELETE /api/chat/conversations/{id}` - 删除对话

### 文档接口

- `GET /api/documents` - 获取文档列表
- `POST /api/documents/upload` - 上传文档
- `GET /api/documents/{id}` - 获取文档详情
- `DELETE /api/documents/{id}` - 删除文档
- `POST /api/documents/{id}/process` - 处理文档生成向量
- `GET /api/documents/search` - 语义搜索文档

### 管理接口

- `GET /api/admin/users` - 用户列表
- `GET /api/admin/roles` - 角色列表
- `GET /api/admin/permissions` - 权限列表
- `GET /api/admin/analytics` - 数据统计
- `GET /api/admin/audit-logs` - 审计日志

详细的API文档请访问：http://localhost:8000/docs

## 🛠️ 开发指南

### 后端开发

```bash
# 进入后端目录
cd backend

# 激活虚拟环境
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest

# 代码格式化
black app/
isort app/

# 代码检查
flake8 app/
```

### 前端开发

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview

# 代码检查
npm run lint
```

### 数据库操作

```bash
# 连接到PostgreSQL
docker exec -it legal_assistant_db psql -U legal_assistant -d legal_assistant

# 常用命令
\dt                    # 列出所有表
\d table_name         # 查看表结构
\q                     # 退出

# 备份数据库
docker exec legal_assistant_db pg_dump -U legal_assistant legal_assistant > backup.sql

# 恢复数据库
cat backup.sql | docker exec -i legal_assistant_db psql -U legal_assistant legal_assistant
```

## 📖 文档

- [安装部署指南](docs/INSTALLATION.md) - 详细的安装和部署步骤
- [聊天功能开发计划](docs/CHAT_DEVELOPMENT_PLAN.md) - 聊天功能的技术实现
- [项目结构说明](project-structure.md) - 详细的代码组织结构
- [API接口文档](http://localhost:8000/docs) - Swagger自动生成的API文档

## 🔧 配置说明

### 环境变量

主要的环境变量配置项：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ENVIRONMENT | 运行环境 | development |
| DATABASE_URL | 数据库连接字符串 | - |
| LLM_API_KEY | 豆包API密钥 | - |
| LLM_MODEL | LLM模型名称 | doubao-1-5-pro-32k-250115 |
| EMBEDDING_MODEL | Embedding模型 | doubao-embedding-vision-250615 |
| MILVUS_HOST | Milvus地址 | localhost |
| MILVUS_PORT | Milvus端口 | 19530 |
| MINIO_ENDPOINT | MinIO地址 | localhost:9000 |
| SECRET_KEY | JWT密钥 | - |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token过期时间 | 10080 |

### 分块策略

文档支持多种分块策略：

- `fixed` - 固定长度分块
- `semantic` - 语义分块
- `hybrid` - 混合分块（推荐）

## 🐛 常见问题

### 1. PostgreSQL连接失败

```bash
# 检查容器状态
docker ps | grep legal_assistant_db

# 检查数据库日志
docker logs legal_assistant_db

# 手动连接测试
docker exec -it legal_assistant_db psql -U legal_assistant -d legal_assistant
```

### 2. Milvus启动失败

```bash
# 检查Milvus服务
cd installation/milvus
docker-compose ps

# 查看日志
docker-compose logs -f milvus

# 重启服务
docker-compose restart
```

### 3. 前端无法连接后端

- 检查 `frontend/.env` 中的 `VITE_API_BASE_URL` 是否正确
- 确保后端服务正在运行
- 检查浏览器控制台的网络请求错误

### 4. 文档上传失败

- 检查文件大小是否超过限制（默认10MB）
- 检查文件类型是否被允许
- 查看后端日志获取详细错误信息

更多问题请参考 [安装部署指南](docs/INSTALLATION.md) 中的常见问题章节。

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 代码规范

- 后端代码遵循 PEP 8 规范
- 前端代码遵循 ESLint 规则
- 提交信息采用 Conventional Commits 格式

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 👥 联系方式

- 项目主页: [https://github.com/zhangkuntony/Intelligent_Legal_Assistant](https://github.com/zhangkuntony/Intelligent_Legal_Assistant)
- 问题反馈: [GitHub Issues](https://github.com/zhangkuntony/Intelligent_Legal_Assistant/issues)

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3 UI组件库
- [Milvus](https://milvus.io/) - 开源向量数据库
- [LangChain](https://langchain.com/) - AI应用开发框架

---

**免责声明**: 本系统提供的法律建议仅供参考，不构成正式法律意见。如需专业法律服务，请咨询执业律师。
