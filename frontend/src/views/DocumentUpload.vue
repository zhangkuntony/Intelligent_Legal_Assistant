<template>
  <div class="upload-container">
    <div class="page-header">
      <h2>文档上传</h2>
      <p>上传法律文档和文件到系统</p>
    </div>
    
    <el-card>
      <template #header>
        <span>上传文档</span>
      </template>
      
      <el-upload
        class="upload-demo"
        drag
        action="#"
        multiple
        :before-upload="beforeUpload"
        :on-success="handleSuccess"
        :on-error="handleError"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持上传 .pdf, .doc, .docx, .txt 格式的文件，单个文件不超过 10MB
          </div>
        </template>
      </el-upload>
      
      <div class="upload-info">
        <el-form :model="form" label-width="80px" style="margin-top: 20px;">
          <el-form-item label="文档分类">
            <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
              <el-option label="合同文件" value="contract" />
              <el-option label="法律文书" value="legal" />
              <el-option label="案例资料" value="case" />
              <el-option label="其他文档" value="other" />
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
          <el-form-item>
            <el-button type="primary" @click="handleSubmit" :loading="uploading">
              确认上传
            </el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

interface UploadForm {
  category: string
  description: string
}

const fileList = ref([])
const uploading = ref(false)
const form = reactive<UploadForm>({
  category: '',
  description: ''
})

const beforeUpload = (file: File) => {
  const isLt10M = file.size / 1024 / 1024 < 10
  const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
  
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('只能上传 PDF、Word 或文本文件!')
    return false
  }
  
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }
  
  return true
}

const handleSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} 上传成功`)
}

const handleError = (error: any, file: any) => {
  ElMessage.error(`${file.name} 上传失败`)
}

const handleSubmit = async () => {
  if (!form.category) {
    ElMessage.error('请选择文档分类')
    return
  }
  
  if (fileList.value.length === 0) {
    ElMessage.error('请选择要上传的文件')
    return
  }
  
  uploading.value = true
  try {
    // 模拟上传过程
    await new Promise(resolve => setTimeout(resolve, 2000))
    ElMessage.success('文档上传成功')
    handleReset()
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

const handleReset = () => {
  form.category = ''
  form.description = ''
  fileList.value = []
}
</script>

<style scoped>
.upload-container {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 20px;
}

.page-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.upload-demo {
  width: 100%;
}

.upload-info {
  margin-top: 20px;
}
</style>