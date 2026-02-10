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
    component: () => import('@/views/login/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/login/Register.vue'),
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
        component: () => import('@/views/document/Documents.vue'),
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/chat/History.vue'),
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/user/Users.vue'),
      },
      {
        path: 'user-roles',
        name: 'UserRoles',
        component: () => import('@/views/user/UserRoles.vue'),
      },
      {
        path: 'permissions',
        name: 'Permissions',
        component: () => import('@/views/user/Permissions.vue'),
      },
      {
        path: 'document-categories',
        name: 'DocumentCategories',
        component: () => import('@/views/document/DocumentCategories.vue'),
      },
      {
        path: 'conversation-analytics',
        name: 'ConversationAnalytics',
        component: () => import('@/views/chat/ConversationAnalytics.vue'),
      },
    ],
  },
  {
    path: '/chat/:id?',
    name: 'Chat',
    component: () => import('@/views/chat/Chat.vue'),
    meta: { requiresAuth: true, fullscreen: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
  },
]

export default routes