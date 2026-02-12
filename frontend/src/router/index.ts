import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router'
import routes from './routes'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to: RouteLocationNormalized) => {
  const authStore = useAuthStore()

  // 检查是否需要认证
  if (to.meta.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      ElMessage.warning('请先登录')
      return { path: '/login', query: { redirect: to.fullPath } }
    }

    // 等待用户信息加载完成
    if (!authStore.user) {
      await authStore.checkAuthStatus()
    }

    // 权限检查（如果路由配置了权限）
    if (to.meta.permission) {
      const requiredPermissions = Array.isArray(to.meta.permission)
        ? to.meta.permission
        : [to.meta.permission]

      const hasPermission = authStore.hasAnyPermission(requiredPermissions)
      const isSuperUser = authStore.user?.is_superuser || false

      if (!hasPermission && !isSuperUser) {
        ElMessage.error('您没有权限访问该页面')
        return { path: '/dashboard' }
      }
    }
  }

  return true
})

export default router