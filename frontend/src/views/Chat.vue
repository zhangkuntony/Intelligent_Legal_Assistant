<template>
  <div class="chat-container">
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <h3>对话列表</h3>
        <el-button type="primary" size="small" @click="createNewChat">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conversation-item', { active: currentConversation?.id === conv.id }]"
          @click="switchConversation(conv.id)"
        >
          <div class="conversation-title">{{ conv.title }}</div>
          <div class="conversation-time">{{ conv.time }}</div>
        </div>
      </div>
    </div>

    <div class="chat-main">
      <div class="chat-header">
        <h3>{{ currentConversation?.title || '新对话' }}</h3>
        <div class="header-actions">
          <el-button type="primary" text @click="saveConversation">保存</el-button>
          <el-button type="danger" text @click="deleteConversation">删除</el-button>
        </div>
      </div>

      <div class="chat-messages" ref="messagesContainer">
        <div
          v-for="message in messages"
          :key="message.id"
          :class="['message', message.role]"
        >
          <div class="message-avatar">
            <el-avatar :size="32" :src="message.avatar" />
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-sender">{{ message.sender }}</span>
              <span class="message-time">{{ message.time }}</span>
            </div>
            <div class="message-text">{{ message.content }}</div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <div class="input-tools">
          <el-button type="text" :icon="Upload" title="上传文件"></el-button>
          <el-button type="text" :icon="Microphone" title="语音输入"></el-button>
        </div>
        <div class="input-container">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="请输入您的问题..."
            @keydown.enter="handleSendMessage"
          />
          <el-button
            type="primary"
            :loading="sending"
            @click="handleSendMessage"
            class="send-button"
          >
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Upload, Microphone } from '@element-plus/icons-vue'

const route = useRoute()

const conversations = ref([
  { id: 1, title: '劳动合同纠纷咨询', time: '2024-01-15 14:30' },
  { id: 2, title: '房屋租赁合同审查', time: '2024-01-14 10:15' },
  { id: 3, title: '知识产权保护咨询', time: '2024-01-12 16:45' }
])

const currentConversation = ref<any>(null)
const messages = ref<any[]>([])
const inputMessage = ref('')
const sending = ref(false)
const messagesContainer = ref<HTMLElement>()

const createNewChat = () => {
  const newConv = {
    id: Date.now(),
    title: '新对话',
    time: new Date().toLocaleString()
  }
  conversations.value.unshift(newConv)
  switchConversation(newConv.id)
}

const switchConversation = (id: number) => {
  const conv = conversations.value.find(c => c.id === id)
  if (conv) {
    currentConversation.value = conv
    // 模拟加载消息
    messages.value = [
      {
        id: 1,
        role: 'user',
        sender: '用户',
        avatar: '',
        content: '您好，我有一个关于劳动合同的问题需要咨询。',
        time: '14:30'
      },
      {
        id: 2,
        role: 'assistant',
        sender: 'AI法律助手',
        avatar: '',
        content: '您好！我很乐意为您解答劳动合同相关的问题。请您详细描述一下您遇到的具体问题。',
        time: '14:31'
      }
    ]
    scrollToBottom()
  }
}

const handleSendMessage = async () => {
  if (!inputMessage.value.trim()) return

  const userMessage = {
    id: Date.now(),
    role: 'user',
    sender: '用户',
    avatar: '',
    content: inputMessage.value,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  messages.value.push(userMessage)
  const messageText = inputMessage.value
  inputMessage.value = ''
  sending.value = true

  scrollToBottom()

  // 模拟AI回复
  setTimeout(() => {
    const aiMessage = {
      id: Date.now(),
      role: 'assistant',
      sender: 'AI法律助手',
      avatar: '',
      content: `关于"${messageText}"的问题，根据相关法律规定：\n\n1. 首先需要确认劳动合同的具体条款\n2. 其次要了解争议的具体情况\n3. 建议您提供更多详细信息以便给出更准确的建议`,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    messages.value.push(aiMessage)
    sending.value = false
    scrollToBottom()
  }, 2000)
}

const saveConversation = () => {
  ElMessage.success('对话已保存')
}

const deleteConversation = () => {
  if (currentConversation.value) {
    conversations.value = conversations.value.filter(c => c.id !== currentConversation.value.id)
    currentConversation.value = null
    messages.value = []
    ElMessage.success('对话已删除')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

onMounted(() => {
  const conversationId = route.params.id
  if (conversationId) {
    switchConversation(Number(conversationId))
  } else if (conversations.value.length > 0) {
    switchConversation(conversations.value[0].id)
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
}

.chat-sidebar {
  width: 300px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
}

.sidebar-header h3 {
  margin: 0 0 15px 0;
  color: #303133;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
}

.conversation-item {
  padding: 15px 20px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.3s;
}

.conversation-item:hover {
  background: #ecf5ff;
}

.conversation-item.active {
  background: #409EFF;
  color: white;
}

.conversation-title {
  font-weight: 500;
  margin-bottom: 5px;
}

.conversation-time {
  font-size: 12px;
  color: #909399;
}

.conversation-item.active .conversation-time {
  color: rgba(255, 255, 255, 0.8);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h3 {
  margin: 0;
  color: #303133;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #fafafa;
}

.message {
  display: flex;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  margin: 0 10px;
}

.message-content {
  max-width: 70%;
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message.user .message-content {
  background: #409EFF;
  color: white;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.message-sender {
  font-weight: 500;
  font-size: 14px;
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
}

.message-text {
  line-height: 1.5;
  white-space: pre-wrap;
}

.chat-input-area {
  padding: 20px;
  border-top: 1px solid #e4e7ed;
  background: white;
}

.input-tools {
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

.send-button {
  height: 74px;
}
</style>