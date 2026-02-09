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
        style="width: 300px;"
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
      <el-select v-model="filterType" placeholder="对话类型" @change="handleFilter">
        <el-option label="全部类型" value="" />
        <el-option label="劳动合同" value="labor" />
        <el-option label="房屋租赁" value="rental" />
        <el-option label="知识产权" value="ip" />
        <el-option label="其他" value="other" />
      </el-select>
    </div>

    <div class="history-content">
      <el-table
        :data="filteredConversations"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="title" label="对话标题" min-width="200">
          <template #default="{ row }">
            <div class="conversation-title" @click="viewConversation(row)">
              <el-icon style="margin-right: 8px; color: #1064b8;">
                <ChatDotRound />
              </el-icon>
              {{ row.title }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTagType(row.type)">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="messageCount" label="消息数" width="100" />
        <el-table-column prop="duration" label="时长" width="100" />
        <el-table-column prop="startTime" label="开始时间" width="180" />
        <el-table-column prop="endTime" label="结束时间" width="180" />
        <el-table-column label="满意度" width="120">
          <template #default="{ row }">
            <el-rate
              v-model="row.satisfaction"
              disabled
              show-score
              text-color="#ff9900"
              score-template="{value}"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="continueConversation(row)">继续</el-button>
            <el-button link type="primary" @click="viewDetails(row)">详情</el-button>
            <el-button link type="danger" @click="deleteSingleConversation(row)">删除</el-button>
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
      />
    </div>

    <!-- 对话详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="对话详情" width="800px">
      <div v-if="currentDetail" class="conversation-detail">
        <div class="detail-header">
          <h3>{{ currentDetail.title }}</h3>
          <div class="detail-meta">
            <span>类型: {{ getTypeText(currentDetail.type) }}</span>
            <span>消息数: {{ currentDetail.messageCount }}</span>
            <span>时长: {{ currentDetail.duration }}</span>
          </div>
        </div>
        
        <div class="detail-messages">
          <h4>对话内容</h4>
          <div class="message-list">
            <div
              v-for="msg in sampleMessages"
              :key="msg.id"
              :class="['message', msg.role]"
            >
              <div class="message-sender">{{ msg.sender }}:</div>
              <div class="message-content">{{ msg.content }}</div>
            </div>
          </div>
        </div>
        
        <div class="detail-analysis">
          <h4>分析总结</h4>
          <p>本次对话主要讨论了劳动合同相关的法律问题，涉及劳动合同的签订、履行和解除等方面。</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const loading = ref(false)
const showDetailDialog = ref(false)
const selectedConversations = ref<any[]>([])

const searchKeyword = ref('')
const dateRange = ref<[Date, Date] | []>([])
const filterType = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const currentDetail = ref<any>(null)

const conversations = ref([
  {
    id: 1,
    title: '劳动合同纠纷咨询',
    type: 'labor',
    messageCount: 24,
    duration: '45分钟',
    startTime: '2024-01-15 14:30',
    endTime: '2024-01-15 15:15',
    satisfaction: 4.5
  },
  {
    id: 2,
    title: '房屋租赁合同审查',
    type: 'rental',
    messageCount: 18,
    duration: '30分钟',
    startTime: '2024-01-14 10:15',
    endTime: '2024-01-14 10:45',
    satisfaction: 4.8
  },
  {
    id: 3,
    title: '知识产权保护咨询',
    type: 'ip',
    messageCount: 32,
    duration: '60分钟',
    startTime: '2024-01-12 16:45',
    endTime: '2024-01-12 17:45',
    satisfaction: 4.2
  },
  {
    id: 4,
    title: '交通事故责任认定',
    type: 'other',
    messageCount: 15,
    duration: '25分钟',
    startTime: '2024-01-10 09:20',
    endTime: '2024-01-10 09:45',
    satisfaction: 4.7
  }
])

const sampleMessages = [
  { id: 1, role: 'user', sender: '用户', content: '您好，我有一个关于劳动合同的问题需要咨询。' },
  { id: 2, role: 'assistant', sender: 'AI法律助手', content: '您好！我很乐意为您解答劳动合同相关的问题。请您详细描述一下您遇到的具体问题。' },
  { id: 3, role: 'user', sender: '用户', content: '公司在没有提前通知的情况下突然解除了我的劳动合同，这种情况合法吗？' }
]

const filteredConversations = computed(() => {
  let result = conversations.value
  
  if (searchKeyword.value) {
    result = result.filter(conv => 
      conv.title.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
  
  if (filterType.value) {
    result = result.filter(conv => conv.type === filterType.value)
  }
  
  if (dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    result = result.filter(conv => {
      const convDate = new Date(conv.startTime)
      return convDate >= start && convDate <= end
    })
  }
  
  return result
})

const getTagType = (type: string) => {
  const typeMap: Record<string, string> = {
    labor: 'primary',
    rental: 'success',
    ip: 'warning',
    other: 'info'
  }
  return typeMap[type] || 'info'
}

const getTypeText = (type: string) => {
  const textMap: Record<string, string> = {
    labor: '劳动合同',
    rental: '房屋租赁',
    ip: '知识产权',
    other: '其他'
  }
  return textMap[type] || '其他'
}

const handleSearch = () => {
  currentPage.value = 1
}

const handleDateChange = () => {
  currentPage.value = 1
}

const handleFilter = () => {
  currentPage.value = 1
}

const handleSelectionChange = (selection: any[]) => {
  selectedConversations.value = selection
}

const viewConversation = (conv: any) => {
  router.push(`/chat/${conv.id}`)
}

const continueConversation = (conv: any) => {
  router.push(`/chat/${conv.id}`)
}

const viewDetails = (conv: any) => {
  currentDetail.value = conv
  showDetailDialog.value = true
}

const deleteSingleConversation = async (conv: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除对话记录"${conv.title}"吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    conversations.value = conversations.value.filter(c => c.id !== conv.id)
    ElMessage.success('对话记录删除成功')
  } catch {
    // 用户取消删除
  }
}

const clearHistory = async () => {
  if (selectedConversations.value.length === 0) return
  
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
    
    const selectedIds = new Set(selectedConversations.value.map(c => c.id))
    conversations.value = conversations.value.filter(c => !selectedIds.has(c.id))
    selectedConversations.value = []
    ElMessage.success('选中记录删除成功')
  } catch {
    // 用户取消删除
  }
}

const exportHistory = () => {
  ElMessage.info('导出功能开发中...')
}

onMounted(() => {
  // 模拟加载数据
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 1000)
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
  line-height: 1.5;
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