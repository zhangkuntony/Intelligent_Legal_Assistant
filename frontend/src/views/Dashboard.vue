<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h1>智能法律助手仪表板</h1>
      <p>欢迎使用智能法律助手，开始您的法律咨询之旅</p>
    </div>
    
    <div class="dashboard-stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="color: #409EFF;">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.conversations }}</div>
                <div class="stat-label">对话记录</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="color: #67C23A;">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.documents }}</div>
                <div class="stat-label">文档数量</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="color: #E6A23C;">
                <el-icon><Clock /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.totalTime }}</div>
                <div class="stat-label">使用时长(小时)</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="color: #F56C6C;">
                <el-icon><Star /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.satisfaction }}</div>
                <div class="stat-label">满意度评分</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="dashboard-actions">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card class="action-card" @click="$router.push('/chat')">
            <div class="action-content">
              <el-icon size="48" color="#409EFF"><ChatDotRound /></el-icon>
              <h3>开始对话</h3>
              <p>与AI法律助手进行智能对话</p>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="action-card" @click="$router.push('/documents')">
            <div class="action-content">
              <el-icon size="48" color="#67C23A"><Document /></el-icon>
              <h3>文档管理</h3>
              <p>管理您的法律文档和文件</p>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="action-card" @click="$router.push('/history')">
            <div class="action-content">
              <el-icon size="48" color="#E6A23C"><Clock /></el-icon>
              <h3>历史记录</h3>
              <p>查看对话历史和使用记录</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="dashboard-recent">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>最近对话</span>
            <el-button type="primary" text @click="$router.push('/history')">查看全部</el-button>
          </div>
        </template>
        <el-table :data="recentConversations" style="width: 100%">
          <el-table-column prop="title" label="对话标题" min-width="200" />
          <el-table-column prop="time" label="时间" width="180" />
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button link type="primary" @click="continueConversation(scope.row)">
                继续对话
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const stats = ref({
  conversations: 0,
  documents: 0,
  totalTime: 0,
  satisfaction: '4.8'
})

const recentConversations = ref([
  { id: 1, title: '劳动合同纠纷咨询', time: '2024-01-15 14:30' },
  { id: 2, title: '房屋租赁合同审查', time: '2024-01-14 10:15' },
  { id: 3, title: '知识产权保护咨询', time: '2024-01-12 16:45' }
])

const continueConversation = (conversation: any) => {
  router.push(`/chat/${conversation.id}`)
}

onMounted(() => {
  // 模拟加载数据
  setTimeout(() => {
    stats.value = {
      conversations: 12,
      documents: 8,
      totalTime: 24,
      satisfaction: '4.8'
    }
  }, 1000)
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.dashboard-header {
  margin-bottom: 30px;
}

.dashboard-header h1 {
  margin: 0;
  color: #303133;
}

.dashboard-header p {
  margin: 10px 0 0 0;
  color: #606266;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  font-size: 48px;
  margin-right: 20px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  color: #909399;
  margin-top: 5px;
}

.action-card {
  cursor: pointer;
  transition: all 0.3s;
  height: 200px;
}

.action-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
}

.action-content {
  text-align: center;
  padding: 20px 0;
}

.action-content h3 {
  margin: 15px 0 10px 0;
  color: #303133;
}

.action-content p {
  color: #909399;
  margin: 0;
}

.dashboard-actions {
  margin: 30px 0;
}

.dashboard-recent {
  margin-top: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>