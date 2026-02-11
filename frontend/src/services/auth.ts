import { request } from './api'
import type { User, LoginData, RegisterData, AuthResponse } from '@/types/auth'
import { Permission } from '@/types/permissions'

export const authService = {
  // 用户登录
  async login(loginData: LoginData): Promise<AuthResponse> {
    return request.formPost<AuthResponse>('/api/auth/token', loginData)
  },

  // 用户注册
  async register(registerData: RegisterData): Promise<{ message: string }> {
    return request.post('/api/auth/register', registerData)
  },

  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    return request.get<User>('/api/auth/me')
  },

  // 用户退出
  async logout(): Promise<{ message: string }> {
    return request.post('/api/auth/logout')
  },

  // 刷新token（如果需要）
  async refreshToken(): Promise<AuthResponse> {
    return request.post<AuthResponse>('/api/auth/refresh')
  },  

  /**
   * 获取当前用户的权限列表
   */
  async getCurrentUserPermissions(): Promise<{ permissions: Permission[] }> {
      return request.get('/api/auth/me/permissions')
  }
}