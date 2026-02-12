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
    status VARCHAR(20) DEFAULT 'processing' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,
    total_chunks INTEGER DEFAULT 0,
    processed_chunks INTEGER DEFAULT 0,
    meta_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(2000)
);

-- 文档分类表
CREATE TABLE document_category (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_name VARCHAR(50) NOT NULL,
    category_code VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

-- 文档分类表索引
CREATE INDEX idx_document_category_code ON document_category(category_code);
CREATE INDEX idx_document_category_name ON document_category(category_name);
CREATE INDEX idx_document_category_created_at ON document_category(created_at);

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

CREATE TRIGGER update_document_category_updated_at BEFORE UPDATE ON document_category
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

-- 插入文档分类初始数据
INSERT INTO document_category (category_name, category_code, description) VALUES
('合同文件', 'contract', '各类合同文件，包括劳动合同、租赁合同、买卖合同等'),
('案例资料', 'case', '法律案例资料，包括法院判决、仲裁裁决等'),
('法律文书', 'legal', '各类法律文书，包括起诉状、答辩状、申请书等'),
('法规法条', 'laws', '法律法规条文，包括法律、法规、规章等');

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
COMMENT ON TABLE document_category IS '文档分类表，管理文档的分类信息';
COMMENT ON TABLE document_embeddings IS '文档向量表，存储文档分块的向量化表示';

-- 设置表所有者
ALTER TABLE document_category OWNER TO legal_assistant;

-- 设置表所有者
ALTER TABLE documents OWNER TO legal_assistant;

COMMENT ON COLUMN users.password_hash IS '使用bcrypt加密的密码哈希';
COMMENT ON COLUMN document_embeddings.embedding IS 'OpenAI text-embedding-ada-002模型生成的1536维向量';

-- ==================== 角色和权限管理 ====================

-- 角色表
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,  -- 是否为系统内置角色（不可删除）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 权限表
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(100) NOT NULL UNIQUE,
    module VARCHAR(50) NOT NULL,  -- 模块名称（如：user, document, chat等）
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 用户-角色关联表
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(id),
    UNIQUE(user_id, role_id)
);

-- 角色-权限关联表
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

-- ==================== 索引 ====================

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission_id ON role_permissions(permission_id);
CREATE INDEX idx_roles_code ON roles(code);
CREATE INDEX idx_permissions_code ON permissions(code);

-- ==================== 触发器 ====================

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== 初始数据 ====================

-- 插入默认角色
INSERT INTO roles (name, code, description, is_system) VALUES
('超级管理员', 'admin', '系统最高权限管理员，拥有所有权限', TRUE),
('普通用户', 'user', '普通系统用户，基本权限', FALSE),
('访客', 'guest', '只读权限用户', FALSE);

-- 插入基础权限
INSERT INTO permissions (name, code, module, description) VALUES
-- 用户管理权限
('查看用户', 'user:view', 'user', '查看用户列表和详情'),
('创建用户', 'user:create', 'user', '创建新用户'),
('编辑用户', 'user:update', 'user', '编辑用户信息'),
('删除用户', 'user:delete', 'user', '删除用户'),
-- 文档管理权限
('查看文档', 'document:view', 'document', '查看文档列表和详情'),
('上传文档', 'document:upload', 'document', '上传新文档'),
('编辑文档', 'document:update', 'document', '编辑文档信息'),
('删除文档', 'document:delete', 'document', '删除文档'),
('处理文档', 'document:process', 'document', '处理文档生成向量'),
-- 对话管理权限
('查看对话', 'chat:view', 'chat', '查看对话历史'),
('发送消息', 'chat:send', 'chat', '发送聊天消息'),
('删除对话', 'chat:delete', 'chat', '删除对话记录'),
-- 角色管理权限
('查看角色', 'role:view', 'role', '查看角色列表和详情'),
('创建角色', 'role:create', 'role', '创建新角色'),
('编辑角色', 'role:update', 'role', '编辑角色信息和权限'),
('删除角色', 'role:delete', 'role', '删除角色'),
('分配角色', 'role:assign', 'role', '为用户分配角色'),
-- 系统管理权限
('系统配置', 'system:config', 'system', '系统配置管理'),
('数据统计', 'system:stats', 'system', '查看数据统计'),
('日志查看', 'system:log', 'system', '查看系统日志');

-- 为超级管理员分配所有权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE code = 'admin'),
    id
FROM permissions;

-- 为普通用户分配基础权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE code = 'user'),
    id
FROM permissions
WHERE code IN ('document:view', 'document:upload', 'chat:view', 'chat:send');

-- 为访客分配只读权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE code = 'guest'),
    id
FROM permissions
WHERE code IN ('document:view', 'chat:view');

-- 为现有测试用户分配普通用户角色
INSERT INTO user_roles (user_id, role_id)
SELECT
    u.id,
    (SELECT id FROM roles WHERE code = 'user')
FROM users u
WHERE u.username = 'testuser';

-- 为管理员用户分配超级管理员角色
INSERT INTO user_roles (user_id, role_id)
SELECT
    u.id,
    (SELECT id FROM roles WHERE code = 'admin')
FROM users u
WHERE u.username = 'admin';

-- 添加表注释
COMMENT ON TABLE roles IS '角色表，存储系统角色信息';
COMMENT ON TABLE permissions IS '权限表，存储系统权限定义';
COMMENT ON TABLE user_roles IS '用户-角色关联表，多对多关系';
COMMENT ON TABLE role_permissions IS '角色-权限关联表，多对多关系';


-- 完成数据库初始化
SELECT '数据库初始化完成' as status;