// frontend/src/config/api.ts
// API 配置常量
export const API_CONFIG = {
  // 基础 URL - 优先使用环境变量，否则使用默认值
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
  // API 端点
  ENDPOINTS: {
    DOCUMENT_CATEGORIES: {
      BASE: '/api/document-categories',
      LIST: '/api/document-categories',
    },
    DOCUMENTS: {
      BASE: '/api/documents',
      UPLOAD: '/api/documents/upload',
      DOWNLOAD: (id: string) => `/api/documents/${id}/download/direct`,
      DELETE: (id: string) => `/api/documents/${id}`
    },
    AUTH: {
      LOGIN: '/api/auth/login',
      LOGOUT: '/api/auth/logout',
      REFRESH: '/api/auth/refresh',
      PROFILE: '/api/auth/profile'
    },
    CONVERSATIONS: {
      BASE: '/api/conversations',
      CREATE: '/api/conversations',
      GET: (id: string) => `/api/conversations/${id}`
    }
  },
  
  // 上传配置
  UPLOAD: {
    MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
    ALLOWED_TYPES: ['.pdf', '.doc', '.docx', '.txt'] as string[]
  },
  
  // 请求配置
  REQUEST: {
    TIMEOUT: 30000,
    RETRY_COUNT: 3
  }
} as const
