# 智能法律助手开发指南

## 1. 开发环境搭建

### 1.1 环境要求
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+ (需安装pgvector扩展)
- Git

### 1.2 后端开发环境

```bash
# 1. 创建Python虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库连接和API密钥

# 4. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 1.3 前端开发环境

```bash
# 1. 安装前端依赖
cd frontend
npm install

# 2. 启动开发服务器
npm run dev
```

### 1.4 数据库设置

```bash
# 1. 安装PostgreSQL和pgvector扩展
# Ubuntu/Debian:
sudo apt install postgresql postgresql-contrib

# 2. 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE legal_assistant;
CREATE USER legal_assistant WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE legal_assistant TO legal_assistant;

# 3. 启用pgvector扩展
\c legal_assistant
CREATE EXTENSION vector;

# 4. 执行数据库初始化
\i database/schema.sql
```

## 2. 项目架构说明

### 2.1 后端架构

```
backend/
├── app/
│   ├── api/           # API路由层
│   ├── core/          # 核心配置和工具
│   ├── models/        # 数据模型
│   ├── schemas/       # Pydantic模型
│   ├── services/      # 业务逻辑层
│   └── utils/         # 工具函数
└── tests/             # 测试文件
```

### 2.2 前端架构

```
frontend/
├── src/
│   ├── components/    # Vue组件
│   ├── views/         # 页面组件
│   ├── stores/        # 状态管理
│   ├── services/      # API服务
│   ├── types/         # TypeScript类型
│   └── utils/         # 工具函数
└── public/            # 静态资源
```

## 3. 开发规范

### 3.1 代码风格

**Python代码规范：**
- 遵循PEP 8规范
- 使用Black进行代码格式化
- 使用isort进行导入排序
- 类型提示使用Python 3.9+语法

**TypeScript代码规范：**
- 使用ESLint + Prettier
- 严格的类型检查
- 组件使用Composition API
- 遵循Vue 3最佳实践

### 3.2 Git提交规范

```bash
# 提交信息格式
feat: 添加用户认证功能
fix: 修复文件上传bug
docs: 更新API文档
style: 调整代码格式
refactor: 重构聊天服务
test: 添加单元测试
chore: 更新依赖版本
```

### 3.3 分支管理

- `main`: 主分支，生产环境代码
- `develop`: 开发分支，功能集成
- `feature/*`: 功能开发分支
- `hotfix/*`: 紧急修复分支

## 4. API开发指南

### 4.1 创建新的API端点

```python
# 在 app/api/ 目录下创建新文件
from fastapi import APIRouter, Depends
from app.schemas.your_schema import YourRequest, YourResponse
from app.services.your_service import your_service_function

router = APIRouter()

@router.post("/your-endpoint", response_model=YourResponse)
async def create_something(
    request: YourRequest,
    current_user: User = Depends(get_current_user)
):
    """创建资源的API端点"""
    result = await your_service_function(request, current_user)
    return result
```

### 4.2 数据模型定义

```python
# 数据库模型 (app/models/)
class YourModel(Base):
    __tablename__ = "your_table"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)

# Pydantic模型 (app/schemas/)
class YourSchema(BaseModel):
    name: str
    
    class Config:
        from_attributes = True
```

### 4.3 业务逻辑服务

```python
# 在 app/services/ 目录下创建服务
class YourService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def your_business_logic(self, data: YourSchema) -> YourModel:
        # 实现业务逻辑
        pass
```

## 5. 前端开发指南

### 5.1 创建新组件

```vue
<template>
  <div class="your-component">
    <h2>{{ title }}</h2>
    <!-- 组件内容 -->
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  title: string
}

const props = defineProps<Props>()
const localState = ref('')
</script>

<style scoped>
.your-component {
  /* 组件样式 */
}
</style>
```

### 5.2 状态管理

```typescript
// 在 src/stores/ 目录下创建store
import { defineStore } from 'pinia'

export const useYourStore = defineStore('yourStore', () => {
  const state = ref('')
  
  const action = async () => {
    // 业务逻辑
  }
  
  return { state, action }
})
```

### 5.3 API服务调用

```typescript
// 在 src/services/ 目录下创建服务
import { request } from './api'

