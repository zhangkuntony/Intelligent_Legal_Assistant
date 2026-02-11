// 用户相关类型定义
import { Permission } from './permissions'
import { UserRole } from './user'

export interface User {
  id: string
  username: string
  email: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
  is_superuser: boolean
  last_login?: string
  created_at: string
  updated_at: string
  roles: UserRole[]
  permissions: Permission[]
}

export interface LoginData {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
  full_name?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ApiResponse<T = any> {
  data?: T
  message?: string
  error?: boolean
}