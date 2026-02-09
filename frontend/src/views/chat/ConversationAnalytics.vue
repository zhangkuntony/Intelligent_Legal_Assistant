<template>
  <div class="analytics-container">
    <div class="page-header">
      <h2>会话分析</h2>
      <p>分析系统对话数据和用户行为</p>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="color: #1064b8;">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalConversations }}</div>
              <div class="stat-label">总对话数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="color: #67C23A;">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.activeUsers }}</div>
              <div class="stat-label">活跃用户</div>
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
              <div class="stat-value">{{ stats.avgDuration }}</div>
              <div class="stat-label">平均时长(分钟)</div>
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

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>对话趋势</span>
          </template>
          <div class="chart-container">
            <div class="chart-placeholder">
              <el-icon><TrendCharts /></el-icon>
              <p>对话趋势图表</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>热门话题</span>
          </template>
          <div class="chart-container">
            <div class="chart-placeholder">
              <el-icon><PieChart /></el-icon>
              <p>热门话题分布</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>最近对话记录</span>
          <el-button type="primary" @click="$router.push('/history')">查看全部</el-button>
        </div>
      </template>
      
      <el-table :data="recentConversations" style="width: 100%" v-loading="loading">
        <el-table-column prop="user" label="用户" width="120" />
        <el-table-column prop="title" label="对话标题" min-width="200" />
        <el-table-column prop="duration" label="时长" width="100" />
        <el-table-column prop="messages" label="消息数" width="80" />
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column prop="satisfaction" label="满意度" width="100">
          <template #default="scope">
            <el-rate
              v-model="scope.row.satisfaction"
              disabled
              show-score
              text-color="#ff9900"
              score-template="{value}"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)

const stats = ref({
  totalConversations: 0,
  activeUsers: 0,
  avgDuration: 0,
  satisfaction: '4.8'
})

const recentConversations = ref([
  {
    user: '张三',
    title: '劳动合同纠纷咨询',
    duration: '15分钟',
    messages: 8,
    time: '2024-01-15 14:30',
    satisfaction: 4.5
  },
  {
    user: '李四',
    title: '房屋租赁合同审查',
    duration: '25分钟',
    messages: 12,
    time: '2024-01-14 10:15',
    satisfaction: 5
  },
  {
    user: '王五',
    title: '知识产权保护咨询',
    duration: '18分钟',
    messages: 10,
    time: '2024-01-12 16:45',
    satisfaction: 4
  }
])

onMounted(() => {
  // 模拟加载数据
  setTimeout(() => {
    stats.value = {
      totalConversations: 156,
      activeUsers: 23,
      avgDuration: 12,
      satisfaction: '4.8'
    }
  }, 1000)
})
</script>

<style scoped>
.analytics-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 20px;
}

.page-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.stats-row {
  margin-bottom: 0;
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

.chart-container {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-placeholder {
  text-align: center;
  color: #909399;
}

.chart-placeholder .el-icon {
  font-size: 64px;
  margin-bottom: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>