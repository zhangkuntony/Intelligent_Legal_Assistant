# 智能法律助手部署指南

## 部署方案概述

本项目支持多种部署方式：
- **开发环境**：使用Docker Compose快速启动
- **生产环境**：使用Docker Compose或手动部署
- **云平台**：支持部署到云服务器

## 1. 开发环境部署

### 1.1 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- Git

### 1.2 快速启动步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd intelligent_legal_Assistant

# 2. 复制环境变量文件
cp .env.example .env

# 3. 修改环境变量（重要！）
# 编辑 .env 文件，设置以下关键配置：
# - OPENAI_API_KEY: 您的OpenAI API密钥
# - SECRET_KEY: 生产环境必须修改为强密码
# - DATABASE_URL: 数据库连接字符串

# 4. 启动所有服务
docker-compose up -d

# 5. 检查服务状态
docker-compose ps
```

### 1.3 访问应用
- **前端应用**：http://localhost:3000
- **后端API**：http://localhost:8000
- **API文档**：http://localhost:8000/docs
- **数据库**：localhost:5432

## 2. 生产环境部署

### 2.1 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker和Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2.2 应用部署

```bash
# 1. 创建应用目录
sudo mkdir -p /opt/legal-assistant
sudo chown $USER:$USER /opt/legal-assistant
cd /opt/legal-assistant

# 2. 克隆项目代码
git clone <repository-url> .

# 3. 配置生产环境变量
cp .env.example .env.production
# 编辑 .env.production，设置生产环境配置

# 4. 使用生产环境Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### 2.3 生产环境配置

#### Nginx配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # 文件上传
    location /uploads {
        proxy_pass http://backend:8000;
    }
}
```

#### SSL证书配置（使用Let's Encrypt）
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com
```

## 3. 数据库管理

### 3.1 数据库初始化

```bash
# 连接到数据库容器
docker exec -it legal_assistant_db psql -U legal_assistant -d legal_assistant

# 执行初始化脚本
\i /docker-entrypoint-initdb.d/init.sql
```

### 3.2 数据库备份

```bash
# 创建备份
docker exec legal_assistant_db pg_dump -U legal_assistant legal_assistant > backup_$(date +%Y%m%d).sql

# 恢复备份
cat backup.sql | docker exec -i legal_assistant_db psql -U legal_assistant legal_assistant
```

### 3.3 数据库迁移

```bash
# 使用Alembic进行数据库迁移
cd backend
docker-compose exec backend alembic upgrade head
```

## 4. 监控和维护

### 4.1 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### 4.2 服务管理

```bash
# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新服务（代码更新后）
docker-compose down
git pull
docker-compose build --no-cache
docker-compose up -d
```

### 4.3 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查数据库连接
docker exec legal_assistant_db pg_isready -U legal_assistant -d legal_assistant
```

## 5. 安全配置

### 5.1 防火墙配置

```bash
# 启用防火墙
sudo ufw enable

# 开放必要端口
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
```

### 5.2 密钥管理

```bash
# 生成强密码
openssl rand -base64 32

# 设置环境变量安全
chmod 600 .env.production
```

## 6. 性能优化

### 6.1 数据库优化

```sql
-- 创建性能优化索引
CREATE INDEX CONCURRENTLY idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX CONCURRENTLY idx_document_embeddings_search ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 200);
```

### 6.2 应用优化

```python
# 后端配置优化
# 在 app/core/config.py 中调整：
- 连接池大小
- 超时设置
- 缓存配置
```

## 7. 故障排除

### 7.1 常见问题

**问题1：数据库连接失败**
```bash
# 检查数据库服务状态
docker-compose ps postgres
# 检查数据库日志
docker-compose logs postgres
```

**问题2：前端无法访问API**
```bash
# 检查后端服务状态
docker-compose ps backend
# 检查CORS配置
curl -H "Origin: http://localhost:3000" http://localhost:8000/health
```

**问题3：文件上传失败**
```bash
# 检查上传目录权限
ls -la uploads/
# 检查Nginx配置
```

### 7.2 性能监控

```bash
# 监控系统资源
docker stats

# 监控数据库性能
docker exec legal_assistant_db pg_stat_activity
```

## 8. 扩展部署

### 8.1 多服务器部署

对于高可用性需求，可以考虑：
- 使用负载均衡器
- 数据库主从复制
- 多实例后端服务

### 8.2 云平台部署

支持部署到：
- AWS/Aliyun/Tencent Cloud
- Kubernetes集群
- Serverless架构

## 总结

本部署指南涵盖了从开发到生产的完整部署流程。根据实际需求选择合适的部署方案，并确保遵循安全最佳实践。