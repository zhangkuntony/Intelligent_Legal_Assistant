<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2 class="logo">智能法律助手</h2>
      </div>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            {{ userInfo?.username || '用户' }}
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 主体内容区域 -->
    <div class="main-container">
      <!-- 左侧菜单栏 -->
      <el-aside class="sidebar" width="240px">
        <el-menu
          :default-active="currentRoute"
          class="sidebar-menu"
          router
          :collapse="false"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#1064b8"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>主页</span>
          </el-menu-item>
          
          <el-sub-menu index="user-management">
            <template #title>
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </template>
            <el-menu-item index="/users">用户列表</el-menu-item>
            <el-menu-item index="/user-roles">角色管理</el-menu-item>
          </el-sub-menu>
          
          <el-sub-menu index="document-management">
            <template #title>
              <el-icon><Document /></el-icon>
              <span>文档管理</span>
            </template>
            <el-menu-item index="/documents">文档列表</el-menu-item>
            <el-menu-item index="/document-categories">分类管理</el-menu-item>
          </el-sub-menu>
          
          <el-sub-menu index="conversation-management">
            <template #title>
              <el-icon><ChatDotRound /></el-icon>
              <span>会话管理</span>
            </template>
            <el-menu-item index="/chat">智能对话</el-menu-item>
            <el-menu-item index="/history">历史记录</el-menu-item>
            <el-menu-item index="/conversation-analytics">会话分析</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <!-- 右侧内容区域 -->
      <el-main class="content">
        <router-view />
        
        <!-- 开始对话浮动按钮（可拖拽） -->
        <div 
          class="floating-chat-button" 
          @mousedown="startDrag"
          @touchstart="startDrag"
          :style="{ left: buttonPosition.x + 'px', top: buttonPosition.y + 'px' }"
        >
          <el-icon size="24"><ChatDotRound /></el-icon>
          <span class="button-text">开始对话</span>
        </div>
      </el-main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userInfo = ref(authStore.user)

const currentRoute = computed(() => route.path)

// 拖拽相关数据
const buttonPosition = reactive({
  x: window.innerWidth - 160,
  y: window.innerHeight - 160
})

const isDragging = ref(false)
const dragOffset = reactive({ x: 0, y: 0 })
const hasDragged = ref(false) // 标记是否进行了拖拽操作

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      
      authStore.logout()
      ElMessage.success('退出成功')
      router.push('/login')
    } catch {
      // 用户取消退出
    }
  } else if (command === 'profile') {
    // 跳转到个人中心页面
    ElMessage.info('个人中心功能开发中')
  }
}

const startNewChat = () => {
  router.push('/chat')
}

// 开始拖拽
const startDrag = (e: MouseEvent | TouchEvent) => {
  e.preventDefault()
  e.stopPropagation()
  
  isDragging.value = true
  hasDragged.value = false
  
  const clientX = e instanceof MouseEvent ? e.clientX : e.touches[0].clientX
  const clientY = e instanceof MouseEvent ? e.clientY : e.touches[0].clientY
  
  // 记录按钮初始位置和鼠标初始位置
  dragOffset.x = clientX - buttonPosition.x
  dragOffset.y = clientY - buttonPosition.y
  
  // 使用更高效的事件监听方式
  document.addEventListener('mousemove', onDrag, { passive: false })
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('mouseup', stopDrag, { passive: true })
  document.addEventListener('touchend', stopDrag, { passive: true })
  
  // 添加拖拽样式
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'grabbing'
}

// 拖拽中 - 使用 requestAnimationFrame 优化性能
let dragAnimationId: number | null = null

const onDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return
  
  e.preventDefault()
  
  // 标记已经开始拖拽
  hasDragged.value = true
  
  // 使用 requestAnimationFrame 确保流畅性
  if (dragAnimationId) {
    cancelAnimationFrame(dragAnimationId)
  }
  
  dragAnimationId = requestAnimationFrame(() => {
    const clientX = e instanceof MouseEvent ? e.clientX : e.touches[0].clientX
    const clientY = e instanceof MouseEvent ? e.clientY : e.touches[0].clientY
    
    // 直接计算按钮位置，确保与鼠标完全同步
    let newX = clientX - dragOffset.x
    let newY = clientY - dragOffset.y
    
    // 边界检查
    const buttonWidth = 140 // 按钮宽度估计值
    const buttonHeight = 56 // 按钮高度估计值
    
    newX = Math.max(10, Math.min(window.innerWidth - buttonWidth - 10, newX))
    newY = Math.max(10, Math.min(window.innerHeight - buttonHeight - 10, newY))
    
    // 直接更新位置，不经过任何延迟
    buttonPosition.x = newX
    buttonPosition.y = newY
  })
}

// 停止拖拽
const stopDrag = (e: MouseEvent | TouchEvent) => {
  // 只有在没有进行拖拽操作的情况下才视为点击
  if (!hasDragged.value) {
    // 使用 setTimeout 确保在拖拽事件完全结束后再触发点击
    setTimeout(() => {
      startNewChat()
    }, 10)
  }
  
  isDragging.value = false
  hasDragged.value = false
  
  // 清理动画帧
  if (dragAnimationId) {
    cancelAnimationFrame(dragAnimationId)
    dragAnimationId = null
  }
  
  // 移除事件监听
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchend', stopDrag)
  
  // 恢复样式
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

onMounted(() => {
  userInfo.value = authStore.user
  
  // 监听窗口大小变化，调整按钮位置
  window.addEventListener('resize', () => {
    const buttonWidth = 140
    const buttonHeight = 56
    
    buttonPosition.x = Math.min(buttonPosition.x, window.innerWidth - buttonWidth - 20)
    buttonPosition.y = Math.min(buttonPosition.y, window.innerHeight - buttonHeight - 20)
  })
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

.header {
  background-color: #304156;
  border-bottom: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  height: 60px;
}

.logo {
  margin: 0;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #bfcbd9;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.user-info .el-icon {
  margin-right: 8px;
  color: #bfcbd9;
}

.user-info .el-icon--right {
  margin-left: 8px;
  margin-right: 0;
}

.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  background-color: #304156;
  overflow-y: auto;
}

.sidebar-menu {
  border: none;
  height: 100%;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 240px;
}

.content {
  padding: 20px;
  background-color: #f5f7fa;
  overflow-y: auto;
}

/* 滚动条样式 */
.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: #304156;
}

.sidebar::-webkit-scrollbar-thumb {
  background: #475669;
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: #5a6b7c;
}

/* 浮动对话按钮 */
.floating-chat-button {
  position: fixed;
  background: linear-gradient(135deg, #1064b8 0%, #67C23A 100%);
  color: white;
  padding: 16px 20px;
  border-radius: 50px;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
  z-index: 1000;
  font-weight: 500;
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

.floating-chat-button:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 25px rgba(64, 158, 255, 0.6);
}

.floating-chat-button:active {
  transform: scale(0.95);
  cursor: grabbing;
}

.button-text {
  font-size: 14px;
  font-weight: 500;
}
</style>