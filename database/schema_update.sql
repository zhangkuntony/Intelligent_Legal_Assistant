/* ============================================================================
   schema.sql - Intelligent Legal Assistant
   PostgreSQL 13+ + pgvector
   1）embedding 1536维 
   2）支持共享团队知识库（workspaces + members + doc visibility + ACL）
   3）本地磁盘（documents.file_path / storage_uri 指向本地路径）
   4）向量 + 全文 BM25：Postgres 原生 FTS 排名不是严格 BM25，但我们用 tsvector+GIN + ts_rank_cd 做“BM25-like”，并提供组合检索函数；若要严格 BM25 需额外扩展/外部检索引擎 
============================================================================ */

SET search_path TO public;

/* ---------- 1) Extensions ---------- */
CREATE EXTENSION IF NOT EXISTS pgcrypto;        -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

/* ---------- 2) Enums ---------- */
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_role') THEN
    CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'doc_source_type') THEN
    CREATE TYPE doc_source_type AS ENUM ('upload', 'url', 'manual');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'doc_status') THEN
    CREATE TYPE doc_status AS ENUM ('uploaded', 'parsing', 'chunked', 'embedded', 'failed', 'deleted');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'workspace_role') THEN
    CREATE TYPE workspace_role AS ENUM ('owner', 'admin', 'member', 'viewer');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'doc_visibility') THEN
    CREATE TYPE doc_visibility AS ENUM ('private', 'workspace', 'public');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
    CREATE TYPE job_status AS ENUM ('pending', 'running', 'success', 'failed', 'canceled');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_type') THEN
    CREATE TYPE job_type AS ENUM ('parse', 'chunk', 'embed', 'reembed', 'delete_doc');
  END IF;
END$$;

/* ---------- 3) updated_at trigger ---------- */
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

/* ============================================================================
   4) Users（兼容你原有 users 思路）
============================================================================ */
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username      VARCHAR(50) UNIQUE NOT NULL,
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name     VARCHAR(100),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  is_superuser  BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

/* ============================================================================
   5) Team Knowledge Base：workspaces + members（团队共享知识库）
============================================================================ */
CREATE TABLE IF NOT EXISTS workspaces (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(100) NOT NULL,
  description TEXT,
  created_by  UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS trg_workspaces_updated_at ON workspaces;
CREATE TRIGGER trg_workspaces_updated_at
BEFORE UPDATE ON workspaces
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_workspaces_name ON workspaces(name);

CREATE TABLE IF NOT EXISTS workspace_members (
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role         workspace_role NOT NULL DEFAULT 'member',
  joined_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id);

/* ============================================================================
   6) Conversations + Messages（兼容原对话结构）
============================================================================ */
CREATE TABLE IF NOT EXISTS conversations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id  UUID REFERENCES workspaces(id) ON DELETE SET NULL,
  title         VARCHAR(200) NOT NULL DEFAULT '新对话',
  description   TEXT,
  is_archived   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at    TIMESTAMPTZ
);

DROP TRIGGER IF EXISTS trg_conversations_updated_at ON conversations;
CREATE TRIGGER trg_conversations_updated_at
BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_workspace ON conversations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);

