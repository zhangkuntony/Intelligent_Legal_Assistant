import request from '@/services/api'
import type { 
    Permission,
    PermissionStats,
    PermissionWithRoles
} from '@/types/permissions'

export const permissionService = { 
    /**
     * 获取所有权限列表
     */
    async getAllPermissions(): Promise<{ permissions: Permission[]; total: number}> {
        return request.get('/api/permissions/all')
    },

    /**
     * 获取权限统计信息
     */
    async getPermissionStats(): Promise<PermissionStats> {
        return request.get('/api/permissions/stats')
    },

    /**
     * 获取权限列表（可按模块筛选）
     */
    async getPermissions(params: {
        module?: string
        include_roles?: boolean
    } = {}): Promise<{ permissions: PermissionWithRoles[]; total: number }> {
        return request.get('/api/permissions', { params })
    },

    /**
     * 获取权限详情
     */
    async getPermission(permissionId: string): Promise<PermissionWithRoles> {
        return request.get(`/api/permissions/${permissionId}`)
    }
}