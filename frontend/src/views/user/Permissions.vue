<template>
  <div class="permissions-container">
    <div class="page-header">
      <h2>权限管理</h2>
      <p>查看和管理系统权限配置</p>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF;">
              <el-icon><Lock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_permissions }}</div>
              <div class="stat-label">权限总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67C23A;">
              <el-icon><Collection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_modules }}</div>
              <div class="stat-label">模块数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E6A23C;">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_roles }}</div>
              <div class="stat-label">角色数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>权限列表</span>
          <el-tag type="info" v-if="currentModule">当前模块: {{ currentModule }}</el-tag>
        </div>
      </template>
      
      <!-- 模块筛选 Tabs -->
      <el-tabs v-model="currentModule" @tab-change="handleModuleChange" class="module-tabs">
        <el-tab-pane label="全部模块" name="" />
        <el-tab-pane 
          v-for="module in moduleList" 
          :key="module" 
          :label="getModuleLabel(module)" 
          :name="module"
        />
      </el-tabs>

      <!-- 权限表格 -->
      <el-table :data="permissionList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="权限名称" width="150" header-align="center" align="center" />
        <el-table-column prop="code" label="权限代码" width="200" header-align="center" align="center" />
        <el-table-column prop="module" label="所属模块" width="120" header-align="center" align="center">
          <template #default="scope">
            <el-tag :type="getModuleTagType(scope.row.module)" size="small">
              {{ getModuleLabel(scope.row.module) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="250" header-align="center" align="left">
          <template #default="scope">
            <div v-if="editingId === scope.row.id">
              <el-input
                v-model="editForm.description"
                type="textarea"
                :rows="2"
                size="small"
                placeholder="请输入权限描述"
              />
            </div>
            <div v-else>{{ scope.row.description || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="role_count" label="关联角色数" width="100" header-align="center" align="center">
          <template #default="scope">
            <el-tag type="success" size="small">{{ scope.row.role_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联角色" min-width="200" header-align="center" align="left">
          <template #default="scope">
            <el-tag
              v-for="role in scope.row.roles"
              :key="role.id"
              :type="role.is_system ? 'danger' : 'primary'"
              size="small"
              style="margin: 2px;"
            >
              {{ role.name }}
            </el-tag>
            <span v-if="!scope.row.roles || scope.row.roles.length === 0" style="color: #909399;">暂无</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180" header-align="center" align="center">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" header-align="center" align="center">
          <template #default="scope">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleEdit(scope.row)"
              v-if="editingId !== scope.row.id"
            >
              编辑
            </el-button>
            <template v-else>
              <el-button type="success" size="small" @click="handleSave(scope.row)">保存</el-button>
              <el-button size="small" @click="handleCancel">取消</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, Collection, User } from '@element-plus/icons-vue'
import { permissionService } from '@/services/permissions'
import type { PermissionStats, PermissionWithRoles } from '@/types/permissions'
import dayjs from 'dayjs'

// State
const loading = ref(false)
const stats = ref<PermissionStats>({
    total_permissions: 0,
    total_modules: 0,
    total_roles: 0,
    modules: []
})
const moduleList = ref<string[]>([])
const currentModule = ref<string>('')
const permissionList = ref<PermissionWithRoles[]>([])
const editingId = ref<string>('')
const editForm = ref<{ description: string }>({ description: '' })

// Module 标签映射
const moduleLabels: Record<string, string> = {
    'user': '用户管理',
    'document': '文档管理',
    'chat': '对话管理',
    'role': '角色管理',
    'system': '系统管理'
}

const moduleTagTypes: Record<string, any> = {
    'user': 'primary',
    'document': 'success',
    'chat': 'warning',
    'role': 'danger',
    'system': 'info'
}

// Methods
const loadStats = async () => {
    try {
        const data = await permissionService.getPermissionStats()
        stats.value = data
        moduleList.value = data.modules
    } catch (error: any) {
        ElMessage.error(error.message || '加载统计信息失败')
    }
}

const loadPermissions = async () => {
    loading.value = true
    try {
        const response = await permissionService.getPermissions({
            module: currentModule.value || undefined,
            include_roles: true
        })
        permissionList.value = response.permissions
    } catch (error: any) {
        ElMessage.error(error.message || '加载权限列表失败')
    } finally {
        loading.value = false
    }
}

const handleModuleChange = () => {
    loadPermissions()
}

const handleEdit = (permission: PermissionWithRoles) => {
    editingId.value = permission.id
    editForm.value = {
        description: permission.description
    }
}

const handleSave = async (permission: PermissionWithRoles) => {
    try {        
        ElMessage.success('修改功能将取消')
        editingId.value = ''
        await loadPermissions()
    } catch (error: any) {
        ElMessage.error(error.message || '保存失败')
    }
}

const handleCancel = () => {
    editingId.value = ''
    editForm.value = { description: '' }
}

const getModuleLabel = (module: string) => {
    return moduleLabels[module] || module
}

const getModuleTagType = (module: string) => {
    return moduleTagTypes[module] || ''
}

const formatDate = (dateString: string) => {
    return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(async () => {
    await loadStats()
    await loadPermissions()
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

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-content {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  color: white;
  font-size: 28px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.module-tabs {
  margin-bottom: 20px;
}
</style>
