# 智能法律助手 (Intelligent Legal Assistant)

基于AI技术的智能法律咨询系统，提供专业的法律问题解答和文档管理功能。

## 系统架构

### 技术栈
- **前端**: Vue 3 + TypeScript + Vite + Element Plus
- **后端**: FastAPI + PostgreSQL + pgvector
- **AI集成**: LangChain + OpenAI API
- **部署**: Docker + Nginx

### 核心功能模块

#### 1. RAG知识库系统
- 文档上传和管理
- 向量化存储和检索
- 智能语义搜索

#### 2. 智能法律助手
- 实时AI对话
- 上下文感知回答
- 历史对话管理

#### 3. 用户管理系统
- 用户注册登录
- 权限控制
- 个人数据管理

## 项目结构

```
legal_assistant/
├── backend/                 # FastAPI后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # Vue3前端应用
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── views/          # 页面
│   │   ├── stores/         # 状态管理
│   │   ├── services/       # API服务
│   │   └── utils/          # 工具函数
│   ├── package.json
│   └── Dockerfile
├── database/               # 数据库相关
│   ├── migrations/         # 迁移脚本
│   ├── init.sql           # 初始化脚本
│   └── schema.sql         # 数据库设计
├── docs/                   # 项目文档
│   ├── api.md             # API接口文档
│   ├── deployment.md      # 部署指南
│   └── development.md     # 开发指南
└── docker-compose.yml     # Docker编排文件
```

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+ (需安装pgvector扩展)
- Docker (可选)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd intelligent_legal_assistant
```

2. **后端设置**
```bash
cd backend
pip install -r requirements.txt
```

3. **前端设置**
```bash
cd frontend
npm install
```

4. **数据库设置**
```bash
# 启动PostgreSQL并创建数据库
cd database
psql -f init.sql
```

5. **启动服务**
```bash
# 启动后端
cd backend && uvicorn app.main:app --reload

# 启动前端
cd frontend && npm run dev
```

## API文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看完整的API文档。

## 部署

### Docker部署
```bash
docker-compose up -d
```

### 生产环境部署
参考 `docs/deployment.md` 文件获取详细的生产环境部署指南。

## 开发指南

详细的技术文档和开发指南请参考 `docs/development.md`。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 许可证

本项目采用MIT许可证。