CREATE TABLE IF NOT EXISTS messages (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role             message_role NOT NULL,
  content          TEXT NOT NULL,
  tokens_used      INTEGER NOT NULL DEFAULT 0,
  meta_data        JSONB,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- 自动设置会话标题：插入第一条 user 消息时覆盖“新对话”
CREATE OR REPLACE FUNCTION trg_autoset_conversation_title()
RETURNS TRIGGER AS $$
DECLARE
  cur_title TEXT;
BEGIN
  IF NEW.role = 'user' THEN
    SELECT title INTO cur_title FROM conversations WHERE id = NEW.conversation_id;
    IF cur_title = '新对话' THEN
      UPDATE conversations
      SET title = COALESCE(SUBSTRING(NEW.content FROM 1 FOR 20), '新对话')
      WHERE id = NEW.conversation_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_messages_autotitle ON messages;
CREATE TRIGGER trg_messages_autotitle
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION trg_autoset_conversation_title();

/* ============================================================================
   7) Document Categories（兼容原 document_category 逻辑）
============================================================================ */
CREATE TABLE IF NOT EXISTS document_categories (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         VARCHAR(50) NOT NULL,
  code         VARCHAR(50) NOT NULL UNIQUE,
  description  VARCHAR(200),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS trg_doc_categories_updated_at ON document_categories;
CREATE TRIGGER trg_doc_categories_updated_at
BEFORE UPDATE ON document_categories
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_doc_categories_name ON document_categories(name);

/* ============================================================================
   8) Documents（在原 documents 基础上补齐“workspace共享 + 本地磁盘 + 可控可追溯”）
============================================================================ */
CREATE TABLE IF NOT EXISTS documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 团队共享：文档归属workspace（团队知识库的核心）
  workspace_id      UUID REFERENCES workspaces(id) ON DELETE SET NULL,

  -- 兼容原逻辑：仍保留上传者/所有者（用于审计与私有文档）
  owner_user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  title             VARCHAR(200) NOT NULL,
  description       VARCHAR(2000),

  category_id       UUID REFERENCES document_categories(id) ON DELETE SET NULL,

  source_type       doc_source_type NOT NULL DEFAULT 'upload',
  source_url        TEXT,

  -- 本地磁盘存储：file_path 指向本地路径；storage_uri 可同file_path或未来切换对象存储
  original_filename VARCHAR(255) NOT NULL,
  mime_type         VARCHAR(100),
  file_path         VARCHAR(500) NOT NULL,
  storage_uri       VARCHAR(500),
  file_size         BIGINT NOT NULL DEFAULT 0,
  checksum          TEXT,

  -- 共享策略：private(仅owner) / workspace(团队成员) / public(公开)
  visibility        doc_visibility NOT NULL DEFAULT 'workspace',

  status            doc_status NOT NULL DEFAULT 'uploaded',
  processing_error  TEXT,

  total_chunks      INTEGER NOT NULL DEFAULT 0,
  processed_chunks  INTEGER NOT NULL DEFAULT 0,

  meta_data         JSONB,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at        TIMESTAMPTZ
);

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_documents_workspace ON documents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_documents_visibility ON documents(visibility);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category_id);
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);

