<template>
  <div class="analytics-container">
    <div class="page-header">
      <h2>会话分析</h2>
      <p>分析系统对话数据和用户行为</p>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="color: #1064b8;">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_conversations }}</div>
              <div class="stat-label">总对话数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="color: #67C23A;">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.active_users }}</div>
              <div class="stat-label">活跃用户</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="color: #E6A23C;">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.avg_duration }}</div>
              <div class="stat-label">平均时长(分钟)</div>
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
            <span>对话趋势（最近7天）</span>
          </template>
          <div class="chart-container">
            <div v-if="trendData.length > 0" class="trend-chart">
              <div 
                v-for="item in trendData" 
                :key="item.date" 
                class="trend-item"
              >
                <div class="trend-date">{{ formatDate(item.date) }}</div>
                <div class="trend-bar">
                  <div 
                    class="trend-bar-fill" 
                    :style="{ width: getBarWidth(item.count, maxTrendCount) }"
                  ></div>
                </div>
                <div class="trend-count">{{ item.count }}</div>
              </div>
            </div>
            <div v-else class="chart-placeholder">
              <p>暂无数据</p>
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
            <div v-if="hotTopics.length > 0" class="topics-list">
              <div 
                v-for="(topic, index) in hotTopics" 
                :key="topic.topic" 
                class="topic-item"
              >
                <span class="topic-rank">{{ index + 1 }}</span>
                <span class="topic-name">{{ topic.topic }}</span>
                <span class="topic-count">{{ topic.count }} 次</span>
              </div>
            </div>
            <div v-else class="chart-placeholder">
              <p>暂无数据</p>
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
        <el-table-column prop="user_name" label="用户" width="120" />
        <el-table-column prop="title" label="对话标题" min-width="200" />
        <el-table-column prop="duration" label="时长(分钟)" width="100" align="center" />
        <el-table-column prop="messages" label="消息数" width="80" align="center" />
        <el-table-column prop="time" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.time) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted, computed } from 'vue'
  import { ElMessage } from 'element-plus'
  import { chatService } from '@/services/chat'
  import dayjs from 'dayjs'

  const loading = ref(false)

  const stats = ref({
    total_conversations: 0,
    active_users: 0,
    avg_duration: 0
  })

  const trendData = ref<Array<{ date: string; count: number }>>([])
  const hotTopics = ref<Array<{ topic: string; count: number }>>([])
  const recentConversations = ref<Array<{
    id: string
    user_id: string
    user_name: string
    title: string
    duration: number
    messages: number
    time: string
  }>>([])

  // 最大趋势数量，用于计算柱状图宽度
  const maxTrendCount = computed(() => {
    if (trendData.value.length === 0) return 1
    return Math.max(...trendData.value.map(item => item.count))
  })

  // 格式化日期
  const formatDate = (dateStr: string) => {
    return dayjs(dateStr).format('MM-DD')
  }

  // 格式化日期时间
  const formatDateTime = (dateTimeStr: string) => {
    return dayjs(dateTimeStr).format('YYYY-MM-DD HH:mm:ss')
  }

  // 计算柱状图宽度百分比
  const getBarWidth = (count: number, max: number) => {
    if (max === 0) return '0%'
    return `${(count / max) * 100}%`
  }

  // 加载分析数据
  const loadAnalytics = async () => {
    loading.value = true
    try {
      const response = await chatService.getConversationAnalytics()
      
      stats.value = response.stats
      trendData.value = response.trend
      hotTopics.value = response.hot_topics
      recentConversations.value = response.recent_conversations
    } catch (error: any) {
      ElMessage.error(error.message || '加载分析数据失败')
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    loadAnalytics()
  })
</script>

<style scoped>
  .analytics-container {
    padding: 20px;
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
    overflow-y: auto;
  }

  .chart-placeholder {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
  }

  /* 对话趋势样式 */
  .trend-chart {
    padding: 10px;
  }

  .trend-item {
    display: flex;
    align-items: center;
    margin-bottom: 15px;
  }

  .trend-date {
    width: 60px;
    color: #606266;
    font-size: 14px;
  }

  .trend-bar {
    flex: 1;
    height: 24px;
    background: #f0f2f5;
    border-radius: 4px;
    margin: 0 15px;
    overflow: hidden;
  }

  .trend-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #409EFF 0%, #53A8FF 100%);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .trend-count {
    width: 50px;
    text-align: right;
    color: #303133;
    font-weight: bold;
    font-size: 14px;
  }

  /* 热门话题样式 */
  .topics-list {
    padding: 10px;
  }

  .topic-item {
    display: flex;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f0f2f5;
  }

  .topic-item:last-child {
    border-bottom: none;
  }

  .topic-rank {
    width: 30px;
    height: 30px;
    background: #409EFF;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    margin-right: 15px;
  }

  .topic-name {
    flex: 1;
    color: #303133;
    font-size: 14px;
  }

  .topic-count {
    color: #909399;
    font-size: 13px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
</style>
