import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authService } from '@/services/auth'
import type { User, LoginData, RegisterData } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const isAuthenticated = ref<boolean>(!!token.value)

  const login = async (loginData: LoginData) => {
    try {
      const response = await authService.login(loginData)
      
      token.value = response.access_token
      user.value = response.user
      isAuthenticated.value = true
      
      localStorage.setItem('access_token', response.access_token)
      
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
      } catch (error) {
        logout()
      }
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    register,
    logout,
    checkAuthStatus,
  }
})