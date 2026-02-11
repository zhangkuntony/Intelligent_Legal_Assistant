<template>
  <div class="history-container">
    <div class="history-header">
      <h2>历史记录</h2>
      <div class="header-actions">
        <el-button @click="exportHistory">
          <el-icon><Download /></el-icon>
          导出记录
        </el-button>
        <el-button type="danger" @click="clearHistory" :disabled="selectedConversations.length === 0">
          <el-icon><Delete /></el-icon>
          删除选中
        </el-button>
      </div>
    </div>

    <div class="history-toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索对话记录..."
        prefix-icon="Search"
        @input="handleSearch"
      />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="handleDateChange"
      />
    </div>

    <div class="history-content">
      <el-table
        :data="filteredConversations"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="title" label="对话标题" min-width="200" header-align="center" align="left">
          <template #default="{ row }">
            <div class="conversation-title" @click="viewDetails(row)">
              {{ row.title }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="message_count" label="消息数" width="100" header-align="center" align="center" />
        <el-table-column prop="user_name" label="用户" width="150" header-align="center" align="center" />
        <el-table-column label="时长" width="200" header-align="center" align="center">
          <template #default="{ row }">
            {{ calculateDuration(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="开始时间" width="200" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_message_at" label="结束时间" width="200" header-align="center" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.last_message_at || row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" header-align="center" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewDetails(row)">详情</el-button>
            <el-button type="danger" size="small" @click="deleteSingleConversation(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="history-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 对话详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      :title="currentDetail?.title || '对话详情'"
      width="70%"
      :close-on-click-model="false"
    >
      <div v-if="currentDetail" class="conversation-detail">
        <!-- 对话元数据 -->
        <div class="detail-header">
          <h3>{{ currentDetail.title }}</h3>
          <div class="detail-meta">
            <span>消息数：{{ currentDetail.message_count }}</span>
            <span>创建时间：{{ formatDateTime(currentDetail.created_at) }}</span>
            <span v-if="currentDetail.last_message_at">最后更新：{{ formatDateTime(currentDetail.last_message_at) }}</span>
          </div>
          <div v-if="currentDetail.description" style="margin-top: 10px; color: #909399;">
            {{ currentDetail.description }}
          </div>
        </div>

        <!-- 消息列表-->
        <div class="detail-messages">
          <h4>对话消息</h4>
          <div class="message-list">
            <div 
              v-for="msg in currentConversationMessages"
              :key="msg.id"
              :class="['message', msg.role]"
            >
              <div class="message-sender">{{ msg.sender }}</div>
              <div class="message-content">
                <span v-html="parseMarkdown(msg.content)"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { chatService} from '@/services/chat'
  import type { ConversationDetail, ConversationWithMessages } from '@/types/chat'
  import dayjs from 'dayjs'
  import relativeTime from 'dayjs/plugin/relativeTime'
  import duration from 'dayjs/plugin/duration'
  import { parseMarkdown } from '@/utils/markdown'

  dayjs.extend(relativeTime)
  dayjs.extend(duration)

  const router = useRouter()

  const loading = ref(false)
  const showDetailDialog = ref(false)
  const selectedConversations = ref<string[]>([])

  const searchKeyword = ref('')
  const dateRange = ref<[Date, Date] | []>([])
  const currentPage = ref(1)
  const pageSize = ref(10)
  const total = ref(0)

  const currentDetail = ref<ConversationWithMessages | null>(null)
  const currentConversationMessages = ref<any[]>([])

  const conversations = ref<ConversationDetail[]>([])

  // 过滤后的对话列表
  const filteredConversations = computed(() => {
    let result = conversations.value
    
    // 搜索过滤
    if (searchKeyword.value) {
      result = result.filter(conv => 
        conv.title.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
        conv.description?.toLowerCase().includes(searchKeyword.value.toLowerCase())
      )
    }
    
    // 日期范围过滤
    if (dateRange.value.length === 2) {
      const [start, end] = dateRange.value
      result = result.filter(conv => {
        const convDate = dayjs(conv.created_at)
        return convDate.isAfter(start) && convDate.isBefore(end)
      })
    }
    
    return result
  })

  // 格式化时间
  const formatDateTime = (dateString: string) => {
    return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
  }

  // 计算对话时长
  const calculateDuration = (conv: ConversationDetail) => {
    const startTime = dayjs(conv.created_at)
    const endTime = dayjs(conv.last_message_at || conv.updated_at)
    const diff = endTime.diff(startTime, 'minute')
    
    if (diff < 60) {
      return `${diff}分钟`
    } else if (diff < 1440) {
      return `${Math.floor(diff / 60)}小时`
    } else {
      return `${Math.floor(diff / 1440)}天`
    }
  }

  const handleSearch = () => {
    currentPage.value = 1
    loadConversations()
  }

  const handleDateChange = () => {
    currentPage.value = 1
    loadConversations()
  }

  const handleSelectionChange = (selection: any[]) => {
    selectedConversations.value = selection.map((item: any) => item.id)
  }

  // 加载对话列表
  const loadConversations = async () => {
    loading.value = true
    try {
      const skip = (currentPage.value - 1) * pageSize.value
      // 使用 getAllConversations 获取所有用户的对话
      const { conversations: data, total: totalCount } = await chatService.getAllConversations(
        skip, 
        pageSize.value
      )

      conversations.value = data
      total.value = totalCount
    } catch (error: any) {
      ElMessage.error(error.message || '加载对话列表失败')
    } finally {
      loading.value = false
    }
  }

  const viewDetails = async (conv: ConversationDetail) => {
    try {
      loading.value = true
      const response = await chatService.getConversation(conv.id)
      currentDetail.value = response

      // 格式化消息
      currentConversationMessages.value = response.messages.map(msg => ({
        id: msg.id,
        role: msg.role,
        sender: msg.role === 'user' ? '用户' : 'AI法律助手',
        content: msg.content
      }))

      showDetailDialog.value = true
    } catch (error: any) {
      ElMessage.error(error.message || '加载对话详情失败')
    } finally {
      loading.value = false
    }
  }

  const deleteSingleConversation = async (conv: ConversationDetail) => {
    try {
      await ElMessageBox.confirm(`确定要删除对话记录"${conv.title}"吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      
      await chatService.deleteConversation(conv.id)
      conversations.value = conversations.value.filter(c => c.id !== conv.id)
      ElMessage.success('对话记录删除成功')
      await loadConversations()       // 重新加载列表
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error(error.message || '删除失败')
      }
    }
  }

  const clearHistory = async () => {
    if (selectedConversations.value.length === 0) {
      ElMessage.warning('请先选择要删除的对话')
      return
    }
    
    try {
      await ElMessageBox.confirm(
        `确定要删除选中的 ${selectedConversations.value.length} 条对话记录吗？此操作不可恢复。`,
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      
      // 批量删除
      const result = await chatService.batchDeleteConversations(selectedConversations.value)
      
      if (result.failed.length > 0) {
        ElMessage.warning(`成功删除 ${result.success.length} 条，失败 ${result.failed.length} 条`)
      } else {
        ElMessage.success(`成功删除 ${result.success.length} 条对话记录`)
      }

      selectedConversations.value = []
      await loadConversations()
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error(error.message || '批量删除失败')
      }
    }
  }

  const exportHistory = () => {
    ElMessage.info('导出功能开发中...')
  }

  // 分页处理
  const handleCurrentChange = (newPage: number) => {
    currentPage.value = newPage
    loadConversations()
  }

  const handleSizeChange = (newSize: number) => {
    pageSize.value = newSize
    currentPage.value = 1
    loadConversations()
  }

  onMounted(() => {
    loadConversations()
  })
</script>

<style scoped>
  .history-container {
    padding: 20px;
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .history-header h2 {
    margin: 0;
    color: #303133;
  }

  .history-toolbar {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
    align-items: center;
  }

  .history-content {
    margin-bottom: 20px;
  }

  .conversation-title {
    display: flex;
    align-items: center;
    cursor: pointer;
    color: #1064b8;
  }

  .conversation-title:hover {
    text-decoration: underline;
  }

  .history-pagination {
    display: flex;
    justify-content: flex-end;
  }

  .conversation-detail {
    max-height: 60vh;
    overflow-y: auto;
  }

  .detail-header {
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #e4e7ed;
  }

  .detail-header h3 {
    margin: 0 0 10px 0;
    color: #303133;
  }

  .detail-meta {
    display: flex;
    gap: 20px;
    color: #606266;
    font-size: 14px;
  }

  .detail-messages {
    margin-bottom: 20px;
  }

  .detail-messages h4 {
    margin: 0 0 15px 0;
    color: #303133;
  }

  .message-list {
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    padding: 15px;
    background: #fafafa;
  }

  .message {
    margin-bottom: 10px;
    padding: 8px 12px;
    border-radius: 4px;
    background: white;
  }

  .message.user {
    border-left: 3px solid #1064b8;
  }

  .message.assistant {
    border-left: 3px solid #67C23A;
  }

  .message-sender {
    font-weight: bold;
    margin-bottom: 5px;
    color: #303133;
  }

  .message-content {
    color: #606266;
    padding: 12px 16px;
    border-radius: 8px;
    line-height: 1.6;
    word-wrap: break-word;
  }

  .detail-analysis h4 {
    margin: 0 0 10px 0;
    color: #303133;
  }

  .detail-analysis p {
    color: #606266;
    line-height: 1.6;
    margin: 0;
  }
</style>