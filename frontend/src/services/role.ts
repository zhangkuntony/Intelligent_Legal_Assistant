import request from '@/services/api'
import type { 
    Role, 
    RoleDetail,
    CreateRoleData, 
    UpdateRoleData
} from '@/types/role'
import type { Permission } from '@/types/permissions'

export const roleService = {
    /**
     * 获取角色列表
     */
    async getRoles(params: {
        skip?: number
        limit?: number
        include_system?: boolean
    } = {}): Promise<{ roles: Role[]; total: number }> {
        return request.get('/api/roles', { params })
    },

    /**
     * 获取角色详情
     */
    async getRole(roleId: string): Promise<RoleDetail> {
        return request.get(`/api/roles/${roleId}`)
    },

    /**
     * 创建角色
     */
    async createRole(data: CreateRoleData): Promise<{ role: Role }> {
        return request.post('/api/roles', data)
    },

    /**
     * 更新角色
     */
    async updateRole(roleId: string, data: UpdateRoleData): Promise<{ role: Role }> {
        return request.put(`/api/roles/${roleId}`, data)
    },

    /**
     * 删除角色
     */
    async deleteRole(roleId: string): Promise<void> {
        return request.delete(`/api/roles/${roleId}`)
    },

    /**
     * 获取角色权限
     */
    async getRolePermissions(roleId: string): Promise<{ permissions: Permission[]; total: number }> {
        return request.get(`/api/roles/${roleId}/permissions`)
    },

    /**
     * 为角色分配权限
     */
    async assignPermissions(roleId: string, permissionIds: string[]): Promise<void> {
        return request.post(`/api/roles/${roleId}/permissions`, { permission_ids: permissionIds })
    }
}