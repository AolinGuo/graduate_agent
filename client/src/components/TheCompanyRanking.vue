<template>
  <div class="company-ranking-container">

    
    <div class="ranking-list custom-scrollbar">
      <div 
        v-for="(item, index) in rankingData" 
        :key="item.name"
        class="ranking-item"
        @click="handleCompanyClick(item)"
      >
        <div class="rank-index" :class="getRankingClass(index)">{{ index + 1 }}</div>
        <div class="company-info">
          <div class="company-name" :title="item.name">{{ item.name }}</div>
          <div class="complaint-count">{{ item.value || item.count || 0 }} 件</div>
        </div>
      </div>
      
      <div v-if="rankingData.length === 0" class="empty-state">
        <el-empty description="暂无数据" :image-size="60"></el-empty>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  rankingData: {
    type: Array,
    default: () => []
  },
  startDate: String,
  endDate: String
})

const emit = defineEmits(['select-company'])

const getRankingClass = (index) => {
  if (index === 0) return 'rank-first'
  if (index === 1) return 'rank-second' 
  if (index === 2) return 'rank-third'
  return ''
}

const handleCompanyClick = (item) => {
  emit('select-company', item.name)
}
</script>

<style scoped>
.company-ranking-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.ranking-header {
  padding: 10px 15px;
  font-weight: bold;
  font-size: 14px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sub-text {
  font-size: 12px;
  color: #999;
  font-weight: normal;
}

.ranking-list {
  flex: 1;
  overflow-y: auto;
  padding: 5px 0;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 8px 15px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid #f9f9f9;
}

.ranking-item:hover {
  background-color: #f5f7fa;
}

.rank-index {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background-color: #f0f2f5;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  margin-right: 12px;
  flex-shrink: 0;
}

.rank-first {
  background-color: #f56c6c;
  color: white;
}

.rank-second {
  background-color: #e6a23c;
  color: white;
}

.rank-third {
  background-color: #409eff;
  color: white;
}

.company-info {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.company-name {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 10px;
}

.complaint-count {
  font-size: 13px;
  color: #606266;
  font-weight: bold;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e4e7ed;
  border-radius: 3px;
}

/* 详情表格样式 */
.content-cell, .reply-cell {
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 100px;
  overflow-y: auto;
}
</style>
