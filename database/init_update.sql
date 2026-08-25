/* ============================================================================
   init.sql - Intelligent Legal Assistant
   作用：创建数据库用户、数据库、授权（幂等执行）
============================================================================ */

-- 1) 创建角色/用户（不存在则创建）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'legal_assistant') THEN
    CREATE ROLE legal_assistant LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
  END IF;
END$$;

-- 2) 创建数据库（不存在则创建）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'legal_assistant') THEN
    CREATE DATABASE legal_assistant OWNER legal_assistant;
  END IF;
END$$;

-- 3) 授权（保险起见）
GRANT ALL PRIVILEGES ON DATABASE legal_assistant TO legal_assistant;
