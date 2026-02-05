<template>
  <div class="chat-container"> 
    <!-- 侧边栏：对话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <h3>对话列表</h3>
        <el-button 
          type="primary" 
          size="small" 
          @click="handleCreateConversation"
          :loading="creatingConversation"
        >
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>

      <div class="conversation-list">
        <!-- 加载状态 -->
        <el-skeleton 
          v-if="loadingConversations && conversations.length === 0"
          :rows="5"
          animated
          style="padding: 20px;"
        />

        <!-- 对话列表-->
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conversation-item', {
            active: currentConversation?.id === conv.id,
            archived: conv.is_archived
          }]"
          @click="handleSwitchConversation(conv.id)"
        >
          <div class="conversation-title">{{ conv.title }}</div>
          <div class="conversation-meta">
            <span class="conversation-time">{{ formatTime(conv.last_message_at || conv.created_at) }}</span>
            <span class="conversation-count">{{ conv.message_count }}条消息</span>
          </div>
          <div class="conversation-actions">
            <el-button
              v-if="conv.id === currentConversation?.id"
              type="danger"
              text
              size="small"
              @click.stop="handleDeleteConversation(conv.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- 加载更多 -->
        <div
          v-if="pagination.hasMore && conversations.length > 0"
          class="load-more"
          @click="loadMoreConversations"
        >
          <el-button text size="small" :loading="loadingConversations">
            加载更多...
          </el-button>
        </div>
      </div>
    </div>

    <!-- 主对话区 -->
    <div class="chat-main"> 
      <!-- 头部 -->
      <div class="chat-header"> 
        <div class="header-left">
          <h3>{{ currentConversation?.title || '新对话' }}</h3>
          <el-tag
            v-if="currentConversation?.is_archived"
            type="info"
            size="small"
          >
            已归档
          </el-tag>
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            text
            @click="handleUpdateConversation"
            :disabled="!currentConversationId"
          >
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button
            type="danger"
            text
            @click="handleDeleteConversation(currentConversation?.id)"
            :disabled="!currentConversationId"
          >
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </div>
      </div>

      <!-- 消息展示区 -->
      <div class="chat-messages" ref="messagesContainer">
        <!-- 加载状态 -->
        <div v-if="loadingMessages" class="messages-loading">
          <el-skeleton :rows="3" animated />
        </div>

        <!-- 空状态 -->
        <div v-else-if="messages.length === 0" class="empty-state">
          <el-empty description="开始一段新的对话吧">
            <template #image>
              <el-icon :size="80"><ChatDotRound /></el-icon>
            </template>
          </el-empty>
        </div>

        <!-- 消息列表 -->
        <div v-else class="message-list">
          <div
            v-for="message in messages"
            :key="message.id"
            :class="['message-wrapper', message.role]"
          >
            <!-- 用户消息 -->
            <div v-if="message.role === 'user'" class="message user">
              <div class="message-avatar">
                <el-avatar :size="36" :icon="User" />
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="message-sender">用户</span>
                  <span class="message-time">{{ formatMessageTime(message.created_at) }}</span>
                </div>
                <div class="message-text">{{ message.content }}</div>
                <div v-if="message.tokens_used" class="message-tokens">
                  {{ message.tokens_used }} tokens
                </div>
              </div>
            </div>

            <!-- AI 消息 -->
            <div v-else class="message assistant">
              <div class="message-avatar">
                <el-avatar :size="36" :icon="ChatDotRound" style="background: #409EFF;" />
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="message-sender">AI法律助手</span>
                  <div class="message-header-right">
                    <span class="message-time">{{ formatMessageTime(message.created_at) }}</span>
                    <el-button
                      type="primary"
                      text
                      size="small"
                      @click="handleRegenerate(message.id)"
                      :disabled="sendingMessage"
                    >
                      <el-icon><Refresh /></el-icon>
                      重新生成
                    </el-button>
                  </div>
                </div>

                <!-- 思考过程 -->
                <div v-if="message.meta_data?.thinking_process" class="thinking-process">
                  <div class="thinking-header" @click="toggleThinking(message.id)">
                    <el-icon><View /></el-icon>
                    思考过程
                    <el-icon class="toggle-icon">
                      <component :is="thinkingExpanded[message.id] ? ArrowDown : ArrowRight" />
                    </el-icon>
                  </div>
                  <el-collapse-transition> 
                    <div v-show="thinkingExpanded[message.id]" class="thinking-content">
                      {{ message.meta_data?.thinking_process || '暂无思考过程' }}
                    </div>
                  </el-collapse-transition>
                </div>

                <!-- 意图分类 -->
                <div v-if="message.meta_data?.intent" class="intent-badge">
                  <el-tag
                    :type="message.meta_data.intent.is_legal_related ? 'success' : 'warning'"
                    size="small"
                  >
                    {{ message.meta_data.intent.is_legal_related ? '法律相关问题' : '非法律相关' }}
                  </el-tag>
                  <el-tag
                    v-if="message.meta_data.intent.legal_category"
                    type="info"
                    size="small"
                  >
                    {{ getLegalCategoryText(message.meta_data.intent.legal_category) }}
                  </el-tag>
                  <span class="intent-confidence">
                    置信度：{{ (message.meta_data.intent.confidence * 100).toFixed(1) }}%
                  </span>
                </div>

                <!-- 消息内容 -->
                <div class="message-text">{{ message.content }}</div>

                <!-- 来源文档引用 -->
                <div v-if="message.meta_data?.retrieved_docs?.length > 0" class="retrieved-docs">
                  <div class="docs-header">
                    <el-icon><Document /></el-icon>
                    参考文档({{ message.meta_data?.retrieved_docs.length }})
                    <el-button
                      text
                      size="small"
                      @click="toggleDocs(message.id)"
                    >
                      <el-icon>
                        <component :is="docsExpanded[message.id] ? ArrowDown : ArrowRight" />
                      </el-icon>
                    </el-button>
                  </div>
                  <el-collapse-transition> 
                    <div v-show="docsExpanded[message.id]" class="docs-list"> 
                      <div
                        v-for="(doc, index) in message.meta_data?.retrieved_docs"
                        :key="index"
                        class="doc-item"
                      >
                        <div class="doc-header">
                          <span class="doc-title">{{ doc.document_title }}</span>
                          <el-tag type="info" size="small">
                            相似度：{{ (doc.score * 100).toFixed(1) }}%
                          </el-tag>
                        </div>
                        <div class="doc-content">{{ doc.chunk_content }}</div>
                      </div>
                    </div>
                  </el-collapse-transition>
                </div>

                <!-- Token使用量 -->
                <div v-if="message.tokens_used" class="message-tokens">
                  <el-icon><DataLine /></el-icon>
                  使用了 {{ message.tokens_used }} tokens
                </div>

                <!-- 复制按钮 -->
                <div class="message-actions">
                  <el-button
                    type="primary"
                    text
                    size="small"
                    @click="copyToClipboard(message.content)"
                  >
                    <el-icon><CopyDocument /></el-icon>
                    复制
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 发送中状态 -->
        <div v-if="sendingMessage" class="message-wrapper">
          <div class="message assistant">
            <div class="message-avatar">
              <el-avatar :size="36" :icon="ChatDotRound" style="background: #409EFF;" />
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-sender">AI法律助手</span>
              </div>
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <div class="input-tools">
          <el-tooltip content="上传文件" placement="top">
            <el-button type="text" :icon="Upload" disabled></el-button>
          </el-tooltip>
          <el-tooltip content="语音输入" placement="top">
            <el-button type="text" :icon="Microphone" disabled></el-button>
          </el-tooltip>
          <el-tooltip content="清空对话" placement="top">
            <el-button
              type="text"
              :icon="Delete"
              @click="handleClearMessages"
              :disabled="messages.length === 0"
            />
          </el-tooltip>
        </div>
        <div class="input-container">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="请输入您的法律问题，我将为您专业解答..."
            @keydown.enter.ctrl="handleSendMessage"
            :disabled="!currentConversation || sendingMessage"
          />
          <el-button
            type="primary"
            :loading="sendingMessage"
            :disabled="!inputMessage.trim() || !currentConversation"
            @click="handleSendMessage"
            class="send-button"
          >
            发送
            <el-tooltip content="快捷键: Ctrl + Enter" placement="top">
              <el-icon style="margin-left: 4px;"><Position /></el-icon>
            </el-tooltip>
          </el-button>
        </div>
        <div class="input-hint">
          按 Ctrl + Enter 快速发送
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts"> 
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Upload,
  Microphone,
  Delete,
  Edit,
  ChatDotRound,
  User,
  Refresh,
  CopyDocument,
  View,
  Document,
  DataLine,
  ArrowDown,
  ArrowRight,
  Position
} from '@element-plus/icons-vue'
import { useChatStore } from '../stores/chat';
import { storeToRefs } from 'pinia';

