import type { PermissionCode } from '@/config/menu'

/**
 * 检查用户是否有指定的权限
 * @param userPermissions 用户拥有的权限代码组合
 * @param requiredPermission 需要的权限代码或权限代码组合
 * @return 是否有权限
 */
export function hasPermission(
    userPermissions: string[],
    requiredPermission?: PermissionCode | PermissionCode[]
): boolean {
    // 如果没有指定权限要求，默认有权限
    if (!requiredPermission) {
        return true
    }

    // 如果是数组，检查是否有任一权限
    if (Array.isArray(requiredPermission)) {
        return requiredPermission.some(perm => userPermissions.includes(perm))
    }

    // 单个权限，直接检查
    return userPermissions.includes(requiredPermission)
}

/**
 * 根据权限过滤菜单项
 * @param menuItems 菜单项数组
 * @param userPermissions 用户拥有的权限代码数组
 * @param isSuperUser 是否是超级用户
 * @returns 过滤后的菜单项
 */
export function filterMenuByPermission<T extends { permission?: PermissionCode | PermissionCode[]; children?: T[] }>(
    menuItems: T[],
    userPermissions: string[],
    isSuperUser: boolean
): T[] {
    return menuItems.filter(item => {
        // 超级用户可以看到所有菜单
        if (isSuperUser) {
            return true
        }

        // 检查当前菜单项的权限
        return hasPermission(userPermissions, item.permission)
    })
    .map(item => {
        // 如果有子菜单，递归过滤子菜单
        if (item.children && item.children.length > 0) {
            const filteredChildren = filterMenuByPermission(item.children, userPermissions, isSuperUser)

            // 如果子菜单全部被过滤掉，也过滤掉父菜单
            return {
                ...item,
                children: filteredChildren,
            } as T
        }

        return item
    })
    .filter(item => {
        // 如果有子菜单但子菜单为空，过滤掉父菜单
        if (item.children?.length === 0) {
            return false
        }
        return true
    })
}