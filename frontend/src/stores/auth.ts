import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authService } from '@/services/auth'
import type { User, LoginData, RegisterData } from '@/types/auth'
import { Permission } from '@/types/permissions'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const permissions = ref<Permission[]>([])
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const isAuthenticated = ref<boolean>(!!token.value)

  const login = async (loginData: LoginData) => {
    try {
      const response = await authService.login(loginData)
      
      token.value = response.access_token
      user.value = response.user
      isAuthenticated.value = true
      
      localStorage.setItem('access_token', response.access_token)

      // 加载用户权限
      await loadPermissions()
      
      return response
    } catch (error) {
      logout()
      throw error
    }
  }

  const register = async (registerData: RegisterData) => {
    try {
      const response = await authService.register(registerData)
      return response
    } catch (error) {
      console.error('Error registering user', error)
      throw error
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    isAuthenticated.value = false
    localStorage.removeItem('access_token')
  }

  const checkAuthStatus = async () => {
    if (token.value) {
      try {
        const userInfo = await authService.getCurrentUser()
        user.value = userInfo
        isAuthenticated.value = true

        // 加载用户权限
        await loadPermissions()
      } catch (error) {
        console.error('Error checking auth status', error)
        logout()
      }
    }
  }

  const loadPermissions = async () => {
    try {
        const response = await authService.getCurrentUserPermissions()
        permissions.value = response.permissions
        
        // 如果用户信息中已经有权限，同步到 store
        if (user.value?.permissions) {
          permissions.value = user.value.permissions
        }
      } catch (error) {
        console.error('Error loading permissions', error)
      }
  }

  // 权限检查方法
  const hasPermission = (permissionCode: string): boolean => {
    // 超级管理员拥有所有权限
    if (user.value?.is_superuser) {
      return true
    }
    
    return permissions.value.some(p => p.code === permissionCode)
  }

  const hasAnyPermission = (permissionCodes: string[]): boolean => {
    // 超级管理员拥有所有权限
    if (user.value?.is_superuser) {
      return true
    }
    
    return permissionCodes.some(code => permissions.value.some(p => p.code === code))
  }

  const hasAllPermissions = (permissionCodes: string[]): boolean => {
    // 超级管理员拥有所有权限
    if (user.value?.is_superuser) {
      return true
    }
    
    return permissionCodes.every(code => permissions.value.some(p => p.code === code))
  }

  return {
    user,
    permissions,
    token,
    isAuthenticated,
    login,
    register,
    logout,
    checkAuthStatus,
    loadPermissions,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
  }
})