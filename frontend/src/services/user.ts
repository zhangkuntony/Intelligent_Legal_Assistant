import request from '@/services/api'
import type { User, UserRole, CreateUser, UpdateUser, AssignRoles } from '@/types/user'

export const userService = {
    /**
     * 获取用户列表
     */
    async getUsers(params: {
        skip?: number
        limit?: number
    } = {}): Promise<{ users: User[]; total: number }> { 
        return request.get('/api/users', { params })
    },

    /** 
     * 获取用户详情
     */
    async getUser(userId: string): Promise<{ user: User }> {
        return request.get(`/api/users/${userId}`)
    },

    /**
     * 创建用户
     */
    async createUser(data: CreateUser): Promise<{ user: User }> {
        return request.post('/api/users', data)
    },

    /**
     * 更新用户
     */
    async updateUser(userId: string, data: UpdateUser): Promise<{ user: User }> {
        return request.put(`/api/users/${userId}`, data)
    },

    /**
     * 更新用户状态
     */
    async updateUserStatus(userId: string, isActive: boolean): Promise<{ user: User }> {
        return request.patch(`/api/users/${userId}/status`, null, {
            params: { is_active: isActive }
        })
    },

    /**
     * 删除用户
     */
    async deleteUser(userId: string): Promise<void> {
        return request.delete(`/api/users/${userId}`)
    },

    /**
     * 获取用户角色
     */
    async getUserRoles(userId: string): Promise<{ roles: UserRole[]; total: number }> {
        return request.get(`/api/users/${userId}/roles`)
    },

    /**
     * 为用户分配角色
     */
    async assignUserRoles(userId: string, data: AssignRoles): Promise<void> {
        return request.post(`/api/users/${userId}/roles`, data)
    },
}