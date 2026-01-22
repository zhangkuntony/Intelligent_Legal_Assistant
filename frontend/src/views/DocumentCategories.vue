<template>
  <div class="categories-container">
    <div class="page-header">
      <h2>文档分类管理</h2>
      <p>管理系统文档分类和标签</p>
    </div>
    
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分类列表</span>
        </div>
      </template>
      
      <el-table :data="categoryList" style="width: 100%" v-loading="loading">
        <el-table-column prop="category_name" label="分类名称" />
        <el-table-column prop="category_code" label="分类代码" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="document_count" label="文档数" />
        <el-table-column prop="created_at" label="创建时间">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { API_CONFIG } from '../config/api'
import request from '../services/api'
import { formatDateTime } from '../utils/dateTimeUtils'

interface Category {
  id: string
  category_name: string
  category_code: string
  description: string
  created_at: string
  updated_at: string
}

const loading = ref(false)
const categoryList = ref<Category[]>([])

const loadCategories = async () => {
  loading.value = true
  try {
    const response = await request.get(API_CONFIG.ENDPOINTS.DOCUMENT_CATEGORIES.BASE)
    categoryList.value = response.document_categories || []
  } catch (error) {
    console.error('加载分类列表失败:', error)
    ElMessage.error('加载分类列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.categories-container {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>