// Store
const chatStore = useChatStore()
const {
  conversations,
  currentConversation,
  currentConversationId,
  error,
  lastChatResponse,
  loadingConversations,
  loadingMessages,
  messages,
  pagination,
  sendingMessage
} = storeToRefs(chatStore)

const {
  clearAllCache,
  createConversation,
  deleteConversation,
  formatMessageTime,
  loadConversations,
  regenerateResponse,
  sendMessage,
  switchConversation,
  updateConversation
} = chatStore

// Route & Router
const route = useRoute()
const router = useRouter()

// Local state
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const creatingConversation = ref(false)
const thinkingExpanded = ref<Record<string, boolean>>({})
const docsExpanded = ref<Record<string, boolean>>({})

// 法律领域映射
const legalCategoryMap: Record<string, string> = {
  'civil': '民事',
  'criminal': '刑事',
  'commercial': '商事',
  'administrative': '行政',
  'intellectual_property': '知识产权',
  'labor': '劳动',
  'family': '婚姻家庭',
  'real_estate': '房地产',
  'tort': '侵权',
  'contract': '合同',
  'other': '其他'
}

// 方法：格式化时间
const formatTime = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN')
}

// 方法：获取法律领域文本
const getLegalCategoryText = (category: string): string => {
  return legalCategoryMap[category] || category
}

