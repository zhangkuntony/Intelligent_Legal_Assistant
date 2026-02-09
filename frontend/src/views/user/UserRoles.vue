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
        <el-table-column label="系统角色" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_system ? 'danger' : 'success'" size="small">
              {{ scope.row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleViewPermissions(scope.row)">权限</el-button>
            <el-button type="success" size="small" @click="handleEdit(scope.row)" :disabled="scope.row.is_system">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(scope.row)" :disabled="scope.row.is_system">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑角色对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑角色' : '新增角色'"
      width="500px"
      @close="handleDialogClose"
    >
      <el-form :model="roleForm" :rules="rules" ref="formRef" label-width="100px"> 
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="roleForm.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="角色代码" prop="code"> 
          <el-input v-model="roleForm.code" placeholder="请输入角色代码" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述" prop="description"> 
          <el-input v-model="roleForm.description" type="textarea" :rows="3" placeholder="请输入角色描述" /> 
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 权限配置对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      title="权限配置"
      width="800px"
      @close="handlePermissionDialogClose"
    >
      <div v-loading="loadingPermissions"> 
        <el-table
          :data="permissionList"
          @selection-change="handlePermissionSelection"
          style="width: 100%"
          max-height="400px"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="权限名称" width="150" />
          <el-table-column prop="code" label="权限代码" width="200" />
          <el-table-column prop="module" label="所属模块" width="100">
            <template #default="scope">
              <el-tag size="small">{{ scope.row.module }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="permissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePermissions" :loading="savingPermissions">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { roleService } from '@/services/role'
import type { Role, Permission, CreateRoleData } from '@/types/role'
import dayjs from 'dayjs'

// State
const loading = ref(false)
const roleList = ref<Role[]>([])
const dialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const savingPermissions = ref(false)
const formRef = ref<FormInstance>()
const loadingPermissions = ref(false)
const permissionList = ref<Permission[]>([])
const selectedPermissions = ref<Permission[]>([])
const currentRole = ref<Role | null>(null)
const selectedPermissionIds = ref<string[]>([])

// Form
const roleForm = ref<CreateRoleData>({
  name: '',
  code: '',
  description: ''
})

// Rules
const rules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入角色代码', trigger: 'blur' },
    { pattern: /^[a-z_]+$/, message: '只能包含小写字母和下划线', trigger: 'blur' }
  ]
}

// Methods
const loadRoles = async () => {
  loading.value = true
  try {
    const response = await roleService.getRoles()
    roleList.value = response.roles
  } catch (error: any) {
    ElMessage.error(error.message || '加载角色列表失败')
  } finally {
    loading.value = false
  }
}

const loadAllPermissions = async () => {
  loadingPermissions.value = true
  try {
    const response = await roleService.getAllPermissions()
    permissionList.value = response.permissions
  } catch (error: any) {
    ElMessage.error(error.message || '加载权限列表失败')
  } finally {
    loadingPermissions.value = false
  }
}

const loadRolePermissions = async (role: Role) => {
  try {
    const response = await roleService.getRolePermissions(role.id)
    selectedPermissionIds.value = response.permissions.map(p => p.id)
  } catch (error: any) {
    ElMessage.error(error.message || '加载角色权限失败')
  }
}

const handleAddRole = () => {
  isEdit.value = false
  roleForm.value = {
    name: '',
    code: '',
    description: ''
  }
  dialogVisible.value = true
}

const handleEdit = (role: Role) => {
  isEdit.value = true
  roleForm.value = {
    name: role.name,
    code: role.code,
    description: role.description
  }
  currentRole.value = role
  dialogVisible.value = true
}

const handleDelete = async (role: Role) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色 "${role.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning', 
      }
    )

    await roleService.deleteRole(role.id)
    ElMessage.success('删除成功')
    await loadRoles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleViewPermissions = async (role: Role) => {  
  currentRole.value = role
  permissionDialogVisible.value = true
  await loadAllPermissions()
  await loadRolePermissions(role)
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
  dialogVisible.value = false
}

const handlePermissionDialogClose = () => {
  permissionDialogVisible.value = false
  selectedPermissions.value = []
  selectedPermissionIds.value = []
  currentRole.value = null
}

const handlePermissionSelection = (selection: Permission[]) => {
  selectedPermissions.value = selection
  selectedPermissionIds.value = selection.map(p => p.id)
}

const handleSubmit = async () => { 
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => { 
    if (!valid) return

    submitting.value = true
    try {
      if (isEdit.value) {
        await roleService.updateRole(currentRole.value!.id, {
          name: roleForm.value.name,
          description: roleForm.value.description
        })
        ElMessage.success('更新成功')
      } else {
        await roleService.createRole(roleForm.value)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      await loadRoles()
    } catch (error: any) {
      ElMessage.error(error.message || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleSavePermissions = async () => { 
  if (!currentRole.value) return

  savingPermissions.value = true
  try {
    await roleService.assignPermissions(currentRole.value.id, selectedPermissionIds.value)
    ElMessage.success('权限保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '权限保存失败')
  } finally {    
    permissionDialogVisible.value = false
  }
}

const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
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