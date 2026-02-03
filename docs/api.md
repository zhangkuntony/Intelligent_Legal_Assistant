# 智能法律助手 API 文档

## 概述

智能法律助手提供完整的RESTful API接口，支持用户认证、对话管理、文档处理和AI聊天等功能。

## 基础信息

- **Base URL**: `http://localhost:8000` (开发环境)
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON
- **API文档**: `http://localhost:8000/docs` (Swagger UI)

## 认证接口

### 用户注册

**POST** `/api/auth/register`

注册新用户

**请求体:**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123",
  "full_name": "测试用户"
}
```

**响应:**
```json
{
  "message": "用户注册成功"
}
```

### 用户登录

**POST** `/api/auth/login`

用户登录，获取访问令牌

**请求体:**
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**响应:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "测试用户"
  }
}
```

### 获取当前用户信息

**GET** `/api/auth/me`

获取当前登录用户信息

**Headers:**
```
Authorization: Bearer <access_token>
```

**响应:**
```json
{
  "id": "uuid",
  "username": "testuser",
  "email": "test@example.com",
  "full_name": "测试用户",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

## 用户管理接口

### 获取用户列表 (管理员)

**GET** `/api/users/`

获取用户列表（需要管理员权限）

**查询参数:**
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 20)

**响应:**
```json
{
  "users": [
    {
      "id": "uuid",
      "username": "user1",
      "email": "user1@example.com",
      "is_active": true
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

## 智能聊天接口

### 获取对话列表

**GET** `/api/chat/conversations`

获取当前用户的对话列表

**查询参数:**
- `skip`: 跳过的数量 (默认: 0)
- `limit`: 返回的最大数量 (默认: 20, 最大: 100)

**响应:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "title": "劳动合同咨询",
    "description": "关于劳动合同的咨询",
    "is_archived": false,
    "message_count": 15,
    "last_message_at": "2025-01-01T10:00:00Z",
    "created_at": "2025-01-01T09:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z"
  }
]
```

### 创建新对话

**POST** `/api/chat/conversations`

创建新的对话会话

**请求体:**
```json
{
  "title": "新对话",
  "description": "对话描述"
}
```

**响应:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "新对话",
  "description": "对话描述",
  "is_archived": false,
  "message_count": 0,
  "last_message_at": null,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### 获取对话详情

**GET** `/api/chat/conversations/{conversation_id}`

获取特定对话的详细信息和消息历史

**响应:**
```json
{
  "conversation": {
    "id": "uuid",
    "user_id": "uuid",
    "title": "劳动合同咨询",
    "description": "关于劳动合同的咨询",
    "is_archived": false,
    "message_count": 2,
    "last_message_at": "2025-01-01T09:01:00Z",
    "created_at": "2025-01-01T09:00:00Z",
    "updated_at": "2025-01-01T09:01:00Z"
  },
  "messages": [
    {
      "id": "msg_uuid",
      "conversation_id": "uuid",
      "role": "user",
      "content": "您好，我想咨询劳动合同问题",
      "tokens_used": 0,
      "meta_data": null,
      "created_at": "2025-01-01T09:00:00Z"
    },
    {
      "id": "msg_uuid2",
      "conversation_id": "uuid",
      "role": "assistant",
      "content": "根据《劳动合同法》...",
      "tokens_used": 256,
      "meta_data": null,
      "created_at": "2025-01-01T09:01:00Z"
    }
  ]
}
```

### 发送消息（智能聊天）

**POST** `/api/chat/send`

发送消息并获取AI回复，执行完整的RAG流程

**请求体:**
```json
{
  "content": "我想了解劳动合同解除的相关规定",
  "conversation_id": "uuid (可选)",
  "use_rag": true
}
```

**响应:**
```json
{
  "message_id": "msg_uuid",
  "content": "根据《劳动合同法》相关规定，劳动合同解除分为...",
  "intent": {
    "is_legal": true,
    "confidence": 0.95,
    "legal_domain": "劳动法",
    "explanation": "问题涉及劳动合同解除的法律规定"
  },
  "question_analysis": {
    "original_question": "我想了解劳动合同解除的相关规定",
    "key_entities": ["劳动合同", "解除"],
    "legal_concepts": ["劳动合同解除", "劳动合同法"],
    "optimized_query": "劳动合同解除 条件 规定",
    "missing_info": []
  },
  "retrieved_docs": [
    {
      "document_id": "uuid",
      "document_title": "劳动合同法全文",
      "chunk_index": 10,
      "chunk_content": "第三十九条 劳动者有下列情形之一的...",
      "similarity": 0.92,
      "metadata": {
        "chapter": "第四章",
        "section": "第三十九条"
      }
    }
  ],
  "tokens_used": 450,
  "sources": [
    {
      "document_title": "劳动合同法全文",
      "section": "第三十九条",
      "relevance": 0.92
    }
  ]
}
```

### 获取消息历史

**GET** `/api/chat/conversations/{conversation_id}/messages`

获取对话的消息列表

**查询参数:**
- `limit`: 返回的最大消息数量 (默认: 50, 最大: 200)

**响应:**
```json
{
  "conversation_id": "uuid",
  "total_messages": 15,
  "messages": [
    {
      "id": "msg_uuid",
      "role": "user",
      "content": "您好，我想咨询劳动合同问题",
      "tokens_used": 0,
      "meta_data": null,
      "created_at": "2025-01-01T09:00:00Z"
    },
    {
      "id": "msg_uuid2",
      "role": "assistant",
      "content": "根据《劳动合同法》...",
      "tokens_used": 256,
      "meta_data": null,
      "created_at": "2025-01-01T09:01:00Z"
    }
  ]
}
```

### 更新对话

**PUT** `/api/chat/conversations/{conversation_id}`

更新对话的标题和描述

**查询参数:**
- `title`: 新标题 (可选)
- `description`: 新描述 (可选)

**响应:**
```json
{
  "message": "对话更新成功",
  "conversation": {
    "id": "uuid",
    "title": "新标题",
    "description": "新描述",
    "updated_at": "2025-01-01T10:00:00Z"
  }
}
```

### 删除对话

**DELETE** `/api/chat/conversations/{conversation_id}`

删除对话及其所有消息

**响应:**
```json
{
  "message": "对话删除成功"
}
```

## 文档管理接口

### 上传文档

**POST** `/api/documents/upload`

上传文档到知识库

**Content-Type:** `multipart/form-data`

**表单数据:**
- `file`: 文档文件 (PDF, DOC, DOCX, TXT)
- `title`: 文档标题

**响应:**
```json
{
  "id": "uuid",
  "title": "劳动合同范本",
  "filename": "contract.pdf",
  "file_size": 1024000,
  "status": "processing",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### 获取文档列表

**GET** `/api/documents/`

获取用户的文档列表

**查询参数:**
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 20)
- `status`: 文档状态 (processing/completed/failed)

**响应:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "title": "劳动合同范本",
      "filename": "contract.pdf",
      "file_size": 1024000,
      "status": "completed",
      "chunk_count": 25,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

### 删除文档

**DELETE** `/api/documents/{document_id}`

删除文档及其向量数据

**响应:**
```json
{
  "message": "文档删除成功"
}
```

### 文档搜索

**POST** `/api/documents/search`

在知识库中搜索相关文档

**请求体:**
```json
{
  "query": "劳动合同解除",
  "top_k": 5
}
```

**响应:**
```json
{
  "results": [
    {
      "document_id": "uuid",
      "document_title": "劳动合同法全文",
      "chunk_content": "第三十九条 劳动者有下列情形之一的，用人单位可以解除劳动合同...",
      "similarity": 0.85
    }
  ],
  "query": "劳动合同解除",
  "total_results": 3
}
```

## 系统管理接口

### 健康检查

**GET** `/health`

检查系统健康状态

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

### 系统信息

**GET** `/`

获取系统基本信息

**响应:**
```json
{
  "message": "智能法律助手 API 服务运行中",
  "version": "1.0.0",
  "environment": "development"
}
```

## 错误码说明

| 状态码 | 错误类型 | 说明 |
|--------|----------|------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未授权访问 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |

## 错误响应格式

```json
{
  "error": true,
  "message": "错误描述",
  "code": 400,
  "detail": "详细错误信息（开发环境）"
}
```

## 数据模型

### 用户模型 (User)
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "full_name": "string | null",
  "avatar_url": "string | null",
  "is_active": "boolean",
  "is_superuser": "boolean",
  "last_login": "datetime | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 对话模型 (Conversation)
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "string",
  "description": "string | null",
  "is_archived": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 消息模型 (Message)
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "role": "string (user/assistant/system)",
  "content": "string",
  "tokens_used": "integer",
  "metadata": "object | null",
  "created_at": "datetime"
}
```

### 文档模型 (Document)
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "string",
  "filename": "string",
  "file_path": "string",
  "file_size": "integer",
  "file_type": "string",
  "status": "string (processing/completed/failed)",
  "total_chunks": "integer",
  "processed_chunks": "integer",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 使用示例

### JavaScript/TypeScript 示例

```javascript
// 用户登录
async function login(username, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  return data;
}

