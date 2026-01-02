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
        style="width: 300px;"
        @input="handleSearch"
      />
      <el-select v-model="filterType" placeholder="文档类型" @change="handleFilter">
        <el-option label="全部类型" value="" />
        <el-option label="合同文件" value="contract" />
        <el-option label="法律文书" value="legal" />
        <el-option label="证据材料" value="evidence" />
        <el-option label="其他" value="other" />
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
              {{ row.name }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTagType(row.type)">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100" />
        <el-table-column prop="uploadTime" label="上传时间" width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'processed' ? 'success' : 'warning'">
              {{ row.status === 'processed' ? '已处理' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="previewDocument(row)">预览</el-button>
            <el-button link type="primary" @click="analyzeDocument(row)">分析</el-button>
            <el-button link type="danger" @click="deleteDocument(row)">删除</el-button>
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
      />
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="500px">
      <el-upload
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="fileList"
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
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" @click="handleUpload" :loading="uploading">
            上传
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Picture, VideoCamera, Folder } from '@element-plus/icons-vue'

const loading = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const fileList = ref<any[]>([])

const searchKeyword = ref('')
const filterType = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const documents = ref([
  {
    id: 1,
    name: '劳动合同范本.pdf',
    type: 'contract',
    size: '2.3MB',
    uploadTime: '2024-01-15 14:30',
    status: 'processed'
  },
  {
    id: 2,
    name: '房屋租赁协议.docx',
    type: 'contract',
    size: '1.8MB',
    uploadTime: '2024-01-14 10:15',
    status: 'processed'
  },
  {
    id: 3,
    name: '知识产权保护说明.txt',
    type: 'legal',
    size: '156KB',
    uploadTime: '2024-01-12 16:45',
    status: 'pending'
  },
  {
    id: 4,
    name: '证据材料.zip',
    type: 'evidence',
    size: '5.2MB',
    uploadTime: '2024-01-10 09:20',
    status: 'processed'
  }
])

const filteredDocuments = computed(() => {
  let result = documents.value
  
  if (searchKeyword.value) {
    result = result.filter(doc => 
      doc.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
  
  if (filterType.value) {
    result = result.filter(doc => doc.type === filterType.value)
  }
  
  return result
})

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
    contract: 'primary',
    legal: 'success',
    evidence: 'warning',
    other: 'info'
  }
  return typeMap[type] || 'info'
}

const getTypeText = (type: string) => {
  const textMap: Record<string, string> = {
    contract: '合同文件',
    legal: '法律文书',
    evidence: '证据材料',
    other: '其他'
  }
  return textMap[type] || '其他'
}

const handleSearch = () => {
  currentPage.value = 1
}

const handleFilter = () => {
  currentPage.value = 1
}

const refreshDocuments = async () => {
  loading.value = true
  // 模拟加载
  setTimeout(() => {
    loading.value = false
    ElMessage.success('文档列表已刷新')
  }, 1000)
}

const previewDocument = (doc: any) => {
  ElMessage.info(`预览文档: ${doc.name}`)
}

const analyzeDocument = (doc: any) => {
  ElMessage.info(`开始分析文档: ${doc.name}`)
}

const deleteDocument = async (doc: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除文档"${doc.name}"吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    documents.value = documents.value.filter(d => d.id !== doc.id)
    ElMessage.success('文档删除成功')
  } catch {
    // 用户取消删除
  }
}

const handleFileChange = (file: any, fileList: any[]) => {
  console.log('File changed:', file, fileList)
}

const handleUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  
  uploading.value = true
  
  // 模拟上传过程
  setTimeout(() => {
    uploading.value = false
    showUploadDialog.value = false
    fileList.value = []
    ElMessage.success('文件上传成功')
    refreshDocuments()
  }, 2000)
}

onMounted(() => {
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