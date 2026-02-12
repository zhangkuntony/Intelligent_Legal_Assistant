import { request } from './api'
import { API_CONFIG } from '@/config/api'
import type {
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationWithMessages,
    CreateConversationData,
    Message,
    IntentClassification,
    QuestionAnalysis,
    RetrievedDoc,
    StreamMessage
} from '@/types/chat'

/**
 * 聊天API服务
 * 提供与后端 /api/chat/* 端点交互的所有方法
 */
export const chatService = {
    /**
     * 发送消息并获取AI回复
     * 执行完整的RAG流程：意图识别、问题理解、文档检索、回答生成
     * 
     * @param data - 聊天请求参数
     * @returns 聊天响应，包含AI回答、意图分析、检索文档等
     * 
     * @example
     * ```typescript
     * const response = await chatService.sendMessage({
     *   content: '劳动合同解除需要哪些条件？',
     *   conversation_id: 'uuid',
     *   use_rag: true
     * })
     * ```
     */
    async sendMessage(data: ChatRequest): Promise<ChatResponse> {
        try {
            return await request.post<ChatResponse>(
                API_CONFIG.ENDPOINTS.CHAT.SEND,
                data
            )
        } catch (error) {
            console.error('发送消息失败：', error)
            throw new Error('发送消息失败，请稍后重试')
        }
    },

   /**
     * 流式发送消息
     * 使用 Server-Sent Events (SSE) 逐块接收AI回复
     * 
     * @param data - 聊天请求参数
     * @param onChunk - 收到每个数据块的回调
     * @param onComplete - 完成的回调
     * @param onError - 错误的回调
     * 
     * @example
     * ```typescript
     * await chatService.sendMessageStream(
     *   { content: '...', conversation_id: '...' },
     *   (chunk) => {
     *     if (chunk.type === 'content') {
     *       console.log('收到内容：', chunk.content)
     *     }
     *   },
     *   () => console.log('完成'),
     *   (err) => console.error(err)
     * )
     * ```
     */
    async sendMessageStream(
        data: ChatRequest,
        onChunk: (chunk: StreamMessage) => void,
        onComplete?: (finalResponse?: ChatResponse) => void,
        onError?: (error: Error) => void
    ): Promise<void> { 
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT.STREAM}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify(data)
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            const reader = response.body?.getReader()
            if (!reader) {
                throw new Error('无法获取响应流')
            }

            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })

                // 处理 SSE 数据（按\n\n分割）
                const lines = buffer.split('\n\n')
                buffer = lines.pop() || ''          // 保留未完成的部分

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6))
                            onChunk(data)

                            if (data.type === 'done' && onComplete) {
                                // 构造完整的ChatResponse
                                onComplete({
                                    message_id: '',
                                    conversation_id: data.conversation_id || '',
                                    content: '',
                                    intent: (data).intent || {} as any,
                                    analysis: (data).analysis || {} as any,
                                    retrieved_docs: [],
                                    tokens_used: data.tokens_used || 0,
                                    created_at: new Date().toISOString()
                                })
                            }
                        } catch (e) {
                            console.error('解析SSE数据失败：', e, line)
                        }
                    }
                }
            }

            if (onComplete)
                onComplete()
        } catch (error) {
            console.error('流式发送消息失败：', error)
            onError?.(error as Error)
            throw error
        }
    },

    /**
     * 获取用户的对话列表（默认获取当前用户的对话）
     * 
     * @param skip - 跳过的数量（分页用），默认0
     * @param limit - 返回的最大数量，默认20，最大100
     * @returns 对话列表，按更新时间倒序排列
     * 
     * @example
     * ```typescript
     * const { conversations, total } = await chatService.getConversations(0, 20)
     * ```
     */
    async getConversations(
        skip: number = 0,
        limit: number = 20
    ): Promise<{
        conversations: ConversationDetail[]
        total: number
    }> {
        // 默认行为：只获取当前用户的对话
        return this.getMyConversations(skip, limit)
    },

        /**
     * 获取用户的对话列表（所有用户，用于历史记录页面）
     * 
     * 如果当前用户有 chat:view 权限，则返回所有用户的对话；
     * 否则只返回当前用户自己的对话
     * 
     * @param skip - 跳过的数量（分页用），默认0
     * @param limit - 返回的最大数量，默认20，最大100
     * @returns 对话列表，按更新时间倒序排列
     * 
     * @example
     * ```typescript
     * const { conversations, total } = await chatService.getAllConversations(0, 20)
     * ```
     */
    async getAllConversations(
        skip: number = 0,
        limit: number = 20
    ): Promise<{
        conversations: ConversationDetail[]
        total: number
    }> {
        try {
            const response = await request.get<{
                conversations: ConversationDetail[]
                total: number
            }>(
                API_CONFIG.ENDPOINTS.CHAT.CONVERSATIONS,
                { params: { skip, limit } }
            )

            return {
                conversations: response.conversations || [],
                total: response.total || 0
            }
        } catch (error) {
            console.error('获取对话列表失败：', error)
            throw new Error('获取对话列表失败，请稍后重试')
        }
    },

    /**
     * 获取当前用户的对话列表（仅当前用户，用于对话页面）
     * 
     * 只返回当前登录用户自己的对话，不受 chat:view 权限影响
     * 
     * @param skip - 跳过的数量（分页用），默认0
     * @param limit - 返回的最大数量，默认20，最大100
     * @returns 对话列表，按更新时间倒序排列
     * 
     * @example
     * ```typescript
     * const { conversations, total } = await chatService.getMyConversations(0, 20)
     * ```
     */
    async getMyConversations(
        skip: number = 0,
        limit: number = 20
    ): Promise<{
        conversations: ConversationDetail[]
        total: number
    }> {
        try {
            const response = await request.get<{
                conversations: ConversationDetail[]
                total: number
            }>(
                `${API_CONFIG.BASE_URL}/api/chat/my-conversations`,
                { params: { skip, limit } }
            )

            return {
                conversations: response.conversations || [],
                total: response.total || 0
            }
        } catch (error) {
            console.error('获取对话列表失败：', error)
            throw new Error('获取对话列表失败，请稍后重试')
        }
    },

    /**
     * 创建新对话
     * 
     * @param data - 对话创建信息
     * @returns 创建的对话详情
     * 
     * @example
     * ```typescript
     * const conversation = await chatService.createConversation({
     *   title: '劳动合同咨询',
     *   description: '关于劳动合同解除的咨询'
     * })
     * ```
     */
    async createConversation(
        data?: CreateConversationData
    ): Promise<ConversationDetail> {
        try {
            return await request.post<ConversationDetail>(
                API_CONFIG.ENDPOINTS.CHAT.CONVERSATIONS,
                data
            )
        } catch (error) {
            console.error('创建对话失败：', error)
            throw new Error('创建对话失败，请稍后重试')
        }
    },

    /**
     * 获取对话详情及消息历史
     * 
     * @param conversationId - 对话ID
     * @returns 对话详情和消息列表
     * 
     * @example
     * ```typescript
     * const conversation = await chatService.getConversation('uuid')
     * ```
     */
    async getConversation(conversationId: string): Promise<ConversationWithMessages> {
        try {
            return await request.get(
                API_CONFIG.ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversationId)
            )
        } catch (error) {
            console.error('获取对话详情失败：', error)
            throw new Error('获取对话详情失败，请稍后重试')
        }
    },

    /**
     * 获取对话的消息历史（仅消息列表）
     * 
     * @param conversationId - 对话ID
     * @param limit - 返回的最大消息数量，默认50，最大200
     * @returns 消息列表
     * 
     * @example
     * ```typescript
     * const { messages, total_messages } = await chatService.getMessages('uuid', 50)
     * ```
     */
    async getMessages(
        conversationId: string,
        limit: number = 50
    ): Promise<{
        conversation_id: string
        total_messages: number
        messages: Message[]
    }> {
        try {
            return await request.get(
                API_CONFIG.ENDPOINTS.CHAT.CONVERSATION_MESSAGES(conversationId),
                { params: { limit } }
            )
        } catch (error) {
            console.error('获取消息列表失败：', error)
            throw new Error('获取消息列表失败，请稍后重试')
        }
    },

    /**
     * 删除对话
     * 注意：删除对话会级联删除该对话下的所有消息
     * 
     * @param conversationId - 对话ID
     * @returns 删除结果
     * 
     * @example
     * ```typescript
     * await chatService.deleteConversation('uuid')
     * ```
     */
    async deleteConversation(conversationId: string): Promise<{ message: string }> { 
        try {
            return await request.delete<{ message: string }>(
                API_CONFIG.ENDPOINTS.CHAT.DELETE_CONVERSATION(conversationId)
            )
        } catch (error) {
            console.error('删除对话失败：', error)
            throw new Error('删除对话失败，请稍后重试')
        }
    },

    /**
     * 更新对话信息（标题、描述）
     * 
     * @param conversationId - 对话ID
     * @param title - 新标题（可选）
     * @param description - 新描述（可选）
     * @returns 更新后的对话信息
     * 
     * @example
     * ```typescript
     * const result = await chatService.updateConversation('uuid', '新标题', '新描述')
     * ```
     */
    async updateConversation(
        conversationId: string,
        title?: string,
        description?: string
    ): Promise<{
        message: string
        conversation: {
            id: string
            title: string
            description: string | undefined
            updated_at: string
        }
    }> {
        try {
            const params: Record<string, string> = {}
            if (title !== undefined) params.title = title
            if (description !== undefined) params.description = description

            return await request.put(
                API_CONFIG.ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversationId),
                null,
                { params }
            )
        } catch (error) {
            console.error('更新对话信息失败：', error)
            throw new Error('更新对话信息失败，请稍后重试')
        }
    },

    /**
     * 搜索对话（扩展功能）
     * 支持按关键词搜索对话
     * 注意：后端可能需要额外实现搜索端点
     * 
     * @param keyword - 搜索关键词
     * @param skip - 跳过的数量
     * @param limit - 返回的数量
     * @returns 匹配的对话列表
     */
    async searchConversations(
        keyword: string,
        skip: number = 0,
        limit: number = 20
    ): Promise<ConversationDetail[]> {
        try {
            const { conversations } = await this.getConversations(skip, limit)

            if (!keyword.trim()) {
                return conversations
            }

            // 前端过滤：搜索标题
            const lowerKeyword = keyword.toLowerCase()
            return conversations.filter(conv => 
                conv.title.toLowerCase().includes(lowerKeyword) ||
                conv.description?.toLowerCase().includes(lowerKeyword)
            )
        } catch (error) {
            console.error('搜索对话失败：', error)
            throw new Error('搜索对话失败，请稍后重试')
        }
    },

    /**
     * 批量删除对话（扩展功能）
     * 
     * @param conversationIds - 对话ID列表
     * @returns 删除结果
     */
    async batchDeleteConversations(
        conversationIds: string[]
    ): Promise<{ success: string[]; failed: string[] }> {
        const success: string[] = []
        const failed: string[] = []

        for (const id of conversationIds) {
            try {
                await this.deleteConversation(id)
                success.push(id)
            } catch (error) {
                console.error(`删除对话${id}失败：`, error)
                failed.push(id)
            }
        }

        return { success, failed }
    },

    /**
     * 获取RAG检索结果详情（调试用）
     * 从消息的metadata中提取检索结果
     * 
     * @param message - 消息对象
     * @returns 检索结果和元数据
     */
    extractRAGMetadata(message: {
        meta_data?: any
    }): {
        intent?: IntentClassification
        anslysis?: QuestionAnalysis
        retrieved_docs?: RetrievedDoc[]
        tokens_used?: number  
    } {
        if (!message.meta_data) {
            return {}
        }

        return {
            intent: message.meta_data.intent,
            anslysis: message.meta_data.analysis,
            retrieved_docs: message.meta_data.retrieved_docs,
            tokens_used: message.meta_data.tokens_used
        }
    },

    /**
     * 格式化时间显示
     * 
     * @param dateString - ISO 8601时间字符串
     * @param format - 格式类型
     * @returns 格式化后的时间字符串
     */
    formatTime(dateString: string, format: 'full' | 'short' | 'relative' = 'short'): string {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMins / 60)
        const diffDays = Math.floor(diffHours / 24)

        if (format === 'relative') {
            if (diffMins < 1) {
                return '刚刚'
            } else if (diffMins < 60) {
                return `${diffMins} 分钟前`
            } else if (diffHours < 24) {
                return `${diffHours} 小时前`
            } else if (diffDays < 7) {
                return `${diffDays} 天前`
            } else {
                return date.toLocaleDateString('zh-CN')
            }
        }

        if (format === 'short') {
            const today = new Date()
            const isToday = date.toDateString() === today.toDateString()

            if (isToday) {
                return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
            } else {
                return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric'})
            }
        }

        // full format
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        })
    },


    /**
     * 获取会话分析统计数据
     * 
     * @returns 会话统计数据
     * 
     * @example
     * ```typescript
     * const analytics = await chatService.getConversationAnalytics()
     * ```
     */
    async getConversationAnalytics(): Promise<{
        stats: {
            total_conversations: number
            active_users: number
            avg_duration: number
        }
        trend: Array<{ date: string; count: number }>
        hot_topics: Array<{ topic: string; count: number }>
        recent_conversations: Array<{
            id: string
            user_id: string
            user_name: string
            title: string
            duration: number
            messages: number
            time: string
        }>
    }> {
        try {
            const response = await request.get(
                `${API_CONFIG.BASE_URL}/api/chat/analytics`
            )
            return response
        } catch (error) {
            console.error('获取会话分析数据失败：', error)
            throw new Error('获取会话分析数据失败，请稍后重试')
        }
    },


    /**
     * 获取Dashboard统计数据
     * 
     * @returns Dashboard统计数据
     * 
     * @example
     * ```typescript
     * const { stats, recent_conversations } = await chatService.getDashboardStats()
     * ```
     */
    async getDashboardStats(): Promise<{
        stats: {
            conversations: number
            documents: number
            totalTime: number
        }
        recent_conversations: Array<{
            id: string
            title: string
            time: string
        }>
    }> {
        try {
            const response = await request.get(
                `${API_CONFIG.BASE_URL}/api/chat/dashboard-stats`
            )
            return response
        } catch (error) {
            console.error('获取Dashboard统计数据失败：', error)
            throw new Error('获取Dashboard统计数据失败，请稍后重试')
        }
    }
}


export default chatService