-- 文档ACL：用于“跨workspace分享/指定用户授权”（补强权限模型）
CREATE TABLE IF NOT EXISTS document_acl (
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  permission   VARCHAR(20) NOT NULL DEFAULT 'read', -- read/write/admin
  granted_by   UUID REFERENCES users(id) ON DELETE SET NULL,
  granted_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (document_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_document_acl_user ON document_acl(user_id);

/* ============================================================================
   9) 兼容旧表：document_embeddings（保留，避免旧代码立刻挂）
   同时新增更标准的：versions + chunks + chunk_embeddings
============================================================================ */

-- 兼容保留：旧版“文档分块+embedding混合表”（不建议新代码继续写入）
CREATE TABLE IF NOT EXISTS document_embeddings (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index  INTEGER NOT NULL,
  chunk_content TEXT NOT NULL,
  embedding    VECTOR(1536),
  meta_data    JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_embeddings_doc ON document_embeddings(document_id, chunk_index);

-- 新版：文档版本（法律场景必要：可追溯引用来源版本）
CREATE TABLE IF NOT EXISTS document_versions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version         INTEGER NOT NULL,
  uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
  note            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(document_id, version)
);

DROP TRIGGER IF EXISTS trg_doc_versions_updated_at ON document_versions;
CREATE TRIGGER trg_doc_versions_updated_at
BEFORE UPDATE ON document_versions
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_doc_versions_doc ON document_versions(document_id);

-- 新版：chunk（RAG检索粒度） + 全文检索 tsvector
CREATE TABLE IF NOT EXISTS document_chunks (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id  UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  chunk_index          INTEGER NOT NULL,
  content              TEXT NOT NULL,
  content_tokens       INTEGER NOT NULL DEFAULT 0,
  meta_data            JSONB,

  -- 全文检索字段（Postgres FTS）
  content_tsv          TSVECTOR,

  created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(document_version_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_doc_chunks_version ON document_chunks(document_version_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_metadata_gin ON document_chunks USING GIN (meta_data);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_tsv_gin ON document_chunks USING GIN (content_tsv);

-- 维护 tsvector 的触发器（使用中文分词需要额外方案；这里用simple配置保证可跑通）
CREATE OR REPLACE FUNCTION trg_doc_chunks_tsvector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.content_tsv = to_tsvector('simple', COALESCE(NEW.content, ''));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_doc_chunks_tsv ON document_chunks;
CREATE TRIGGER trg_doc_chunks_tsv
BEFORE INSERT OR UPDATE OF content ON document_chunks
FOR EACH ROW EXECUTE FUNCTION trg_doc_chunks_tsvector();

-- 新版：embedding表（支持多模型；本作业默认 1536维）
CREATE TABLE IF NOT EXISTS chunk_embeddings (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id       UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
  embed_model    TEXT NOT NULL,
  embedding      VECTOR(1536),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(chunk_id, embed_model)
);

CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk ON chunk_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model ON chunk_embeddings(embed_model);

-- 向量索引（IVFFLAT）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='idx_chunk_embeddings_vector'
  ) THEN
    EXECUTE 'CREATE INDEX idx_chunk_embeddings_vector ON chunk_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)';
  END IF;
END$$;

/* ============================================================================
   10) RAG证据链：retrieval_runs + retrieval_results（法律场景关键）
============================================================================ */
CREATE TABLE IF NOT EXISTS retrieval_runs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_message_id  UUID REFERENCES messages(id) ON DELETE SET NULL,
  query_text       TEXT NOT NULL,
  filters          JSONB,
  top_k            INTEGER NOT NULL DEFAULT 5,
  score_threshold  DOUBLE PRECISION,
  embed_model      TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retrieval_runs_conv ON retrieval_runs(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS retrieval_results (
  run_id     UUID NOT NULL REFERENCES retrieval_runs(id) ON DELETE CASCADE,
  chunk_id   UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
  rank       INTEGER NOT NULL,
  vector_score DOUBLE PRECISION,
  text_score   DOUBLE PRECISION,
  fused_score  DOUBLE PRECISION,
  snippet    TEXT,
  PRIMARY KEY (run_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_retrieval_results_run_rank ON retrieval_results(run_id, rank);

/* ============================================================================
   11) Jobs + Audit Logs（工程化：异步处理与审计）
============================================================================ */
CREATE TABLE IF NOT EXISTS jobs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type        job_type NOT NULL,
  status      job_status NOT NULL DEFAULT 'pending',
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  payload     JSONB,
  error       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_doc ON jobs(document_id);

CREATE TABLE IF NOT EXISTS audit_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action        TEXT NOT NULL,
  target_type   TEXT,
  target_id     UUID,
  detail        JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

/* ============================================================================
   12) Views（便于前端/管理后台）
============================================================================ */
CREATE OR REPLACE VIEW conversation_details AS
SELECT
  c.id,
  c.user_id,
  c.workspace_id,
  c.title,
  c.description,
  c.is_archived,
  c.created_at,
  c.updated_at,
  u.username,
  u.full_name,
  COUNT(m.id) AS message_count,
  MAX(m.created_at) AS last_message_at
FROM conversations c
JOIN users u ON c.user_id = u.id
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.deleted_at IS NULL
GROUP BY c.id, u.username, u.full_name;

CREATE OR REPLACE VIEW document_latest_version AS
SELECT DISTINCT ON (document_id)
  document_id,
  id AS version_id,
  version,
  created_at
FROM document_versions
ORDER BY document_id, version DESC, created_at DESC;

CREATE OR REPLACE VIEW document_stats AS
SELECT
  d.id,
  d.workspace_id,
  d.owner_user_id,
  d.title,
  d.original_filename,
  d.status,
  d.visibility,
  d.created_at,
  u.username,
  COUNT(DISTINCT dv.id) AS version_count,
  COUNT(DISTINCT dc.id) AS chunk_count
FROM documents d
JOIN users u ON d.owner_user_id = u.id
LEFT JOIN document_versions dv ON d.id = dv.document_id
LEFT JOIN document_chunks dc ON dv.id = dc.document_version_id
WHERE d.deleted_at IS NULL
GROUP BY d.id, u.username;

/* ============================================================================
   13) Seed：文档分类（兼容你原 init.sql 的分类逻辑）
============================================================================ */
INSERT INTO document_categories (name, code, description)
VALUES
  ('合同文件', 'contract', '各类合同文件，包括劳动合同、租赁合同、买卖合同等'),
  ('案例资料', 'case', '法律案例资料，包括法院判决、仲裁裁决等'),
  ('法律文书', 'legal', '各类法律文书，包括起诉状、答辩状、申请书等'),
  ('法规法条', 'laws', '法律法规条文，包括法律、法规、规章等')
ON CONFLICT (code) DO NOTHING;

/* ============================================================================
   14) Hybrid Retrieval Helper（向量+全文融合的示例函数）
   注意：Postgres原生ts_rank不是严格BM25；这里提供“可跑通/可解释”的融合方式
============================================================================ */

-- 简单融合函数：fused = w_vec * (1 - cosine_distance) + w_text * ts_rank_cd
CREATE OR REPLACE FUNCTION rag_fuse_score(vec_similarity DOUBLE PRECISION,
                                         text_rank DOUBLE PRECISION,
                                         w_vec DOUBLE PRECISION DEFAULT 0.7,
                                         w_text DOUBLE PRECISION DEFAULT 0.3)
RETURNS DOUBLE PRECISION AS $$
BEGIN
  RETURN (w_vec * vec_similarity) + (w_text * text_rank);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

SELECT 'schema applied successfully' AS status;
