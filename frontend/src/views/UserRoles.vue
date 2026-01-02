<template>
  <div class="roles-container">
    <div class="page-header">
      <h2>角色管理</h2>
      <p>管理系统用户角色和权限分配</p>
    </div>
    
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色列表</span>
          <el-button type="primary" @click="handleAddRole">
            <el-icon><Plus /></el-icon>
            新增角色
          </el-button>
        </div>
      </template>
      
      <el-table :data="roleList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="角色名称" min-width="120" />
        <el-table-column prop="code" label="角色代码" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="userCount" label="用户数" width="80" />
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

interface Role {
  id: number
  name: string
  code: string
  description: string
  userCount: number
  createTime: string
}

const loading = ref(false)
const roleList = ref<Role[]>([])

const loadRoles = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 800))
    roleList.value = [
      {
        id: 1,
        name: '超级管理员',
        code: 'admin',
        description: '系统最高权限管理员',
        userCount: 1,
        createTime: '2024-01-01 10:00:00'
      },
      {
        id: 2,
        name: '普通用户',
        code: 'user',
        description: '普通系统用户',
        userCount: 5,
        createTime: '2024-01-02 14:30:00'
      },
      {
        id: 3,
        name: '访客',
        code: 'guest',
        description: '只读权限用户',
        userCount: 3,
        createTime: '2024-01-03 09:15:00'
      }
    ]
  } catch (error) {
    ElMessage.error('加载角色列表失败')
  } finally {
    loading.value = false
  }
}

const handleAddRole = () => {
  ElMessage.info('新增角色功能开发中')
}

const handleEdit = (role: Role) => {
  ElMessage.info(`编辑角色: ${role.name}`)
}

const handleDelete = async (role: Role) => {
  try {
    await ElMessageBox.confirm(`确定要删除角色 "${role.name}" 吗？`, '提示', {
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
  loadRoles()
})
</script>

<style scoped>
.roles-container {
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