// 方法：创建新对话
const handleCreateConversation = async () => {
  try {
    creatingConversation.value = true
    await createConversation({
      title: '新对话'
    })
    inputMessage.value = ''
    ElMessage.success('新对话已创建')
  } catch (error: any) {
    ElMessage.error(`创建对话失败: ${error.message}`)
  } finally {
    creatingConversation.value = false
  }
}

// 方法：切换对话
const handleSwitchConversation = async (conversationId: string) => {
  try {
    await switchConversation(conversationId)
    inputMessage.value = ''
    scrollToBottom()
  } catch (error: any) {
    ElMessage.error(`切换对话失败: ${error.message}`)
  }
}

// 方法：发送消息
const handleSendMessage = async () => { 
  if (!inputMessage.value.trim() || !currentConversationId.value) {
    return
  }

  const messageContent = inputMessage.value.trim()
  inputMessage.value = ''

  try {
    await sendMessage(messageContent, currentConversationId.value)
    scrollToBottom()
  } catch (error: any) {
    inputMessage.value = messageContent
    ElMessage.error(`发送消息失败: ${error.message}`)
  }
}

// 方法：重新生成回复
const handleRegenerate = async (messageId: string) => { 
  try {
    await regenerateResponse(messageId)
    scrollToBottom()
    ElMessage.success('已重新生成回复')
  } catch (error: any) {
    ElMessage.error(`重新生成回复失败: ${error.message}`)  
  }
}

// 方法：删除对话
const handleDeleteConversation = async (conversationId?: string) => { 
  if (!conversationId) {
    return
  }

  try {
    await ElMessageBox.confirm(
      '确定要删除这个对话吗？删除后无法恢复。',
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteConversation(conversationId)
    ElMessage.success('对话已删除')

    // 如果删除的是当前对话，创建新对话
    if (conversationId === currentConversationId.value) {
      await handleCreateConversation()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`删除对话失败: ${error.message}`)
    }    
  }
}

// 方法：更新对话信息
const handleUpdateConversation = async () => {
  if (!currentConversationId.value || !currentConversation.value?.id) {
    ElMessage.error('当前没有选择任何对话')
    return
  }

  try {
    const { value } = await ElMessageBox.prompt(
      '请输入新对话标题',
      '编辑对话',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: currentConversation.value?.title
      }
    )

    if (value) {
      await updateConversation(currentConversation.value.id, value)
      ElMessage.success('对话标题已更新')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`更新对话失败: ${error.message}`)
    }
  }
}

// 方法：清空当前对话消息
const handleClearMessages = () => {
  ElMessageBox.confirm(
    '确定要清空当前对话的所有消息吗？',
    '清空确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 这里可以添加清空消息的逻辑
    ElMessage.success('消息已清空')
  }).catch(() => {
    // 用户取消清空
  })
}

// 方法：加载更多对话
const loadMoreConversations = async () => {
  try {
    await loadConversations(false)
  } catch (error: any) {
    ElMessage.error(`加载对话失败: ${error.message}`)
  }
}

// 方法：复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// 方法：切换思考过程显示
const toggleThinking = (messageId: string) => {
  if (thinkingExpanded.value[messageId]) {
    thinkingExpanded.value[messageId] = false
  } else {
    thinkingExpanded.value[messageId] = true
  }
}

// 方法：切换文档列表显示
const toggleDocs = (messageId: string) => {
  if (docsExpanded.value[messageId]) {
    docsExpanded.value[messageId] = false
  } else {
    docsExpanded.value[messageId] = true
  }
}

