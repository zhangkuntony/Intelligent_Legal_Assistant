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
          <el-button type="primary" @click="handleAddCategory">
            <el-icon><Plus /></el-icon>
            新增分类
          </el-button>
        </div>
      </template>
      
      <el-table :data="categoryList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="分类名称" min-width="120" />
        <el-table-column prop="code" label="分类代码" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="documentCount" label="文档数" width="80" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'active' ? 'success' : 'danger'">
              {{ scope.row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Category {
  id: number
  name: string
  code: string
  description: string
  documentCount: number
  status: string
  createTime: string
}

const loading = ref(false)
const categoryList = ref<Category[]>([])

const loadCategories = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 800))
    categoryList.value = [
      {
        id: 1,
        name: '合同文件',
        code: 'contract',
        description: '各类合同和协议文档',
        documentCount: 15,
        status: 'active',
        createTime: '2024-01-01 10:00:00'
      },
      {
        id: 2,
        name: '法律文书',
        code: 'legal',
        description: '法律文书和诉讼材料',
        documentCount: 8,
        status: 'active',
        createTime: '2024-01-02 14:30:00'
      },
      {
        id: 3,
        name: '案例资料',
        code: 'case',
        description: '法律案例和判例',
        documentCount: 12,
        status: 'active',
        createTime: '2024-01-03 09:15:00'
      }
    ]
  } catch (error) {
    ElMessage.error('加载分类列表失败')
  } finally {
    loading.value = false
  }
}

const handleAddCategory = () => {
  ElMessage.info('新增分类功能开发中')
}

const handleEdit = (category: Category) => {
  ElMessage.info(`编辑分类: ${category.name}`)
}

const handleDelete = async (category: Category) => {
  try {
    await ElMessageBox.confirm(`确定要删除分类 "${category.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    ElMessage.success('删除成功')
  } catch {
    // 用户取消删除
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