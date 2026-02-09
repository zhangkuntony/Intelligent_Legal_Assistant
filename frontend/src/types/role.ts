export interface Role {
    id: string
    name: string
    code: string
    description: string
    is_system: boolean
    user_count: number
    created_at: string
    updated_at: string
}

export interface Permission {
    id: string
    name: string
    code: string
    module: string
    description: string
    created_at: string
}

export interface RoleDetail extends Role {
    permissions: Permission[]
}

export interface CreateRoleData {
    name: string
    code: string
    description: string
}

export interface UpdateRoleData {
    name?: string
    description?: string
}