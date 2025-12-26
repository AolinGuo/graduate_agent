<template>
  <div class="company-detail-container" v-loading="loading">
    <div v-if="!companyName" class="empty-state">
      <el-icon :size="40" color="#c0c4cc"><OfficeBuilding /></el-icon>
      <p>请点击左侧图表或排名列表<br>查看企业详情</p>
    </div>
    
    <div v-else class="detail-content">
      <div class="company-header-simple" v-if="companyName">
        <span class="company-name-text">{{ companyName }}</span>
        <el-tag size="small" type="info" class="count-tag">{{ complaints.length }}</el-tag>
      </div>
      
      <div class="list-container" v-if="complaints.length > 0">
        <el-collapse v-model="activeNames" accordion>
          <el-collapse-item 
            v-for="(item, index) in complaints" 
            :key="index" 
            :name="index"
          >
            <template #title>
              <div class="item-header">
                <span class="time">{{ formatTime(item.time) }}</span>
                <span class="issue-tag" v-if="item.issue1">
                  <el-tag size="small" effect="plain">{{ item.issue1 }}</el-tag>
                </span>
              </div>
            </template>
            
            <div class="item-detail">
              <div class="detail-row" v-if="item.issue2">
                <span class="label">涉及问题(2):</span>
                <span class="value">{{ item.issue2 }}</span>
              </div>
              
              <div class="detail-block">
                <p class="label">问题描述:</p>
                <div class="contentBox description">{{ item.desc }}</div>
              </div>
              
              <div class="detail-block">
                <p class="label">回复内容:</p>
                <div class="contentBox reply">{{ item.reply }}</div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <div v-else-if="!loading" class="empty-state">
        <p>暂无详细投诉记录</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { OfficeBuilding } from '@element-plus/icons-vue'
import { getCompanyDetails } from '@/stores/complaint-store'
import { ElMessage } from 'element-plus'

const props = defineProps({
  companyName: {
    type: String,
    default: ''
  },
  startDate: {
    type: String,
    default: null
  },
  endDate: {
    type: String,
    default: null
  }
})

const loading = ref(false)
const complaints = ref([])
const activeNames = ref('')

const formatTime = (timeStr) => {
  if (!timeStr || timeStr === 'NaT' || timeStr === 'None') return '未知时间'
  // Try to parse YYYY-MM-DD
  try {
    const date = new Date(timeStr)
    return date.toLocaleDateString()
  } catch (e) {
    return timeStr
  }
}

const fetchDetails = async () => {
  if (!props.companyName) return
  
  loading.value = true
  try {
    const response = await getCompanyDetails({
      company_name: props.companyName,
      start_date: props.startDate,
      end_date: props.endDate
    })
    
    if (response.data && response.data.error) {
      ElMessage.error(response.data.error)
      complaints.value = []
    } else {
      complaints.value = response.data.data || []
    }
  } catch (error) {
    console.error('获取企业详情失败:', error)
    ElMessage.error('获取详情失败')
    complaints.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.companyName, (newVal) => {
  if (newVal) {
    fetchDetails()
  } else {
    complaints.value = []
  }
})

watch(() => [props.startDate, props.endDate], () => {
  if (props.companyName) {
    fetchDetails()
  }
})

onMounted(() => {
  if (props.companyName) {
    fetchDetails()
  }
})
</script>

<style scoped>
.company-detail-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  border-radius: 4px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  text-align: center;
  padding: 20px;
}

.empty-state p {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.detail-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.company-header-simple {
  padding: 5px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
}
.company-name-text {
  font-weight: bold;
  font-size: 13px;
  color: #333;
}

.company-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.list-container {
  flex: 1;
  overflow-y: auto;
  padding: 0 5px;
}

/* Customizing el-collapse */
:deep(.el-collapse-item__header) {
  height: auto;
  line-height: normal;
  padding: 10px 0;
  min-height: 40px;
}

:deep(.el-collapse-item__content) {
  padding-bottom: 15px;
}

.item-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding-right: 10px;
}

.time {
  font-size: 12px;
  color: #909399;
}

.issue-tag {
  display: flex;
}

.item-detail {
  padding: 5px 10px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 12px;
}

.detail-row {
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
}

.label {
  font-weight: bold;
  color: #606266;
  flex-shrink: 0;
  margin: 0 0 4px 0;
}

.detail-block {
  margin-top: 8px;
}

.contentBox {
  padding: 8px;
  border-radius: 4px;
  line-height: 1.4;
  word-break: break-all;
}

.description {
  background: #fff;
  border: 1px solid #e4e7ed;
  color: #303133;
}

.reply {
  background: #f0f9ff;
  border: 1px solid #d9ecff;
  color: #409eff;
  margin-top: 4px;
}

/* Scrollbar */
.list-container::-webkit-scrollbar {
  width: 6px;
}
.list-container::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}
</style>
