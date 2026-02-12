import type { Component } from 'vue'
import {
    Odometer,
    User,
    Document,
    ChatDotRound,
} from '@element-plus/icons-vue'

// 权限代码常量
export const PERMISSIONS = {
    // 仪表盘
    DASHBOARD_VIEW: 'dashboard:view',
    
    // 用户管理
    USER_MANAGE: 'user:view',
    USER_VIEW: 'user:view',
    USER_CREATE: 'user:create',
    USER_EDIT: 'user:edit',
    USER_DELETE: 'user:delete',
    USER_ASSIGN_ROLE: 'user:assign_role',
    
    // 角色管理
    ROLE_MANAGE: 'role:manage',
    ROLE_VIEW: 'role:view',
    ROLE_CREATE: 'role:create',
    ROLE_EDIT: 'role:edit',
    ROLE_DELETE: 'role:delete',
    ROLE_ASSIGN_PERMISSION: 'role:assign_permission',
    
    // 权限管理
    PERMISSION_MANAGE: 'permission:manage',
    PERMISSION_VIEW: 'permission:view',
    
    // 文档管理
    DOCUMENT_MANAGE: 'document:manage',
    DOCUMENT_VIEW: 'document:view',
    DOCUMENT_CREATE: 'document:create',
    DOCUMENT_EDIT: 'document:edit',
    DOCUMENT_DELETE: 'document:delete',
    DOCUMENT_UPLOAD: 'document:upload',
    DOCUMENT_CATEGORY_MANAGE: 'document:view',
    
    // 会话管理
    CHAT_MANAGE: 'chat:manage',
    CHAT_VIEW: 'chat:view',
    CHAT_SEND: 'chat:send',
    CHAT_DELETE: 'chat:delete',
    CHAT_HISTORY: 'chat:history',
    CHAT_ANALYTICS: 'chat:view',
} as const

export type PermissionCode = typeof PERMISSIONS[keyof typeof PERMISSIONS]

// 菜单项类型定义
export interface MenuItem {
    id: string
    title: string
    icon?: Component
    path?: string
    permission?: PermissionCode | PermissionCode[]
    children?: MenuItem[]
}

// 菜单配置
export const menuConfig: MenuItem[] = [
    {
        id: 'dashboard',
        title: '主页',
        icon: Odometer,
        path: '/dashboard',
    },
    {
        id: 'user-management',
        title: '用户管理',
        icon: User,
        children: [
            {
                id: 'users',
                title: '用户列表',
                path: '/users',
                permission: PERMISSIONS.USER_VIEW
            },
            {
                id: 'user-roles',
                title: '角色管理',
                path: '/user-roles',
                permission: PERMISSIONS.ROLE_VIEW,
            },
            {
                id: 'permissions',
                title: '权限管理',
                path: '/permissions',
                permission: PERMISSIONS.PERMISSION_VIEW,
            },
        ],
    },
    {
        id: 'document-management',
        title: '文档管理',
        icon: Document,
        children: [
            {
                id: 'documents',
                title: '文档列表',
                path: '/documents',
                permission: PERMISSIONS.DOCUMENT_VIEW,
            },
            {
                id: 'document-categories',
                title: '分类管理',
                path: '/document-categories',
                permission: PERMISSIONS.DOCUMENT_CATEGORY_MANAGE,
            },
        ],
    },
    {
    id: 'conversation-management',
    title: '会话管理',
    icon: ChatDotRound,
    children: [
      {
        id: 'chat',
        title: '智能对话',
        path: '/chat',
        permission: [PERMISSIONS.CHAT_SEND, PERMISSIONS.CHAT_VIEW],
      },
      {
        id: 'history',
        title: '历史记录',
        path: '/history',
        permission: PERMISSIONS.CHAT_VIEW,
      },
      {
        id: 'conversation-analytics',
        title: '会话分析',
        path: '/conversation-analytics',
        permission: PERMISSIONS.CHAT_ANALYTICS,
      },
    ],
  },
]