export const yourService = {
  async getData(): Promise<YourType> {
    return request.get<YourType>('/api/your-endpoint')
  }
}
```

## 6. 数据库开发

### 6.1 数据库迁移

```bash
# 创建迁移文件
alembic revision --autogenerate -m "添加新表"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 6.2 向量搜索开发

```python
# 使用pgvector进行相似度搜索
from sqlalchemy import select
from pgvector.sqlalchemy import Vector

async def vector_search(query_embedding: List[float]):
    stmt = select(DocumentEmbedding).order_by(
        DocumentEmbedding.embedding.cosine_distance(query_embedding)
    ).limit(5)
    
    result = await db.execute(stmt)
    return result.scalars().all()
```

## 7. AI集成开发

### 7.1 RAG流程实现

```python
class RAGService:
    async def rag_search(self, query: str, user_id: UUID) -> str:
        # 1. 生成查询向量
        query_embedding = await self.generate_embedding(query)
        
        # 2. 向量相似度搜索
        similar_chunks = await self.vector_search(query_embedding, user_id)
        
        # 3. 构建Prompt
        context = self.build_context(similar_chunks)
        prompt = self.build_prompt(query, context)
        
        # 4. 调用AI模型
        response = await self.call_ai_model(prompt)
        
        return response
```

### 7.2 对话管理

```python
class ConversationService:
    async def create_conversation(self, user_id: UUID, title: str) -> Conversation:
        # 创建新对话
        pass
    
    async def add_message(self, conversation_id: UUID, role: str, content: str) -> Message:
        # 添加消息
        pass
    
    async def get_conversation_history(self, conversation_id: UUID) -> List[Message]:
        # 获取对话历史
        pass
```

## 8. 测试开发

### 8.1 后端测试

```python
# 在 tests/ 目录下创建测试文件
import pytest
from fastapi.testclient import TestClient

class TestYourAPI:
    def test_your_endpoint(self, client: TestClient):
        response = client.post("/api/your-endpoint", json={"name": "test"})
        assert response.status_code == 200
```

### 8.2 前端测试

```typescript
// 使用Vitest进行组件测试
import { mount } from '@vue/test-utils'
import YourComponent from '@/components/YourComponent.vue'

describe('YourComponent', () => {
  it('renders correctly', () => {
    const wrapper = mount(YourComponent, {
      props: { title: 'Test' }
    })
    expect(wrapper.text()).toContain('Test')
  })
})
```

## 9. 调试和优化

### 9.1 后端调试

```python
# 使用日志记录
import logging

logger = logging.getLogger(__name__)

async def your_function():
    logger.info("函数开始执行")
    # 业务逻辑
    logger.debug(f"中间结果: {result}")
```

### 9.2 前端调试

```typescript
// 使用浏览器开发者工具
console.log('调试信息', data)

// Vue Devtools
// 安装Vue Devtools浏览器扩展进行调试
```

### 9.3 性能优化

**数据库优化：**
- 添加合适的索引
- 使用连接池
- 避免N+1查询

**前端优化：**
- 代码分割
- 图片懒加载
- 组件缓存

## 10. 部署和CI/CD

### 10.1 本地构建测试

```bash
# 后端构建
cd backend
python -m pytest

# 前端构建
cd frontend
npm run build
npm run type-check
```

### 10.2 Docker构建

```bash
# 构建后端镜像
docker build -t legal-assistant-backend ./backend

# 构建前端镜像
docker build -t legal-assistant-frontend ./frontend
```

## 11. 常见问题解决

### 11.1 依赖问题

```bash
# 清理Python缓存
pip cache purge

# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 清理Node.js依赖
rm -rf node_modules package-lock.json
npm install
```

### 11.2 数据库连接问题

```bash
# 检查数据库服务
sudo systemctl status postgresql

# 检查连接权限
psql -h localhost -U legal_assistant -d legal_assistant
```

### 11.3 CORS问题

```python
# 检查后端CORS配置
# 在 app/core/config.py 中确认CORS_ORIGINS设置
```

## 12. 贡献指南

### 12.1 提交代码

1. Fork项目仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

### 12.2 代码审查

- 确保代码符合规范
- 添加必要的测试
- 更新相关文档
- 通过CI/CD检查

## 总结

本开发指南提供了从环境搭建到代码提交的完整开发流程。遵循这些指南可以确保代码质量、可维护性和团队协作效率。