<template>
  <div class="documents-container">
    <div class="documents-header">
      <h2>文档管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传文档
        </el-button>
        <el-button @click="refreshDocuments">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="documents-toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索文档..."
        prefix-icon="Search"        
        @input="handleSearch"
      />
      <el-select v-model="filterStatus" placeholder="文档状态" style="width: 400px;" @change="handleFilter">
        <el-option label="全部状态" value="" />
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="processing" />
        <el-option label="已处理" value="processed" />
        <el-option label="处理失败" value="error" />
      </el-select>      

      <el-select v-model="filterType" placeholder="文档类型" style="width: 400px;" @change="handleFilter">
        <el-option label="全部分类" value="" />
        <el-option 
          v-for="category in categories" 
          :key="category.id"
          :label="category.category_name" 
          :value="category.category_code" 
        />
      </el-select>
    </div>

    <div class="documents-content">
      <el-table :data="filteredDocuments" style="width: 100%" v-loading="loading">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="文档名称" min-width="200">
          <template #default="{ row }">
            <div class="document-name">
              <el-icon :color="getFileColor(row.type)" style="margin-right: 8px;">
                <component :is="getFileIcon(row.type)" />
              </el-icon>
              {{ row.filename }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTagType(row.file_category)">
              {{ row.file_category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
            <div v-if="row.status === 'processing'" class="progress-info">
              <el-progress 
                :percentage="calculateProgress(row)" 
                :show-text="false" 
                size="small"
                style="width: 60px; margin-left: 8px;"
              />
              <span class="progress-text">{{ row.processed_chunks }}/{{ row.total_chunks }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button link type="primary" @click="previewDocument(row)" :disabled="row.status !== 'processed'">
              预览
            </el-button>
            <el-button link type="primary" @click="downloadDocument(row)">
              下载
            </el-button>
            <el-button link type="primary" @click="analyzeDocument(row)" :disabled="row.status !== 'processed'">
              分析
            </el-button>
            <el-button link type="danger" @click="deleteDocument(row)">
              删除
            </el-button>
          </template>
        </el-table-column>       
      </el-table>
    </div>

    <div class="documents-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="500px">
      <el-upload
        ref="uploadRef"
        drag
        :action="uploadAction"
        :headers="uploadHeaders"
        :data="uploadData"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        :file-list="uploadFileList"
        :auto-upload="false"
        multiple
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .pdf, .doc, .docx, .txt 格式文件，单个文件不超过10MB
          </div>
        </template>
      </el-upload>

      <div class="upload-info">
        <el-form :model="form" label-width="80px" style="margin-top: 20px;">
          <el-form-item label="文档分类">
            <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
              <el-option 
                v-for="category in categories" 
                :key="category.id"
                :label="category.category_name" 
                :value="category.category_name" 
              />
            </el-select>
          </el-form-item>
          <el-form-item label="文档描述">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入文档描述"
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" @click="submitUpload" :loading="uploading">
            上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, UploadUserFile } from 'element-plus'
import { Document, Folder } from '@element-plus/icons-vue'
import { API_CONFIG } from '../config/api'
import { useAuthStore } from '../stores/auth'
import { request } from '../services/api'
import { formatDateTime } from '../utils/dateTimeUtils'

// 响应式数据
const loading = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadFileList = ref<UploadUserFile[]>([])
const uploadRef = ref()

const searchKeyword = ref('')
const filterType = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const categories = ref<any[]>([])

const documents = ref<any[]>([])

interface UploadForm {
  category: string
  description: string
}

const form = reactive<UploadForm>({
  category: '',
  description: ''
})

// 计算属性
const filteredDocuments = computed(() => {
  let result = documents.value
  
  // 搜索过滤
  if (searchKeyword.value) {
    result = result.filter(doc => 
      doc.filename.toLowerCase().includes(searchKeyword.value.toLowerCase()) || 
      doc.title?.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }

  if (filterStatus.value) {
    result = result.filter(doc => doc.status === filterStatus.value)
  }
  
  if (filterType.value) {
    result = result.filter(doc => doc.file_category === filterType.value)
  }
  
  return result
})

// API配置
const authStore = useAuthStore()
const uploadAction = computed(() => API_CONFIG.ENDPOINTS.DOCUMENTS.UPLOAD)
const uploadHeaders = computed(() => ({
  'Authorization': `Bearer ${authStore.token}`
}))
const uploadData = computed(() => ({
  title: '',        // 可以根据需要添加其他字段
}))

const getFileIcon = (type: string) => {
  const iconMap: Record<string, any> = {
    contract: Document,
    legal: Document,
    evidence: Folder,
    other: Folder
  }
  return iconMap[type] || Document
}

const getFileColor = (type: string) => {
  const colorMap: Record<string, string> = {
    contract: '#409EFF',
    legal: '#67C23A',
    evidence: '#E6A23C',
    other: '#909399'
  }
  return colorMap[type] || '#909399'
}

const getTagType = (type: string) => {
  const typeMap: Record<string, string> = {
    '合同文件': 'primary',
    '案例资料': 'success',
    '法律文书': 'warning',
    '法规法条': 'error'
  }
  return typeMap[type] || 'info'
}

const getStatusTagType = (status: string) => {
  const typeMap: Record<string, string> = {
    'pending': 'info',
    'processing': 'warning',
    'processed': 'success',
    'error': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    'pending': '待处理',
    'processing': '处理中',
    'processed': '已处理',
    'error': '处理失败'
  }
  return textMap[status] || '未知'
}

const formatFileSize = (bytes: number) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const calculateProgress = (document: any) => {
  if (!document.total_chunks || document.total_chunks === 0) return 0
  return Math.round((document.processed_chunks / document.total_chunks) * 100)
}

const handleSearch = () => {
  currentPage.value = 1
}

const handleFilter = () => {
  currentPage.value = 1
}

// 添加缺失的分页事件处理函数
const handleSizeChange = (newSize: number) => {
  pageSize.value = newSize
  currentPage.value = 1
  refreshDocuments()
}

const handleCurrentChange = (newPage: number) => {
  currentPage.value = newPage
  refreshDocuments()
}

const refreshDocuments = async () => {
  console.log('当前token:', localStorage.getItem('access_token'))
  console.log('调用接口:', `${API_CONFIG.ENDPOINTS.DOCUMENTS.BASE}?skip=0&limit=10`)

  // 在调用接口前检查token
  const token = localStorage.getItem('access_token')
  console.log('token:', token)
  if (!token) {
    // 跳转到登录页面
    console.log('未找到token，跳转到登录页面')
    globalThis.location.href = '/login'
    return
  }

  try {
    loading.value = true
    const skip = (currentPage.value - 1) * pageSize.value
    const response = await request.get(`${API_CONFIG.ENDPOINTS.DOCUMENTS.BASE}?skip=${skip}&limit=${pageSize.value}`)
    
    documents.value = response.documents || []
    total.value = response.total || 0
    
    ElMessage.success(`已加载 ${documents.value.length} 个文档`)
  } catch (error: any) {
    console.error('获取文档列表失败:', error)
    ElMessage.error('获取文档列表失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}

const previewDocument = (doc: any) => {
  if (doc.status !== 'processed') {
    ElMessage.warning('文档尚未处理完成，无法预览')
    return
  }
  ElMessage.info(`预览文档: ${doc.filename}`)
  // TODO: 实现文档预览功能
}

const downloadDocument = async (doc: any) => {
  try {
    ElMessage.info('开始下载文档...')
    
    // 使用直接下载方式
    const response = await request.get(API_CONFIG.ENDPOINTS.DOCUMENTS.DOWNLOAD(doc.id), {
      responseType: 'blob'
    })
    
    // 创建下载链接
    const url = globalThis.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', doc.filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    globalThis.URL.revokeObjectURL(url)
    
    ElMessage.success('文档下载成功')
  } catch (error: any) {
    console.error('下载文档失败:', error)
    ElMessage.error('下载文档失败: ' + (error.response?.data?.message || error.message))
  }
}

const analyzeDocument = (doc: any) => {
  if (doc.status !== 'processed') {
    ElMessage.warning('文档尚未处理完成，无法分析')
    return
  }
  ElMessage.info(`开始分析文档: ${doc.filename}`)
  // TODO: 实现文档分析功能
}

const deleteDocument = async (doc: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除文档"${doc.filename}"吗？此操作不可恢复。`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await request.delete(API_CONFIG.ENDPOINTS.DOCUMENTS.DELETE(doc.id))
    ElMessage.success('文档删除成功')
    await refreshDocuments()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除文档失败:', error)
      ElMessage.error('删除文档失败: ' + (error.response?.data?.message || error.message))
    }
  }
}

const beforeUpload = (file: any) => {
  // 文件类型检查
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
  
  if (!API_CONFIG.UPLOAD.ALLOWED_TYPES.includes(fileExtension)) {
    ElMessage.error('不支持的文件类型，请上传PDF、Word或文本文件')
    return false
  }
  
  // 文件大小检查（10MB）
  const isLt10M = file.size < API_CONFIG.UPLOAD.MAX_FILE_SIZE
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过10MB')
    return false
  }
  
  return true
}

const handleReset = () => {
  form.category = ''
  form.description = ''
  uploadFileList.value = []
}

const submitUpload = () => {
  if (!uploadRef.value) 
    return;

  uploading.value = true
  uploadRef.value.submit()
}

const handleUploadSuccess = (response: any, file: any) => {
  uploading.value = false
  if (response.error) {
    ElMessage.error('文件上传失败: ' + response.message)
  } else {
    ElMessage.success('文件上传成功')
    showUploadDialog.value = false
    uploadFileList.value = []
    refreshDocuments()
  }
}

const handleUploadError = (error: any, file: any) => {
  uploading.value = false
  ElMessage.error('文件上传失败: ' + (error.message || '网络错误'))
}

const loadCategories = async () => {
  try {
    const response = await request.get(API_CONFIG.ENDPOINTS.DOCUMENT_CATEGORIES.BASE)
    categories.value = response.document_categories || []
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

onMounted(() => {
  loadCategories()
  refreshDocuments()
})
</script>

<style scoped>
.documents-container {
  padding: 20px;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.documents-header h2 {
  margin: 0;
  color: #303133;
}

.documents-toolbar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.documents-content {
  margin-bottom: 20px;
}

.document-name {
  display: flex;
  align-items: center;
}

.documents-pagination {
  display: flex;
  justify-content: flex-end;
}
</style>