// 发送消息（智能聊天）
async function sendMessage(content, conversationId = null) {
  const token = localStorage.getItem('access_token');

  const response = await fetch('/api/chat/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      content,
      conversation_id: conversationId,
      use_rag: true
    })
  });

  return await response.json();
}

// 获取对话列表
async function getConversations(skip = 0, limit = 20) {
  const token = localStorage.getItem('access_token');

  const response = await fetch(`/api/chat/conversations?skip=${skip}&limit=${limit}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  return await response.json();
}

// 创建新对话
async function createConversation(title = "新对话", description = null) {
  const token = localStorage.getItem('access_token');

  const response = await fetch('/api/chat/conversations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      title,
      description
    })
  });

  return await response.json();
}
```

### Python 示例

```python
import requests

# 用户登录
login_data = {
    "username": "testuser",
    "password": "password123"
}

response = requests.post("http://localhost:8000/api/auth/login", json=login_data)
data = response.json()
token = data["access_token"]

# 发送消息（智能聊天）
headers = {"Authorization": f"Bearer {token}"}
message_data = {
    "content": "法律问题咨询",
    "use_rag": True
}

response = requests.post(
    "http://localhost:8000/api/chat/send",
    json=message_data,
    headers=headers
)

# 获取对话列表
response = requests.get(
    "http://localhost:8000/api/chat/conversations?skip=0&limit=20",
    headers=headers
)
```

## 注意事项

1. **认证要求**: 除登录和注册接口外，所有接口都需要Bearer Token认证
2. **文件上传**: 文档上传接口使用multipart/form-data格式
3. **分页参数**: 列表接口支持分页，默认page=1, page_size=20
4. **错误处理**: 统一使用HTTP状态码和JSON错误响应格式
5. **数据验证**: 所有输入数据都会进行严格验证

## 版本历史

- **v1.0.0** (2025-01-01): 初始版本发布，包含基础功能