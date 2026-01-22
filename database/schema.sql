-- 智能法律助手数据库设计
-- 使用PostgreSQL 13+ 和 pgvector扩展

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 创建数据库用户和权限（根据需要调整）
-- CREATE USER legal_assistant WITH PASSWORD 'your_password';
-- GRANT ALL PRIVILEGES ON DATABASE legal_assistant TO legal_assistant;

-- ==================== 核心数据表设计 ====================

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 对话会话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL DEFAULT '新对话',
    description TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    meta_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 知识库文档表
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_category VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    processing_error TEXT,
    total_chunks INTEGER DEFAULT 0,
    processed_chunks INTEGER DEFAULT 0,
    meta_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(2000)
);

-- 文档向量表（使用pgvector扩展）
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embedding维度
    meta_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 索引优化 ====================

-- 用户表索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 对话表索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);

-- 消息表索引
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_role ON messages(role);

-- 文档表索引
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at)
    WITH (fillfactor=100, deduplicate_items=True);

-- 向量表索引（pgvector专用）
CREATE INDEX idx_document_embeddings_document_id ON document_embeddings(document_id);
CREATE INDEX idx_document_embeddings_embedding ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ==================== 函数和触发器 ====================

-- 自动更新updated_at字段的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要自动更新时间的表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 对话标题自动生成函数
CREATE OR REPLACE FUNCTION generate_conversation_title()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.title = '新对话' THEN
        -- 从第一条用户消息中提取前20个字符作为标题
        SELECT SUBSTRING(content FROM 1 FOR 20) INTO NEW.title
        FROM messages 
        WHERE conversation_id = NEW.id AND role = 'user'
        ORDER BY created_at ASC LIMIT 1;
        
        -- 如果提取失败，保持默认标题
        IF NEW.title IS NULL THEN
            NEW.title := '新对话';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER set_conversation_title AFTER INSERT ON conversations
    FOR EACH ROW EXECUTE FUNCTION generate_conversation_title();

-- ==================== 视图定义 ====================

-- 对话详情视图
CREATE VIEW conversation_details AS
SELECT 
    c.id,
    c.title,
    c.description,
    c.is_archived,
    c.created_at,
    c.updated_at,
    u.username,
    u.full_name,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_at
FROM conversations c
JOIN users u ON c.user_id = u.id
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY c.id, u.username, u.full_name;

-- 文档统计视图
CREATE VIEW document_stats AS
SELECT 
    d.id,
    d.title,
    d.filename,
    d.status,
    d.created_at,
    u.username,
    COUNT(de.id) as chunk_count
FROM documents d
JOIN users u ON d.user_id = u.id
LEFT JOIN document_embeddings de ON d.id = de.document_id
GROUP BY d.id, u.username;

-- ==================== 示例数据（可选） ====================

-- 插入测试用户（密码为：123456，使用bcrypt加密）
INSERT INTO users (username, email, password_hash, full_name) VALUES
('admin', 'admin@legal.com', '$2b$12$1CHH902i8.Y5DYlm.2M20OhsBJbmP5Uh/ZyL6tUwPHgPjsoRdJnCG', '系统管理员'),
('testuser', 'user@legal.com', '$2b$12$jnSy0OdIS7NOX6poMQbtou5uB4szUzZdDAur883CTR/mXlCjHVlEi', '测试用户');

-- 插入测试对话
INSERT INTO conversations (user_id, title) VALUES
((SELECT id FROM users WHERE username = 'testuser'), '劳动合同相关问题咨询');

-- 插入测试消息
INSERT INTO messages (conversation_id, role, content) VALUES
((SELECT id FROM conversations WHERE title = '劳动合同相关问题咨询'), 'user', '您好，我想咨询关于劳动合同解除的相关法律规定。'),
((SELECT id FROM conversations WHERE title = '劳动合同相关问题咨询'), 'assistant', '根据《劳动合同法》相关规定，劳动合同解除需要符合法定情形...');

-- ==================== 权限设置 ====================

-- 为应用用户授予权限（根据实际用户调整）
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO legal_assistant;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO legal_assistant;

-- 评论表结构（便于维护）
COMMENT ON TABLE users IS '系统用户表，存储用户认证信息';
COMMENT ON TABLE conversations IS '用户对话会话表，记录每次对话的基本信息';
COMMENT ON TABLE messages IS '对话消息表，存储用户和AI的对话内容';
COMMENT ON TABLE documents IS '知识库文档表，管理用户上传的法律文档';
COMMENT ON TABLE document_embeddings IS '文档向量表，存储文档分块的向量化表示';

-- 设置表所有者
ALTER TABLE documents OWNER TO legal_assistant;

COMMENT ON COLUMN users.password_hash IS '使用bcrypt加密的密码哈希';
COMMENT ON COLUMN document_embeddings.embedding IS 'OpenAI text-embedding-ada-002模型生成的1536维向量';

-- 完成数据库初始化
SELECT '数据库初始化完成' as status;