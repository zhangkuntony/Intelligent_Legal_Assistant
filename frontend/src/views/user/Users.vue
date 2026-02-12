<template>
  <div class="users-container">
    <div class="page-header">
      <h2>用户管理</h2>
      <p>管理平台用户信息和权限</p>
    </div>
    
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户列表</span>
          <el-button 
            type="primary" 
            @click="handleAddUser"
            v-if="hasPermission(USER_CREATE_PERMISSION)"
          >
            <el-icon><Plus /></el-icon>
            新增用户
          </el-button>
        </div>
      </template>
      
      <el-table :data="userList" style="width: 100%" v-loading="loading">
        <el-table-column prop="username" label="用户名" width="150" header-align="center" align="center" />
        <el-table-column prop="email" label="邮箱" min-width="250" header-align="center" align="center" />
        <el-table-column prop="full_name" label="全名" width="200" header-align="center" align="center" />
        <el-table-column prop="role" label="角色" width="200" header-align="center" align="center">
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
        <el-table-column prop="is_active" label="状态" width="120" header-align="center" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'danger'" size="small">
              {{ scope.row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="250" header-align="center" align="center">
          <template #default="scope">
            {{ formatDate(scope.row.createTime) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right" header-align="center" align="center">
          <template #default="scope">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleEdit(scope.row)"
              v-if="hasPermission(USER_EDIT_PERMISSION)"
            >
              编辑
            </el-button>
            <el-button
              :type="scope.row.is_active ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(scope.row)"
              :disabled="scope.row.is_superuser"
              v-if="hasPermission(USER_EDIT_PERMISSION)"
            >
              {{ scope.row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleDelete(scope.row)"
              :disabled="scope.row.is_superuser"
              v-if="hasPermission(USER_DELETE_PERMISSION)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form :model="userForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="userForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="全名" prop="full_name">
          <el-input v-model="userForm.full_name" placeholder="请输入全名" />
        </el-form-item>
        <el-form-item label="角色" prop="role_ids" v-if="hasPermission(USER_ASSIGN_ROLE_PERMISSION)">
          <el-select v-model="userForm.role_ids" multiple placeholder="请选择角色" style="width: 100%;">
            <el-option
              v-for="role in roleList"
              :key="role.id"
              :label="role.name"
              :value="role.id"
              :disabled="role.is_system"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>


  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
  import { Plus } from '@element-plus/icons-vue'
  import { userService } from '@/services/user'
  import { roleService } from '@/services/role'
  import type { User, UserForm } from '@/types/user'
  import type { Role } from '@/types/role'
  import dayjs from 'dayjs'
  import { useAuthStore } from '@/stores/auth'

  // State
  const loading = ref(false)
  const userList = ref<User[]>([])
  const currentPage = ref(1)
  const pageSize = ref(10)
  const total = ref(0)
  const dialogVisible = ref(false)
  const isEdit = ref(false)
  const submitting = ref(false)
  const formRef = ref<FormInstance>()
  const roleList = ref<Role[]>([])
  const authStore = useAuthStore()
  const { hasPermission } = authStore

  // 用户管理权限代码
  const USER_MANAGE_PERMISSION = 'user.manage'
  const USER_CREATE_PERMISSION = 'user.create'
  const USER_EDIT_PERMISSION = 'user.edit'
  const USER_DELETE_PERMISSION = 'user.delete'
  const USER_ASSIGN_ROLE_PERMISSION = 'user.assign_role'

  // Form
  const userForm = ref<UserForm>({
    username: '',
    email: '',
    password: '',
    full_name: ''
  })

  // Rules
  const rules = {
    username: [
      { required: true, message: '请输入用户名', trigger: 'blur' },
      { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' }
    ],
    email: [
      { required: true, message: '请输入邮箱', trigger: 'blur' },
      { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
    ],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 6, max: 100, message: '长度在 6 到 100 个字符', trigger: 'blur' }
    ]
  }

  // Methods
  const loadUsers = async () => {
    loading.value = true
    try {
      const skip = (currentPage.value - 1) * pageSize.value
      const response = await userService.getUsers({ skip, limit: pageSize.value })
      userList.value = response.users
      total.value = response.total
    } catch (error: any) {
      ElMessage.error(error.message ||'加载用户列表失败')
    } finally {
      loading.value = false
    }
  }

  const loadRoles = async () => {
    try {
      const response = await roleService.getRoles()
      roleList.value = response.roles
    } catch (error: any) {
      ElMessage.error(error.message || '加载角色列表失败')
    }
  }

  const handleAddUser = async () => {
    isEdit.value = false
    userForm.value = {
      username: '',
      email: '',
      password: '',
      full_name: ''
    }
    await loadRoles()
    dialogVisible.value = true
  }

  const handleEdit = async (user: User) => {
    isEdit.value = true
    userForm.value = {
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      role_ids: user.roles.map(role => role.id)
    }
    await loadRoles()
    dialogVisible.value = true
  }

  const handleDelete = async (user: User) => {
    try {
      await ElMessageBox.confirm(
        `确定要删除用户 "${user.username}" 吗？`,
        '删除确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )

      await userService.deleteUser(user.id)
      ElMessage.success('删除成功')
      await loadUsers()
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error(error.message || '删除失败')
      }
    }
  }

  const handleToggleStatus = async (user: User) => {
    try {
      await userService.updateUserStatus(user.id, !user.is_active)
      ElMessage.success('状态更新成功')
      await loadUsers()
    } catch (error: any) {
      ElMessage.error(error.message || '状态更新失败')
    }
  }

  const handleDialogClose = () => {
    formRef.value?.resetFields()
    dialogVisible.value = false
  }

  const handleSubmit = async () => { 
    if (!formRef.value)
      return

    await formRef.value.validate(async (valid) => {
      if (!valid)
        return

      submitting.value = true
      try {
        if (isEdit.value) {
          const currentUser = userList.value.find(u => u.username === userForm.value.username)
          if (currentUser) {
            // 更新用户信息
            await userService.updateUser(currentUser.id, {
              full_name: userForm.value.full_name
            })
            // 更新用户角色
            await userService.assignUserRoles(currentUser.id, { role_ids: userForm.value.role_ids || [] })
          }
          ElMessage.success('更新成功')
        } else {
          const { user } = await userService.createUser({
            username: userForm.value.username || '',
            email: userForm.value.email || '',
            password: userForm.value.password || '',
            full_name: userForm.value.full_name
          })

          // 为用户分配角色
          if (userForm.value.role_ids && userForm.value.role_ids.length > 0) {
            await userService.assignUserRoles(user.id, { role_ids: userForm.value.role_ids })
          }
          
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        await loadUsers()
      } catch (error: any) {
        ElMessage.error(error.message || '操作失败')
      } finally {
        submitting.value = false
      }
    })
  };

  const handleSizeChange = (val: number) => {
    pageSize.value = val
    loadUsers()
  }

  const handleCurrentChange = (val: number) => {
    currentPage.value = val
    loadUsers()
  }

  const formatDate = (dateString: string) => {
    return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
  }

  onMounted(async () => {
    // 等待用户信息加载完成
    if (!authStore.user) {
      await authStore.checkAuthStatus()
    }

    // 检查权限
    if (!hasPermission(USER_MANAGE_PERMISSION)) {
      ElMessage.error('您没有权限访问用户管理页面')
      // 跳转到首页或其他有权限的页面
      return
    }
    
    loadUsers()
  })
</script>

<style scoped>
  .users-container {
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

  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
</style>