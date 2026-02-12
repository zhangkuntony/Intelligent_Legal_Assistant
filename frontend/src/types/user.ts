import { Permission } from './permissions'

export interface User {
    id: string
    username: string
    email: string
    full_name: string
    avatar_url: string
    is_active: boolean
    is_superuser: boolean
    roles: UserRole[]
    last_login: string
    created_at: string
    updated_at: string
}

export interface UserRole {
    id: string
    name: string
    code: string
    is_system: boolean
    assigned_at: string
}

export interface CreateUser {
    username: string
    email: string
    password: string
    full_name?: string
}

export interface UpdateUser {
    full_name?: string
}

export interface UserForm {
    username?: string
    email?: string
    password?: string
    full_name?: string
    role_ids?: string[]
}

export interface AssignRoles {
    role_ids: string[]
}

export interface UserWithPermissions {
    id: string
  username: string
  email: string
  full_name: string
  avatar_url: string
  is_active: boolean
  is_superuser: boolean
  roles: {
    id: string
    name: string
    code: string
    is_system: boolean
  }[]
  permissions: Permission[]
  last_login: string
  created_at: string
}