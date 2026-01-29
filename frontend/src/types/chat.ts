// 聊天相关类型定义

/**
 * 意图分类结果
 */
export interface IntentClassification {
  is_legal_related: boolean             // 是否为法律相关问题
  legal_category: string | null         // 法律领域
  confidence: number                    // 置信度 0-1
  suggested_topics: string[]            // 建议的相关话题
}

/**
 * 法律领域类型
 */
export type LegalCategory = 
  | 'civil'           // 民事
  | 'criminal'        // 刑事
  | 'commercial'      // 商事
  | 'administrative'  // 行政
  | 'intellectual_property'  // 知识产权
  | 'labor'           // 劳动
  | 'family'          // 婚姻家庭
  | 'real_estate'     // 房地产
  | 'tort'            // 侵权
  | 'contract'        // 合同
  | 'other'           // 其他


/**
 * 问题分析结果
 */
export interface QuestionAnalysis {
    core_issue: string                  // 核心问题
    legal_elements: string[]            // 法律要素
    key_entities: string[]              // 关键实体
    query_for_retrieval: string         // 优化的检索查询
    missing_info: string[]              // 缺失信息
}

/**
 * 实体提取结果
 */
export interface EntityExtraction {
    entity_type: string                 // 实体类型
    entity_value: string                // 实体值
    confidence: number                  // 提取置信度
}

/**
 * 检索到的文档片段
 */
export interface RetrievedDoc {
    document_id: string                 // 文档ID
    document_title: string              // 文档标题
    chunk_index: number                 // 分块索引
    chunk_content: string               // 分块内容
    score: number                       // 相似度分数 0-1
    metadata?: Record<string, any>      // 额外元数据
}

/**
 * 消息角色枚举
 */
export type MessageRole = 'user' | 'assistant' | 'system'

/**
 * 聊天请求
 */
export interface ChatRequest {
    content: string                     // 用户输入内容
    conversation_id?: string            // 对话ID（可选）
    include_thinking?: boolean          // 是否包含思考过程
    top_k?: number                      // 检索文档数量
}

/**
 * 聊天响应
 */
export interface ChatResponse {
    message_id: string                  // 消息ID
    conversation_id: string             // 对话ID
    content: string                     // AI生成的回答
    intent: IntentClassification        // 意图分类结果
    analysis: QuestionAnalysis          // 问题分析结果
    retrieved_docs: RetrievedDoc[]      // 检索到的相关文档
    tokens_used: number                 // 使用的token数量
    thinking_process?: string           // 思考过程（可选）
    created_at: string                  // 创建时间
}

/**
 * 创建对话数据
 */
export interface CreateConversationData {
    title?: string                       // 对话标题
    description?: string                 // 对话描述
}

/**
 * 对话详情
 */
export interface ConversationDetail {
    id: string
    user_id: string
    title: string
    description?: string
    is_archived: boolean
    message_count: number
    last_message_at?: string
    created_at: string
    updated_at: string
}

/**
 * 流式消息数据
 */
export interface StreamMessage {
    type: 'content' | 'thinking' | 'metadata' | 'done'
    content?: string                        // 消息内容
    thinking?: string                       // 思考过程
    metadata?: {
        intent?: IntentClassification
        analysis?: QuestionAnalysis
        retrieved_docs?: RetrievedDoc[]
        tokens_used?: number
    }
    error?: string                          // 错误信息 
}

/**
 * 搜索对话参数
 */
export interface SearchConversationParams {
    page?: number
    page_size?: number
    keyword?: string
    is_archived?: boolean
}

/**
 * API响应包装
 */
export interface ApiResponse<T = any> {
    data?: T
    message?: string
    error?: string
    code?: number
}