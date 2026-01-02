import { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/Documents.vue'),
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/History.vue'),
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
      },
      {
        path: 'user-roles',
        name: 'UserRoles',
        component: () => import('@/views/UserRoles.vue'),
      },
      {
        path: 'user-permissions',
        name: 'UserPermissions',
        component: () => import('@/views/UserPermissions.vue'),
      },
      {
        path: 'document-upload',
        name: 'DocumentUpload',
        component: () => import('@/views/DocumentUpload.vue'),
      },
      {
        path: 'document-categories',
        name: 'DocumentCategories',
        component: () => import('@/views/DocumentCategories.vue'),
      },
      {
        path: 'conversation-analytics',
        name: 'ConversationAnalytics',
        component: () => import('@/views/ConversationAnalytics.vue'),
      },
    ],
  },
  {
    path: '/chat/:id?',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { requiresAuth: true, fullscreen: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
  },
]

export default routes