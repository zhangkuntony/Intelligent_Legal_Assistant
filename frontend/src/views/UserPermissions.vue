<template>
  <div class="permissions-container">
    <div class="page-header">
      <h2>权限管理</h2>
      <p>管理系统功能权限和访问控制</p>
    </div>
    
    <el-card>
      <template #header>
        <div class="card-header">
          <span>权限列表</span>
          <el-button type="primary" @click="handleAddPermission">
            <el-icon><Plus /></el-icon>
            新增权限
          </el-button>
        </div>
      </template>
      
      <el-table :data="permissionList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="权限名称" min-width="120" />
        <el-table-column prop="code" label="权限代码" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.type === 'menu' ? 'primary' : 'success'">
              {{ scope.row.type === 'menu' ? '菜单' : '功能' }}
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

interface Permission {
  id: number
  name: string
  code: string
  description: string
  type: string
  createTime: string
}

const loading = ref(false)
const permissionList = ref<Permission[]>([])

const loadPermissions = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 800))
    permissionList.value = [
      {
        id: 1,
        name: '用户管理',
        code: 'user:manage',
        description: '管理用户信息和权限',
        type: 'menu',
        createTime: '2024-01-01 10:00:00'
      },
      {
        id: 2,
        name: '文档管理',
        code: 'document:manage',
        description: '管理文档和文件',
        type: 'menu',
        createTime: '2024-01-01 11:00:00'
      },
      {
        id: 3,
        name: '会话管理',
        code: 'conversation:manage',
        description: '管理对话和会话',
        type: 'menu',
        createTime: '2024-01-01 12:00:00'
      }
    ]
  } catch (error) {
    ElMessage.error('加载权限列表失败')
  } finally {
    loading.value = false
  }
}

const handleAddPermission = () => {
  ElMessage.info('新增权限功能开发中')
}

const handleEdit = (permission: Permission) => {
  ElMessage.info(`编辑权限: ${permission.name}`)
}

const handleDelete = async (permission: Permission) => {
  try {
    await ElMessageBox.confirm(`确定要删除权限 "${permission.name}" 吗？`, '提示', {
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
  loadPermissions()
})
</script>

<style scoped>
.permissions-container {
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