// 方法：滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 生命周期：组件挂载
onMounted(async () => {
  try {
    // 加载对话列表
    await loadConversations(true)

    // 检查URL参数是否有对话ID
    const conversationId = route.params.id as string
    if (conversationId) {
      await handleSwitchConversation(conversationId)
    } else if (conversations.value.length > 0 && currentConversationId.value) {
      // 如果有对话但没有指定ID，使用第一个对话
      await handleSwitchConversation(currentConversationId.value)
    } else {
      // 如果没有任何对话，创建新对话
      await handleCreateConversation()
    }
  } catch (error: any) {
    ElMessage.error(`初始化失败：${error.message}`)
  }
})

// 监听路由变化
watch(() => route.params.id, async (newId) => {
  if (newId && typeof newId === 'string') {
    await handleSwitchConversation(newId)
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏样式 */
.chat-sidebar {
  width: 300px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
}

.sidebar-header h3 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 16px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
}

.conversation-item {
  position: relative;
  padding: 15px 20px;
  margin: 0 10px 5px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.conversation-item:hover {
  background: #ecf5ff;
}

.conversation-item.active {
  background: #409EFF;
}

.conversation-item.archived {
  opacity: 0.6;
}

.conversation-title {
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  opacity: 0.7;
}

.conversation-item.active .conversation-meta {
  color: rgba(255, 255, 255, 0.8);
}

.conversation-time {
  color: inherit;
}

.conversation-count {
  color: inherit;
}

.conversation-item.active .conversation-time,
.conversation-item.active .conversation-count {
  color: rgba(255, 255, 255, 0.8);
}

.conversation-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0;
  transition: opacity 0.3s;
}

.conversation-item:hover .conversation-actions {
  opacity: 1;
}

.conversation-item.active .conversation-actions {
  opacity: 1;
}

.load-more {
  text-align: center;
  padding: 10px;
}

/* 主对话区样式 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 消息区域样式 */
.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #fafafa;
  display: flex;
  flex-direction: column;
}

.messages-loading {
  padding: 20px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-wrapper {
  display: flex;
  width: 100%;
}

.message {
  display: flex;
  max-width: 80%;
  gap: 12px;
}

.message.user {
  margin-left: auto;
}

.message.assistant {
  margin-right: auto;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-sender {
  font-weight: 500;
  font-size: 14px;
  color: #303133;
}

.message-time {
  font-size: 12px;
  color: #909399;
}

.message-text {
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message.user .message-text {
  background: #1976d8;
  color: white;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.message.assistant .message-text {
  background: white;
  color: #303133;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 思考过程样式 */
.thinking-process {
  margin-bottom: 12px;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #409EFF;
  transition: all 0.3s;
}

.thinking-header:hover {
  background: #e0f2fe;
}

.toggle-icon {
  margin-left: auto;
}

.thinking-content {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
}

/* 意图分类标签 */
.intent-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.intent-confidence {
  font-size: 12px;
  color: #909399;
}

/* 来源文档样式 */
.retrieved-docs {
  margin-top: 12px;
}

.docs-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #409EFF;
  transition: all 0.3s;
}

.docs-header:hover {
  background: #e0f2fe;
}

.docs-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 3px solid #409EFF;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.doc-title {
  font-weight: 500;
  font-size: 14px;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  max-height: 150px;
  overflow-y: auto;
}

/* Token使用量 */
.message-tokens {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

/* 消息操作 */
.message-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

/* 打字动画 */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  align-items: center;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409EFF;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

/* 输入区域样式 */
.chat-input-area {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
  background: white;
}

.input-tools {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.input-container {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.input-container :deep(.el-textarea) {
  flex: 1;
}

.input-container :deep(.el-textarea__inner) {
  resize: none;
  font-family: inherit;
}

.send-button {
  height: 76px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.send-button :deep(.el-button__content) {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.input-hint {
  text-align: right;
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-sidebar {
    position: absolute;
    left: -300px;
    z-index: 100;
    height: 100%;
    transition: left 0.3s;
  }

  .chat-sidebar.open {
    left: 0;
  }

  .chat-header h3 {
    font-size: 16px;
  }

  .message {
    max-width: 95%;
  }
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar,
.conversation-list::-webkit-scrollbar,
.docs-content::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-thumb,
.conversation-list::-webkit-scrollbar-thumb,
.docs-content::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover,
.conversation-list::-webkit-scrollbar-thumb:hover,
.docs-content::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}
</style>