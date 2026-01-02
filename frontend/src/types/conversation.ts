// 对话和消息相关类型定义

export interface Conversation {
  id: string
  user_id: string
  title: string
  description?: string
  is_archived: boolean
  created_at: string
  updated_at: string
  message_count?: number
  last_message_at?: string
  username?: string
  full_name?: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tokens_used: number
  metadata?: any
  created_at: string
}

export interface CreateConversationData {
  title?: string
  description?: string
}

export interface SendMessageData {
  content: string
  conversation_id?: string  // 如果为空，创建新对话
}

export interface ConversationResponse {
  conversation: Conversation
  messages: Message[]
}

export interface SearchConversationParams {
  page?: number
  page_size?: number
  keyword?: string
  is_archived?: boolean
}