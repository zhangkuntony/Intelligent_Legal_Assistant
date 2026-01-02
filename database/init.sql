-- 智能法律助手数据库初始化脚本
-- 执行顺序：先创建数据库，然后执行此脚本

-- 1. 创建数据库（需要在外部执行）
CREATE DATABASE legal_assistant;

-- 2. 连接到数据库后执行以下语句

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 创建数据库用户（如果需要）
CREATE USER legal_assistant WITH PASSWORD 'legal_assistant_123456';
GRANT ALL PRIVILEGES ON DATABASE legal_assistant TO legal_assistant;

-- 设置搜索路径
SET search_path TO public;

-- 执行主数据库架构
\i schema.sql

-- 输出初始化完成信息
SELECT '数据库初始化完成，请检查以下扩展是否已启用：' as message;
SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');

-- 检查表创建情况
SELECT '已创建的表：' as message;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;