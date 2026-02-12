export interface Permission {
    id: string
    name: string
    code: string
    module: string
    description: string
    created_at: string
}

export interface PermissionWithRoles extends Permission {
    roles: Array<{
        id: string
        name: string
        code: string
        is_system: boolean
    }>
    role_count?: number
}


export interface PermissionStats {
    total_permissions: number
    total_modules: number
    total_roles: number
    modules: string[]
}