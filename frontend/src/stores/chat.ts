import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { chatService } from "@/services/chat";
import type {
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    CreateConversationData,
    IntentClassification,
    Message,
    QuestionAnalysis,
    RetrievedDoc,
    StreamMessage
} from '@/types/chat'

/**
 * 聊天状态管理 Store
 * 管理对话、消息、发送状态等核心功能
 */
export const useChatStore = defineStore('chat', () => { 
    // ========================================
    // State - 状态定义
    // ========================================

    /** 对话列表 */
    const conversations = ref<ConversationDetail[]>([])

    /** 当前激活的对话 */
    const currentConversationId = ref<string | null>(null)

    /** 当前对话的详细消息 */
    const messages = ref<Message[]>([])

    /** 消息加载状态 */
    const loadingMessages = ref(false)

    /** 消息发送状态 */
    const sendingMessage = ref(false)

    /** 对话列表加载状态 */
    const loadingConversations = ref(false)

    /** 最后的聊天响应 */
    const lastChatResponse = ref<ChatResponse | null>(null)

    /** 错误信息 */
    const error = ref<string | null>(null)

    /** 分页参数 */
    const pagination = ref({
        skip: 0,
        limit: 20,
        hasMore: true
    })

    // ========================================
    // Getters - 计算属性
    // ========================================

    /** 当前对话对象 */
    const currentConversation = computed(() => {
        if (!currentConversationId.value)
            return null

        return conversations.value.find(c => c.id === currentConversationId.value) || null
    })

    /** 当前对话的消息数量 */
    const currentMessageCount = computed(() => messages.value.length)

    /** 按时间排序的消息（最新的在最前面） */
    const sortedMessages = computed(() => {
        return [...messages.value].sort((a, b) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
    })

    /** 对话总数 */
    const totalConversations = computed(() => conversations.value.length)

    /** 是否有错误 */
    const hasError = computed(() => error.value !== null)

    /** 最后一条用户消息 */
    const lastUserMessage = computed(() => {
        const userMessages = messages.value.filter(m => m.role === 'user')
        return userMessages.length > 0 ? userMessages.at(-1) : null
    })

    /** 最后一条AI消息 */
    const lastAssistantMessage = computed(() => {
        const assistantMessages = messages.value.filter(m => m.role === 'assistant')
        return assistantMessages.length > 0 ? assistantMessages.at(-1) : null
    })

    // ========================================
    // Actions - 异步操作
    // ========================================

    /**
     * 加载对话列表
     * @param refresh 是否刷新（重置分页）
     */
    const loadConversations = async (refresh = false) => {
        try {
            loadingConversations.value = true
            error.value = null

            // 如果刷新，重置分页
            if (refresh) {
                pagination.value = { skip: 0, limit: 20, hasMore: true }
            }

            // 加载对话列表
            const data = await chatService.getConversations(
                pagination.value.skip,
                pagination.value.limit
            )

            if (refresh) {
                // 刷新模式：完全替换
                conversations.value = data
            } else {
                // 加载更多模式：追加
                conversations.value = [...conversations.value, ...data]
            }

            // 更新分页状态
            pagination.value.hasMore = data.length === pagination.value.limit
            pagination.value.skip += data.length
        } catch (err: any) {
            console.error('加载对话列表失败：', err)
            error.value = err.message || '加载对话失败'
            throw err
        } finally {
            loadingConversations.value = false
        }
    }

    /**
     * 创建新对话
     * @param data 对话数量
     * @returns 创建的对话
     */
    const createConversation = async (data?: CreateConversationData) => {
        try {
            error.value = null
            const conversation = await chatService.createConversation(data)

            // 添加到列表头部
            conversations.value.unshift(conversation)

            // 自动切换到新对话
            currentConversationId.value = conversation.id
            messages.value = []
            return conversation
        } catch (err: any) {
            console.error('创建对话失败：', err)
            error.value = err.message || '创建对话失败'
            throw err
        }
    }

    /**
     * 切换到指定对话
     * @param conversationId 对话ID
     */
    const switchConversation = async (conversationId: string) => {
        try {
            error.value = null
            loadingMessages.value = true

            // 切换对话ID
            currentConversationId.value = conversationId

            // 加载对话详情和消息
            const data = await chatService.getConversation(conversationId)

            // 更新消息列表
            messages.value = data.messages || []

            // 构建对话对象
            const conversationObj = {
                id: data.id,
                user_id: data.user_id,
                title: data.title,
                description: data.description,
                is_archived: data.is_archived ?? false,
                message_count: data.message_count ?? 0,
                last_message_at: data.last_message_at,
                created_at: data.created_at,
                updated_at: data.updated_at
            }

            // 查找对话在列表中的索引
            const index = conversations.value.findIndex(c => c?.id === conversationId)

            if (index === -1) {
                // 添加新对话到列表
                conversations.value.unshift(conversationObj)
            } else {
                // 更新现有对话的信息
                conversations.value[index] = conversationObj
            }

            // 保存到本地缓存
            saveConversationToCache(conversationId, data.messages)
        } catch (err: any) {
            console.error('切换对话失败:', err)
            error.value = err.message || '加载对话失败'
            throw err
        } finally {
            loadingMessages.value = false
        }
    }

    /**
     * 发送消息
     * @param content 消息内容
     * @param conversationId 对话ID （可选，如果不提供则创建新对话）
     */
    const sendMessage = async (content: string, conversationId?: string) => {
        try {
            sendingMessage.value = true
            error.value = null

            // 构建请求
            const reqeust: ChatRequest = {
                content,
                conversation_id: conversationId || currentConversationId.value || undefined,
                top_k: 5,
                include_thinking: false,
            }

            // 乐观更新：立即在本地显示用户消息
            const tempMessageId = `temp-${Date.now()}`                  // 临时ID
            const userMessage: Message = {
                id: tempMessageId,
                conversation_id: conversationId || currentConversationId.value || '',
                role: 'user',
                content: content,
                tokens_used: 0,
                created_at: new Date().toISOString(),
            }

            // 立即添加用户消息到列表
            messages.value.push(userMessage)

            // 更新对话的 message_count
            const convIndex = conversations.value.findIndex(
                c => c.id === (conversationId || currentConversationId.value)
            )
            if (convIndex !== -1) {
                conversations.value[convIndex].message_count++
                conversations.value[convIndex].last_message_at = userMessage.created_at
            }

            // 调用API发送消息
            const response = await chatService.sendMessage(reqeust)

            // 更新最后响应
            lastChatResponse.value = response

            // 保存响应到本地缓存
            if (response.conversation_id) {
                saveChatResponseToCache(response.conversation_id, response)
            }

            // 重新加载当前对话的消息列表
            if (currentConversationId.value === response.conversation_id) {
                await loadConversationMessages(currentConversationId.value, false)
            }

            // 更新对话在列表中的位置（置顶）
            moveConversationToTop(response.conversation_id)
            return response
        } catch (err: any) { 
            console.error('发送消息失败：', err)
            error.value = err.message || '发送消息失败'
            throw err
        } finally { 
            sendingMessage.value = false
        }
    }

    /**
     * 流式发送消息
     * @param content 消息内容
     * @param conversationId 对话ID
     * @param onContentChunk 内容块的回调
     */
    const sendMessageStream = async (
        content: string,
        conversationId?: string,
        onContentChunk?: (chunk: string) => void
    ) => {
        try {
            sendingMessage.value = true
            error.value = null

            // 构建请求
            const request: ChatRequest = {
                content,
                conversation_id: conversationId || currentConversationId.value || undefined,
                top_k: 5,
                include_thinking: true,
            }

            // 乐观更新：立即在本地显示用户消息
            const tempUserId = `temp-user-${Date.now()}`
            const userMessage: Message = {
                id: tempUserId,
                conversation_id: conversationId || currentConversationId.value || '',
                role: 'user',
                content: content,
                tokens_used: 0,
                created_at: new Date().toISOString(),
            }

            messages.value.push(userMessage)

            // 更新对话的 message_count
            const convIndex = conversations.value.findIndex(
                c => c.id === (conversationId || currentConversationId.value)
            )
            if (convIndex !== -1) {
                conversations.value[convIndex].message_count++
                conversations.value[convIndex].last_message_at = userMessage.created_at
            }

            // 创建临时AI消息对象（流式填充内容）
            const tempAiId = `temp-ai-${Date.now()}`
            let fullContent = ''

            const tempAiMessage: Message = {
                id: tempAiId,
                conversation_id: conversationId || currentConversationId.value || '',
                role: 'assistant',
                content: '',
                tokens_used: 0,
                meta_data: {
                    _isStreaming: true
                },
                created_at: new Date().toISOString()
            }

            messages.value.push(tempAiMessage)

            // 辅助函数：更新临时AI消息并触发响应式更新
            const updateTempMessage = (updates: Partial<Message>) => {
                const aiMessageIndex = messages.value.findIndex(m => m.id === tempAiId)
                if (aiMessageIndex !== -1) {
                    messages.value[aiMessageIndex] = {
                        ...messages.value[aiMessageIndex],
                        ...updates
                    }
                }
            }

            // 调用流式API
            await chatService.sendMessageStream(
                request, 
                (chunk: StreamMessage) => {
                    if (chunk.type === 'content' && chunk.content) {
                        fullContent += chunk.content
                        updateTempMessage({ content: fullContent })

                        // 调用内容块回调
                        onContentChunk?.(chunk.content)
                    } else if (chunk.type === 'intent' && chunk.data) {
                        updateTempMessage({
                            meta_data: {
                                ...tempAiMessage.meta_data,
                                intent: chunk.data
                            }
                        })
                    } else if (chunk.type === 'analysis' && chunk.data) { 
                        updateTempMessage({
                            meta_data: {
                                ...tempAiMessage.meta_data,
                                analysis: chunk.data
                            }
                        })
                    } else if (chunk.type === 'retrieved_docs' && chunk.data) { 
                        updateTempMessage({
                            meta_data: {
                                ...tempAiMessage.meta_data,
                                retrieved_docs: chunk.data
                            }
                        })
                    } else if (chunk.type === 'done') { 
                        updateTempMessage({ tokens_used: chunk.tokens_used || 0 })
                    } else if (chunk.type === 'error') { 
                        throw new Error(chunk.message || '生成回复失败')
                    }
                },

                async (finalResponse) => {
                    // 移除临时消息的 _isStreaming 标记
                    const aiMessageIndex = messages.value.findIndex(m => m.id === tempAiId)
                    if (aiMessageIndex !== -1) {
                        const { _isStreaming, ...cleanMetaData } = messages.value[aiMessageIndex].meta_data || {}
                        messages.value[aiMessageIndex] = {
                            ...messages.value[aiMessageIndex],
                            meta_data: cleanMetaData
                        }
                    }

                    // 重新获取对话信息以获取更新后的标题
                    const targetConversationId = conversationId || currentConversationId.value
                    if (targetConversationId) {
                        try {
                            // 调用API获取最新的对话详情（包含更新后的标题）
                            const conversationData = await chatService.getConversation(targetConversationId)

                            // 更新对话列表中的标题
                            const convIndex = conversations.value.findIndex(c => c.id === targetConversationId)
                            if (convIndex !== -1) {
                                conversations.value[convIndex] = {
                                    ...conversations.value[convIndex],
                                    title: conversationData.title,
                                    message_count: conversationData.message_count,
                                    last_message_at: conversationData.last_message_at,
                                    updated_at: conversationData.updated_at
                                }
                            }

                            // 如果是当前对话，将对话置顶
                            moveConversationToTop(targetConversationId)
                        } catch (err) { 
                            console.warn('获取对话详情失败，保持原标题：', err)
                            // 即使失败也要置顶对话
                            moveConversationToTop(targetConversationId)
                        }
                    } else {
                        console.warn('当前对话ID为空，无法更新对话位置')
                    }
                },
                (error) => {
                    throw error
                }
            )
        } catch (err: any) {
            console.error('流式发送消息失败：', err)
            error.value = err.message || '发送消息失败'

            // 移除临时消息
            const aiIndex = messages.value.findIndex(m => m.id.startsWith('temp-ai-'))
            if (aiIndex !== -1) {
                messages.value.splice(aiIndex, 1)
            }

            throw err
        } finally { 
            sendingMessage.value = false
        }
    }

    /**
     * 重新生成回复（使用相同的上下文）
     * @param messageId 原始消息ID
     */
    const regenerateResponse = async (messageId: string) => { 
        try {
            sendingMessage.value = true
            error.value = null

            // 找到该消息之前的所有消息作为上下文
            const messageIndex = messages.value.findIndex(m => m.id === messageId)
            if (messageIndex === -1) {
                throw new Error('未找到消息')
            }

            // 获取用户消息
            const userMessage = messages.value[messageIndex]
            if (userMessage.role !== 'user') {
                throw new Error('只能重新生成用户消息的回复')
            }

            // 重新发送相同的用户消息
            await sendMessage(userMessage.content, userMessage.conversation_id)
        } catch (err: any) { 
            console.error('重新生成回复失败：', err)
            error.value = err.message || '重新生成回复失败'
            throw err
        }
    }

    /**
     * 删除对话
     * @param conversationId 对话ID
     */
    const deleteConversation = async (conversationId: string) => { 
        try {
            error.value = null

            await chatService.deleteConversation(conversationId)

            // 从列表中删除
            conversations.value = conversations.value.filter(c => c.id !== conversationId)

            // 如果删除的是当前对话，清空消息
            if (currentConversationId.value === conversationId) {
                messages.value = []
                currentConversationId.value = null
            }

            // 清除本地缓存
            removeConversationFromCache(conversationId)
        } catch (err: any) { 
            console.error('删除对话失败：', err)
            error.value = err.message || '删除对话失败'
            throw err
        }
    }

    /**
     * 批量删除对话
     * @param conversationIds 对话ID列表
     */
    const batchDeleteConversations = async (conversationIds: string[]) => { 
        try {
            error.value = null

            const result = await chatService.batchDeleteConversations(conversationIds)

            // 从列表中删除成功的对话
            conversations.value = conversations.value.filter(
                c => !result.success.includes(c.id)
            )

            // 如果删除的包含当前对话，清空消息
            if (currentConversationId.value && result.success.includes(currentConversationId.value)) {
                messages.value = []
                currentConversationId.value = null
            }

            // 清除所有相关缓存
            conversationIds.forEach(id => removeConversationFromCache(id))
            return result
        } catch (err: any) { 
            console.error('批量删除对话失败：', err)
            error.value = err.message || '批量删除对话失败'
            throw err
        }
    }

    /**
     * 更新对话信息
     * @param conversationId 对话ID
     * @param title 新标题（可选）
     * @param description 新描述（可选）
     */
    const updateConversation = async (
        conversationId: string,
        title?: string,
        description?: string
    ) => {
        try {
            error.value = null

            const result = await chatService.updateConversation(
                conversationId,
                title,
                description
            )

            // 更新列表中的对话信息
            const index = conversations.value.findIndex(c => c.id === conversationId)
            if (index !== -1) {
                conversations.value[index] = {
                    ...conversations.value[index],
                    ...result.conversation
                }
            }
            return result.conversation
        } catch (err: any) { 
            console.error('更新对话失败：', err)
            error.value = err.message || '更新对话失败'
            throw err
        }
    }

    /**
     * 搜索对话
     * @param keyword 搜索关键词
     */
    const searchConversations = async (keyword: string) => {
        try {
            error.value = null
            
            const results = await chatService.searchConversations(
                keyword,
                0,
                100
            )

            return results
        } catch (err: any) { 
            console.error('搜索对话失败：', err)
            error.value = err.message || '搜索对话失败'
            throw err
        }
    }

    /**
     * 加载更多对话
     */
    const loadMoreConversations = async () => { 
        if (!pagination.value.hasMore || loadingConversations.value) {
            return
        }

        await loadConversations(false)
    }

    /**
     * 清除错误
     */
    const clearError = () => { 
        error.value = null
    }

    // ========================================
    // Private Helpers - 辅助方法
    // ========================================

    /**
     * 加载对话消息（带缓存）
     * @param conversationId 对话ID
     * @param useCache 是否使用缓存
     */
    const loadConversationMessages = async (
        conversationId: string,
        useCache = true
    ) => {
        try {
            // 尝试从缓存加载
            if (useCache) {
                const cached = getConversationFromCache(conversationId)
                if (cached) {
                    messages.value = cached
                    return
                }
            }

            // 从API加载
            const data = await chatService.getMessages(conversationId, 100)
            messages.value = data.messages

            // 保存到缓存
            saveConversationToCache(conversationId, data.messages)
        } catch (err: any) { 
            console.error('加载消息失败：', err)
            throw err
        }
    }

    /**
     * 将对话移到列表顶部
     * @param conversationId 对话ID
     */
    const moveConversationToTop = (conversationId: string) => { 
        const index = conversations.value.findIndex(c => c.id === conversationId)
        if (index > 0) {
            const [conversation] = conversations.value.splice(index, 1)
            conversations.value.unshift(conversation)
        }
    }

    /** 
     * 从本地缓存获取对话
     * @param conversationId 对话ID
     * @returns 消息列表或null
     */
    const getConversationFromCache = (conversationId: string): Message[] | null => { 
        try {
            const cacheKey = `conversation_${conversationId}`
            const cached = localStorage.getItem(cacheKey)

            if (cached) {
                return JSON.parse(cached)
            }
            return null
        } catch (err: any) { 
            console.error('读取缓存失败：', err)
            return null
        }
    }

    /**
     * 保存对话到本地缓存
     * @param conversationId 对话ID
     * @param messages 消息列表
     */
    const saveConversationToCache = (
        conversationId: string, 
        messages: Message[]
    ) => {
        try {
            const cacheKey = `conversation_${conversationId}`
            localStorage.setItem(cacheKey, JSON.stringify(messages))
        } catch (err: any) { 
            console.error('保存缓存失败：', err)
        }
    }

    /**
     * 保存聊天响应到缓存
     * @param conversationId 对话ID
     * @param response 聊天响应
     */
    const saveChatResponseToCache = (
        conversationId: string, 
        response: ChatResponse
    ) => { 
        try {
            const cacheKey = `chat_response_${conversationId}`
            localStorage.setItem(cacheKey, JSON.stringify(response))
        } catch (err: any) { 
            console.error('保存缓存失败：', err)
        }
    }

    /**
     * 从缓存中移除对话
     * @param conversationId 对话ID
     */
    const removeConversationFromCache = (conversationId: string) => {
        try {
            const cacheKey = `conversation_${conversationId}`
            localStorage.removeItem(cacheKey)

            const responseCacheKey = `chat_response_${conversationId}`
            localStorage.removeItem(responseCacheKey)
        } catch (err: any) { 
            console.error('删除缓存失败：', err)

        }
    }

    /**
     * 清空所有对话缓存
     */
    const clearAllCache = () => {
        try {
            const keysToRemove: string[] = []

            // 收集所有对话相关的缓存键
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i)
                if (key && (key.startsWith('conversation_') || key.startsWith('chat_response_'))) {
                    keysToRemove.push(key)
                }
            }

            // 删除所有缓存键
            keysToRemove.forEach(key => localStorage.removeItem(key))
        } catch (err) {
            console.error('清空缓存失败:', err)
        }
    }

    /**
     * 提取RAG元数据
     * @param message 消息对象
     * @returns RAG元数据对象
     */
    const extractRAGMetadata = (message: Message): {
        intent?: IntentClassification
        analysis?: QuestionAnalysis
        retrieved_docs?: RetrievedDoc[]
        tokens_used?: number
    } => {
        if (!message.meta_data) {
            return {}
        }

        return {
            intent: message.meta_data.intent,
            analysis: message.meta_data.analysis,
            retrieved_docs: message.meta_data.retrieved_docs?.splice(0, 5),         // 只取前5个
            tokens_used: message.meta_data.tokens_used
        }
    }

    /**
     * 格式化消息时间
     * @param dateString ISO时间字符串
     * @param format 格式类型
     * @returns 格式化后的时间字符串
     */
    const formatMessageTime = (
        dateString: string,
        format: 'full' | 'short' | 'relative' = 'short'
    ): string => {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMins / 60)
        const diffDays = Math.floor(diffHours / 24)

        if (format === 'relative') {
            if (diffMins < 1) return '刚刚'
            if (diffMins < 60) return `${diffMins}分钟前`
            if (diffHours < 24) return `${diffHours}小时前`
            if (diffDays < 7) return `${diffDays}天前`
            return date.toLocaleDateString('zh-CN')
        }

        if (format === 'short') {
            const today = new Date()
            const isToday = date.toDateString() === today.toDateString()
            
            if (isToday) {
                return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
            }
            return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
        }

        // full format
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    /** 
     * 重置所有状态
     */
    const resetState = () => {
        conversations.value = []
        currentConversationId.value = null
        messages.value = []
        loadingMessages.value = false
        sendingMessage.value = false
        loadingConversations.value = false
        lastChatResponse.value = null
        error.value = null
        pagination.value = { skip: 0, limit: 20, hasMore: true }
    }

    // ========================================
    // Return - 导出状态和方法
    // ========================================
    
    return {
        // State
        conversations,
        currentConversationId,
        currentConversation,
        messages,
        loadingMessages,
        sendingMessage,
        loadingConversations,
        lastChatResponse,
        error,
        pagination,

        // Getters
        currentMessageCount,
        sortedMessages,
        totalConversations,
        hasError,
        lastUserMessage,
        lastAssistantMessage,

        // Actions
        loadConversations,
        createConversation,
        switchConversation,
        sendMessage,
        sendMessageStream,
        regenerateResponse,
        deleteConversation,
        batchDeleteConversations,
        updateConversation,
        searchConversations,
        loadMoreConversations,
        clearAllCache,
        resetState,

        // Helpers
        extractRAGMetadata,
        formatMessageTime,
        clearError
    }
})