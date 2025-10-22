<template>
  <div class="dashboard-container">
    <!-- 主网格布局 -->
    <div class="dashboard-grid">
      <!-- 左上：控制台 -->
      <div class="grid-item console-panel">
        <el-card class="full-height-card" shadow="hover">
          <template #header>
            <div class="card-header-compact">
              <span>控制台</span>
              <el-button 
                type="primary" 
                size="small" 
                @click="loadDashboardData" 
                :loading="loading"
                circle>
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          <div class="scrollable-content">
            <el-form :model="filters" label-width="70px" size="small">
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="filters.startDate"
                  type="date"
                  placeholder="开始日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                  @change="loadDashboardData"
                />
              </el-form-item>
              
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="filters.endDate"
                  type="date"
                  placeholder="结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                  @change="loadDashboardData"
                />
              </el-form-item>
              
              <el-form-item label="企业选择">
                <el-select
                  v-model="filters.selectedCompanies"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择企业"
                  style="width: 100%"
                  :max-collapse-tags="1"
                  @change="loadDashboardData"
                >
                  <el-option
                    v-for="company in filterOptions.companies"
                    :key="company"
                    :label="company"
                    :value="company"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="行业大类">
                <el-select
                  v-model="filters.selectedIndustryLevel1"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择行业大类"
                  style="width: 100%"
                  :max-collapse-tags="1"
                  @change="loadDashboardData"
                >
                  <el-option
                    v-for="industry in filterOptions.industryLevel1"
                    :key="industry"
                    :label="industry"
                    :value="industry"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="行业中类">
                <el-select
                  v-model="filters.selectedIndustryLevel2"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择行业中类"
                  style="width: 100%"
                  :max-collapse-tags="1"
                  @change="loadDashboardData"
                >
                  <el-option
                    v-for="industry in filterOptions.industryLevel2"
                    :key="industry"
                    :label="industry"
                    :value="industry"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="详细分类">
                <el-select
                  v-model="filters.selectedIndustries"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择详细分类"
                  style="width: 100%"
                  :max-collapse-tags="1"
                  @change="loadDashboardData"
                >
                  <el-option
                    v-for="industry in filterOptions.industries"
                    :key="industry"
                    :label="industry"
                    :value="industry"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="问题分类">
                <el-select
                  v-model="filters.selectedCategories"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择问题分类"
                  style="width: 100%"
                  :max-collapse-tags="1"
                  @change="loadDashboardData"
                >
                  <el-option
                    v-for="category in filterOptions.categories"
                    :key="category"
                    :label="category"
                    :value="category"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item>
                <el-button @click="clearFilters" size="small" style="width: 100%">
                  <el-icon><RefreshLeft /></el-icon>
                  重置筛选
                </el-button>
              </el-form-item>
              
              <div class="filter-tags">
                <el-tag 
                  v-if="filters.selectedCompanies.length > 0" 
                  type="info" 
                  size="small" 
                  closable 
                  @close="filters.selectedCompanies = []; loadDashboardData()">
                  企业: {{ filters.selectedCompanies.length }}
                </el-tag>
                <el-tag 
                  v-if="filters.selectedIndustries.length > 0" 
                  type="success" 
                  size="small" 
                  closable 
                  @close="filters.selectedIndustries = []; loadDashboardData()">
                  行业: {{ filters.selectedIndustries.length }}
                </el-tag>
                <el-tag 
                  v-if="filters.selectedCategories.length > 0" 
                  type="warning" 
                  size="small" 
                  closable 
                  @close="filters.selectedCategories = []; loadDashboardData()">
                  问题: {{ filters.selectedCategories.length }}
                </el-tag>
              </div>
            </el-form>
          </div>
        </el-card>
      </div>

      <!-- 右上：时序分析 -->
      <div class="grid-item timeseries-panel">
        <el-card class="full-height-card" shadow="hover">
          <template #header>
            <div class="card-header-compact">
              <span>时间序列分析</span>
              <el-button 
                type="primary" 
                size="small" 
                @click="performTimeSeriesAnalysis" 
                :loading="analysisLoading">
                执行分析
              </el-button>
            </div>
          </template>
          <div class="scrollable-content">
            <div v-if="!timeSeriesResults && !analysisLoading" class="empty-state">
              <el-icon :size="40" color="#c0c4cc"><TrendCharts /></el-icon>
              <p>点击"执行分析"查看时序分析结果</p>
            </div>
            
            <div v-if="analysisLoading" class="empty-state">
              <el-icon class="is-loading" :size="40" color="#409eff"><Loading /></el-icon>
              <p>分析中...</p>
            </div>
            
            <div v-if="timeSeriesResults && !analysisLoading">
              <!-- ACF分析结果 -->
              <div v-if="timeSeriesResults.analysis.acf && !timeSeriesResults.analysis.acf.error" class="analysis-result-compact">
                <h5>ACF自相关分析</h5>
                <div ref="acfChart" style="width: 100%; height: 180px;"></div>
              </div>
              
              <!-- STL分解结果 -->
              <div v-if="timeSeriesResults.analysis.stl && !timeSeriesResults.analysis.stl.error" class="analysis-result-compact">
                <h5>STL季节性分解</h5>
                <div class="stl-compact">
                  <p class="stl-label">趋势分量</p>
                  <div ref="stlTrendChart" style="width: 100%; height: 140px;"></div>
                </div>
                <div class="stl-compact">
                  <p class="stl-label">季节分量</p>
                  <div ref="stlSeasonalChart" style="width: 100%; height: 140px;"></div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 中下：趋势图 + 统计指标 + 企业排名 -->
      <div class="grid-item combined-panel">
        <el-card class="full-height-card" shadow="hover">
          <template #header>
            <div class="card-header-compact">
              <span>趋势图以及企业投诉排名</span>
              <el-radio-group v-model="trendPeriod" size="small" @change="loadTrendData">
                <el-radio-button label="day">按天</el-radio-button>
                <el-radio-button label="week">按周</el-radio-button>
                <el-radio-button label="month">按月</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          
          <div class="combined-content">
            <!-- 左侧：统计指标 -->
            <div class="stats-sidebar">
              <div class="stat-item-vertical total-stat">
                <el-icon size="16"><Document /></el-icon>
                <div class="stat-content-vertical">
                  <div class="stat-value-vertical">{{ dashboardStats.total_complaints || 0 }}</div>
                  <div class="stat-label-vertical">投诉总量</div>
                </div>
              </div>
              <div class="stat-item-vertical company-stat">
                <el-icon size="16"><OfficeBuilding /></el-icon>
                <div class="stat-content-vertical">
                  <div class="stat-value-vertical">{{ dashboardStats.companies_count || 0 }}</div>
                  <div class="stat-label-vertical">涉及企业数</div>
                </div>
              </div>
              <div class="stat-item-vertical industry-stat">
                <el-icon size="16"><Grid /></el-icon>
                <div class="stat-content-vertical">
                  <div class="stat-value-vertical">{{ dashboardStats.industries_count || 0 }}</div>
                  <div class="stat-label-vertical">涉及行业数</div>
                </div>
              </div>
              <div class="stat-item-vertical repeat-stat">
                <el-icon size="16"><Warning /></el-icon>
                <div class="stat-content-vertical">
                  <div class="stat-value-vertical">{{ dashboardStats.repeat_companies_count || 0 }}</div>
                  <div class="stat-label-vertical">月内重复投诉企业</div>
                </div>
              </div>
            </div>
            
            <!-- 中间：趋势图 -->
            <div class="trend-section">
              <div v-loading="trendLoading" class="trend-chart-wrapper">
                <div ref="trendChart" style="width: 100%; height: 100%;"></div>
              </div>
            </div>
            
            <!-- 右侧：企业排名 -->
            <div class="ranking-section">
              <div class="ranking-header">
                <span>企业投诉量排名</span>
                <el-tag type="info" size="small">全部企业</el-tag>
              </div>
              <div v-loading="loading" class="ranking-list-compact">
                <div 
                  v-for="(item, index) in dashboardStats.company_ranking || []" 
                  :key="index"
                  class="ranking-item-compact"
                  :class="getRankingClass(index)"
                >
                  <div class="rank-number-compact">{{ index + 1 }}</div>
                  <div class="company-info-compact">
                    <div class="company-name-compact" :title="item.name">{{ item.name }}</div>
                    <div class="complaint-count-compact">{{ item.count }} 件</div>
                  </div>
                </div>
                
                <div v-if="(!dashboardStats.company_ranking || dashboardStats.company_ranking.length === 0) && !loading" class="empty-state">
                  <el-empty description="暂无数据" :image-size="60"></el-empty>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右下：AI功能（标签切换） -->
      <div class="grid-item ai-panel">
        <el-card class="full-height-card" shadow="hover">
          <template #header>
            <div class="card-header-compact">
              <span>AI智能助手</span>
            </div>
          </template>
          <el-tabs v-model="activeAITab" class="ai-tabs">
            <!-- AI报告生成 -->
            <el-tab-pane label="报告生成" name="report">
              <div class="ai-tab-content">
                <div class="ai-action-bar">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="handleGenerateAIReport"
                    :loading="aiReportLoading"
                    :disabled="!filters.startDate || !filters.endDate"
                    style="width: 100%">
                    {{ aiReportLoading ? '生成中...' : '生成AI报告' }}
                  </el-button>
                </div>
                
                <div class="ai-output-area">
                  <div v-if="!aiReport && !aiReportLoading" class="empty-state">
                    <el-icon :size="40" color="#c0c4cc"><Document /></el-icon>
                    <p>点击按钮生成AI分析报告</p>
                  </div>
                  
                  <div v-else-if="aiReportLoading" class="empty-state">
                    <el-icon class="is-loading" :size="40" color="#409eff"><Loading /></el-icon>
                    <p>AI正在生成报告...</p>
                  </div>
                  
                  <div v-else class="ai-result-content">
                    <div v-if="aiReportThinking" class="thinking-section-compact">
                      <el-icon><View /></el-icon> <span class="thinking-label">思考过程</span>
                      <div class="thinking-content-compact">{{ aiReportThinking }}</div>
                    </div>
                    <div class="report-text-compact" v-html="formatReportText(aiReport)"></div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
            
            <!-- AI辅助回复 -->
            <el-tab-pane label="辅助回复" name="reply">
              <div class="ai-tab-content">
                <el-input
                  v-model="complaintInput"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入市民投诉内容..."
                  class="complaint-input-compact"
                />
                
                <div class="ai-action-bar">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="handleGenerateAIReply"
                    :loading="aiReplyLoading"
                    :disabled="!complaintInput.trim()">
                    生成回复
                  </el-button>
                  <el-button 
                    size="small" 
                    @click="handleUseExample">
                    使用示例
                  </el-button>
                  <el-button 
                    v-if="aiReply"
                    type="success" 
                    size="small" 
                    @click="handleCopyReply">
                    复制
                  </el-button>
                </div>
                
                <div class="ai-output-area" v-if="aiReply || aiReplyLoading">
                  <div v-if="aiReplyLoading" class="empty-state">
                    <el-icon class="is-loading" :size="40" color="#67c23a"><Loading /></el-icon>
                    <p>AI正在生成回复...</p>
                  </div>
                  
                  <div v-else class="ai-result-content">
                    <div v-if="aiReplyThinking" class="thinking-section-compact">
                      <el-icon><View /></el-icon> <span class="thinking-label">思考过程</span>
                      <div class="thinking-content-compact">{{ aiReplyThinking }}</div>
                    </div>
                    <div class="reply-text-compact">{{ aiReply }}</div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Refresh, Document, OfficeBuilding, Grid, Warning, TrendCharts, RefreshLeft,
  ChatDotSquare, Loading, View
} from '@element-plus/icons-vue'
import { 
  getDashboardStats, 
  getTrendData, 
  analyzeTimeSeries,
  getDataSummary,
  getFilterOptions,
  generateAIReport,
  generateAIReply
} from '@/stores/complaint-store'
import * as d3 from 'd3'

// 响应式数据
const loading = ref(false)
const trendLoading = ref(false)
const analysisLoading = ref(false)

// AI功能相关状态
const activeAITab = ref('report')
const aiReportLoading = ref(false)
const aiReport = ref('')
const aiReportThinking = ref('') // AI报告的思考过程
const aiReplyLoading = ref(false)
const aiReply = ref('')
const aiReplyThinking = ref('') // AI回复的思考过程
const complaintInput = ref('')

const filters = ref({
  startDate: null,
  endDate: null,
  selectedCompanies: [],
  selectedIndustries: [],
  selectedCategories: [],
  selectedIndustryLevel1: [],
  selectedIndustryLevel2: []
})

const filterOptions = ref({
  companies: [],
  industries: [],
  categories: [],
  industryLevel1: [],
  industryLevel2: []
})

const dashboardStats = ref({
  total_complaints: 0,
  companies_count: 0,
  industries_count: 0,
  repeat_companies_count: 0,
  company_ranking: [],
  date_range: {}
})

const trendPeriod = ref('day')
const trendData = ref([])
const timeSeriesResults = ref(null)

// Chart引用
const trendChart = ref(null)
const acfChart = ref(null)
const stlTrendChart = ref(null)
const stlSeasonalChart = ref(null)

// 初始化数据
const initializeDashboard = async () => {
  loading.value = true
  try {
    console.log('开始初始化仪表板...')
    
    // 同时获取数据摘要和筛选选项
    const [summaryResponse, filterOptionsResponse] = await Promise.all([
      getDataSummary().catch(err => {
        console.error('获取数据摘要失败:', err)
        return { data: null }
      }),
      getFilterOptions().catch(err => {
        console.error('获取筛选选项失败:', err)
        return { data: { companies: [], industries: [], categories: [] } }
      })
    ])
    
    console.log('数据摘要响应:', summaryResponse.data)
    console.log('筛选选项响应:', filterOptionsResponse.data)
    
    // 设置默认时间范围
    if (summaryResponse.data && summaryResponse.data.date_range) {
      filters.value.startDate = summaryResponse.data.date_range.start
      filters.value.endDate = summaryResponse.data.date_range.end
      console.log('设置时间范围:', filters.value.startDate, '至', filters.value.endDate)
    } else {
      // 如果没有数据范围，设置默认范围
      const endDate = new Date()
      const startDate = new Date()
      startDate.setFullYear(endDate.getFullYear() - 1)
      filters.value.startDate = startDate.toISOString().split('T')[0]
      filters.value.endDate = endDate.toISOString().split('T')[0]
      console.log('使用默认时间范围:', filters.value.startDate, '至', filters.value.endDate)
    }
    
    // 设置筛选选项
    if (filterOptionsResponse.data) {
      filterOptions.value = {
        companies: filterOptionsResponse.data.companies || [],
        industries: filterOptionsResponse.data.industry_classification || [], // 保持向后兼容
        categories: filterOptionsResponse.data.categories || [],
        industryLevel1: filterOptionsResponse.data.industry_level1 || [],
        industryLevel2: filterOptionsResponse.data.industry_level2 || []
      }
      console.log('筛选选项设置完成:', {
        companies: filterOptions.value.companies.length,
        industries: filterOptions.value.industries.length,
        categories: filterOptions.value.categories.length,
        industryLevel1: filterOptions.value.industryLevel1.length,
        industryLevel2: filterOptions.value.industryLevel2.length
      })
    }
    
    // 加载仪表板数据
    await loadDashboardData()
    await loadTrendData()
    
    console.log('仪表板初始化完成')
  } catch (error) {
    console.error('初始化仪表板失败:', error)
    ElMessage.error('初始化数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 加载仪表板统计数据
const loadDashboardData = async () => {
  if (!filters.value.startDate || !filters.value.endDate) {
    console.warn('时间范围未设置，跳过数据加载')
    return
  }
  
  loading.value = true
  try {
    const params = {
      start_date: filters.value.startDate,
      end_date: filters.value.endDate,
      companies: filters.value.selectedCompanies.length > 0 ? filters.value.selectedCompanies : undefined,
      industries: filters.value.selectedIndustries.length > 0 ? filters.value.selectedIndustries : undefined,
      categories: filters.value.selectedCategories.length > 0 ? filters.value.selectedCategories : undefined,
      industry_level1: filters.value.selectedIndustryLevel1.length > 0 ? filters.value.selectedIndustryLevel1 : undefined,
      industry_level2: filters.value.selectedIndustryLevel2.length > 0 ? filters.value.selectedIndustryLevel2 : undefined
    }
    
    console.log('加载仪表板数据，参数:', params)
    
    const response = await getDashboardStats(params)
    console.log('仪表板数据响应:', response.data)
    
    if (response.data) {
      if (response.data.error) {
        console.error('后端返回错误:', response.data.error)
        ElMessage.error('数据加载失败: ' + response.data.error)
      } else {
        dashboardStats.value = response.data
        console.log('仪表板数据更新成功:', dashboardStats.value)
      }
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败: ' + (error.response?.data?.error || error.message))
  } finally {
    loading.value = false
  }
}

// 加载趋势数据
const loadTrendData = async () => {
  if (!filters.value.startDate || !filters.value.endDate) return
  
  trendLoading.value = true
  try {
    const params = {
      start_date: filters.value.startDate,
      end_date: filters.value.endDate,
      period: trendPeriod.value,
      companies: filters.value.selectedCompanies.length > 0 ? filters.value.selectedCompanies : undefined,
      industries: filters.value.selectedIndustries.length > 0 ? filters.value.selectedIndustries : undefined,
      categories: filters.value.selectedCategories.length > 0 ? filters.value.selectedCategories : undefined,
      industry_level1: filters.value.selectedIndustryLevel1.length > 0 ? filters.value.selectedIndustryLevel1 : undefined,
      industry_level2: filters.value.selectedIndustryLevel2.length > 0 ? filters.value.selectedIndustryLevel2 : undefined
    }
    
    console.log('加载趋势数据，参数:', params)
    
    const response = await getTrendData(params)
    console.log('趋势数据响应:', response.data)
    
    if (response.data && response.data.data) {
      trendData.value = response.data.data
      console.log('趋势数据更新成功:', trendData.value.length, '个数据点')
      
      // 等待DOM更新后渲染趋势图
      await nextTick()
      renderTrendChart()
    } else if (response.data && response.data.error) {
      console.error('趋势数据获取失败:', response.data.error)
      ElMessage.error('趋势数据获取失败: ' + response.data.error)
    }
  } catch (error) {
    console.error('加载趋势数据失败:', error)
    ElMessage.error('加载趋势数据失败: ' + (error.response?.data?.error || error.message))
  } finally {
    trendLoading.value = false
  }
}

// 渲染趋势图表
const renderTrendChart = () => {
  if (!trendChart.value || trendData.value.length === 0) {
    console.warn('无法渲染趋势图表:', {
      hasContainer: !!trendChart.value,
      dataLength: trendData.value.length,
      dataExample: trendData.value.slice(0, 2)
    })
    return
  }
  
  console.log('开始渲染趋势图表，数据点:', trendData.value.length)
  
  const container = trendChart.value
  
  // 清除之前的图表
  d3.select(container).selectAll("*").remove()
  
  const margin = { top: 20, right: 30, bottom: 30, left: 50 }
  const width = container.offsetWidth - margin.left - margin.right
  const height = container.offsetHeight - margin.top - margin.bottom
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 设置比例尺
  const xScale = d3.scaleBand()
    .domain(trendData.value.map(d => d.time))
    .range([0, width])
    .padding(0.1)
  
  const yScale = d3.scaleLinear()
    .domain([0, d3.max(trendData.value, d => d.count)])
    .nice()
    .range([height, 0])
  
  // 创建面积生成器
  const area = d3.area()
    .x((d, i) => xScale(d.time) + xScale.bandwidth() / 2)
    .y0(height)
    .y1(d => yScale(d.count))
    .curve(d3.curveMonotoneX)
  
  // 创建线条生成器
  const line = d3.line()
    .x((d, i) => xScale(d.time) + xScale.bandwidth() / 2)
    .y(d => yScale(d.count))
    .curve(d3.curveMonotoneX)
  
  // 添加渐变定义
  const gradient = svg.append("defs")
    .append("linearGradient")
    .attr("id", "areaGradient")
    .attr("gradientUnits", "userSpaceOnUse")
    .attr("x1", 0).attr("y1", height)
    .attr("x2", 0).attr("y2", 0)
  
  gradient.append("stop")
    .attr("offset", "0%")
    .attr("stop-color", "#409eff")
    .attr("stop-opacity", 0.1)
  
  gradient.append("stop")
    .attr("offset", "100%")
    .attr("stop-color", "#409eff")
    .attr("stop-opacity", 0.3)
  
  // 绘制面积图
  svg.append("path")
    .datum(trendData.value)
    .attr("fill", "url(#areaGradient)")
    .attr("d", area)
  
  // 绘制线条
  svg.append("path")
    .datum(trendData.value)
    .attr("fill", "none")
    .attr("stroke", "#409eff")
    .attr("stroke-width", 2)
    .attr("d", line)
  
  // 添加数据点
  svg.selectAll(".dot")
    .data(trendData.value)
    .enter().append("circle")
    .attr("class", "dot")
    .attr("cx", d => xScale(d.time) + xScale.bandwidth() / 2)
    .attr("cy", d => yScale(d.count))
    .attr("r", 4)
    .attr("fill", "#409eff")
    .on("mouseover", function(event, d) {
      // 显示提示框
      const tooltip = d3.select("body").append("div")
        .attr("class", "d3-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0, 0, 0, 0.8)")
        .style("color", "white")
        .style("padding", "8px")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("opacity", 0)
      
      tooltip.transition().duration(200).style("opacity", 1)
      tooltip.html(`时间: ${d.time}<br/>投诉数量: ${d.count}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px")
      
      d3.select(this).attr("r", 6)
    })
    .on("mouseout", function() {
      d3.selectAll(".d3-tooltip").remove()
      d3.select(this).attr("r", 4)
    })
  
  // 添加X轴 - 根据时间粒度智能控制显示
  const dataLength = trendData.value.length
  let tickValues = []
  let tickFormat = d => d
  const maxTicks = 10  // 固定显示10个刻度
  
  if (trendPeriod.value === 'month') {
    // 按月：固定显示10个刻度
    if (dataLength <= maxTicks) {
      tickValues = trendData.value.map(d => d.time)
    } else {
      const interval = Math.floor(dataLength / maxTicks)
      tickValues = trendData.value.filter((d, i) => i % interval === 0).map(d => d.time)
      const lastTime = trendData.value[dataLength - 1].time
      if (!tickValues.includes(lastTime)) {
        tickValues.push(lastTime)
      }
    }
    tickFormat = d => {
      // 格式为 2025.03
      const match = d.match(/(\d{4})[-年](\d{1,2})/)
      if (match) {
        const year = match[1]
        const month = match[2].padStart(2, '0')
        return `${year}.${month}`
      }
      return d
    }
  } else if (trendPeriod.value === 'week') {
    // 按周：固定显示10个刻度
    if (dataLength <= maxTicks) {
      tickValues = trendData.value.map(d => d.time)
    } else {
      const interval = Math.floor(dataLength / maxTicks)
      tickValues = trendData.value.filter((d, i) => i % interval === 0).map(d => d.time)
      const lastTime = trendData.value[dataLength - 1].time
      if (!tickValues.includes(lastTime)) {
        tickValues.push(lastTime)
      }
    }
    
    tickFormat = d => {
      // 尝试从周数据中提取日期，格式为 2025.09.28
      const dateMatch = d.match(/(\d{4})-(\d{2})-(\d{2})/)
      if (dateMatch) {
        return `${dateMatch[1]}.${dateMatch[2]}.${dateMatch[3]}`
      }
      // 如果只是"第XX周"，返回简短格式
      const weekMatch = d.match(/第(\d+)周/)
      if (weekMatch) {
        return `W${weekMatch[1]}`
      }
      return d
    }
  } else {
    // 按天：固定显示10个刻度，带年份
    if (dataLength <= maxTicks) {
      tickValues = trendData.value.map(d => d.time)
    } else {
      const interval = Math.floor(dataLength / maxTicks)
      tickValues = trendData.value.filter((d, i) => i % interval === 0).map(d => d.time)
      const lastTime = trendData.value[dataLength - 1].time
      if (!tickValues.includes(lastTime)) {
        tickValues.push(lastTime)
      }
    }
    
    tickFormat = d => {
      // 日期格式：YYYY.MM.DD（带年份）
      const match = d.match(/(\d{4})[-年](\d{1,2})[-月](\d{1,2})/)
      if (match) {
        const year = match[1]
        const month = match[2].padStart(2, '0')
        const day = match[3].padStart(2, '0')
        return `${year}.${month}.${day}`
      }
      return d
    }
  }
  
  // X轴不倾斜，水平显示
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale)
      .tickValues(tickValues)
      .tickFormat(tickFormat))
    .selectAll("text")
    .style("text-anchor", "middle")
    .style("font-size", "8px")
    .attr("dy", "0.8em")
  
  // 添加Y轴
  svg.append("g")
    .call(d3.axisLeft(yScale))
    .selectAll("text")
    .style("font-size", "11px")
  
  // 添加Y轴标签
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "11px")
    .style("fill", "#666")
    .text("投诉数量")
}

// 执行时间序列分析
const performTimeSeriesAnalysis = async () => {
  if (!filters.value.startDate || !filters.value.endDate) {
    ElMessage.warning('请先设置时间范围')
    return
  }
  
  analysisLoading.value = true
  try {
    const params = {
      start_date: filters.value.startDate,
      end_date: filters.value.endDate,
      methods: ['acf', 'stl'],
      companies: filters.value.selectedCompanies.length > 0 ? filters.value.selectedCompanies : undefined,
      industries: filters.value.selectedIndustries.length > 0 ? filters.value.selectedIndustries : undefined,
      categories: filters.value.selectedCategories.length > 0 ? filters.value.selectedCategories : undefined,
      industry_level1: filters.value.selectedIndustryLevel1.length > 0 ? filters.value.selectedIndustryLevel1 : undefined,
      industry_level2: filters.value.selectedIndustryLevel2.length > 0 ? filters.value.selectedIndustryLevel2 : undefined
    }
    
    console.log('执行时间序列分析，参数:', params)
    
    const response = await analyzeTimeSeries(params)
    console.log('时间序列分析响应:', response.data)
    
    if (response.data && response.data.analysis) {
      timeSeriesResults.value = response.data
      
      // 等待DOM更新后渲染分析图表
      await nextTick()
      renderAnalysisCharts()
      
      ElMessage.success('时间序列分析完成')
    } else {
      console.error('时间序列分析数据格式错误:', response.data)
      ElMessage.error('时间序列分析数据格式错误')
    }
  } catch (error) {
    console.error('时间序列分析失败:', error)
    ElMessage.error('时间序列分析失败: ' + (error.response?.data?.error || error.message))
  } finally {
    analysisLoading.value = false
  }
}

// 渲染分析图表
const renderAnalysisCharts = () => {
  if (!timeSeriesResults.value || !timeSeriesResults.value.analysis) {
    console.warn('无分析结果数据可渲染')
    return
  }
  
  console.log('渲染分析图表，分析结果:', timeSeriesResults.value.analysis)
  
  // 延迟渲染，确保DOM完全更新和容器尺寸正确
  setTimeout(() => {
    // 渲染ACF图表
    if (timeSeriesResults.value.analysis.acf && !timeSeriesResults.value.analysis.acf.error && acfChart.value) {
      console.log('渲染ACF图表，容器尺寸:', {
        width: acfChart.value.offsetWidth,
        height: acfChart.value.offsetHeight
      })
      renderACFChart()
    } else if (timeSeriesResults.value.analysis.acf && timeSeriesResults.value.analysis.acf.error) {
      console.error('ACF分析错误:', timeSeriesResults.value.analysis.acf.error)
    }
    
    // 渲染STL分解图表
    if (timeSeriesResults.value.analysis.stl && !timeSeriesResults.value.analysis.stl.error) {
      console.log('渲染STL分解图表')
      if (stlTrendChart.value && stlSeasonalChart.value) {
        console.log('STL容器尺寸:', {
          trendWidth: stlTrendChart.value.offsetWidth,
          trendHeight: stlTrendChart.value.offsetHeight,
          seasonalWidth: stlSeasonalChart.value.offsetWidth,
          seasonalHeight: stlSeasonalChart.value.offsetHeight
        })
      }
      renderSTLCharts()
    } else if (timeSeriesResults.value.analysis.stl && timeSeriesResults.value.analysis.stl.error) {
      console.error('STL分解错误:', timeSeriesResults.value.analysis.stl.error)
    }
  }, 100)
}

// 渲染ACF图表
const renderACFChart = () => {
  if (!acfChart.value) {
    console.warn('ACF图表容器不存在')
    return
  }
  
  const container = acfChart.value
  const acfData = timeSeriesResults.value.analysis.acf.acf_values
  const confidenceInterval = timeSeriesResults.value.analysis.acf.confidence_interval
  
  // 检查容器尺寸
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn('ACF容器尺寸为0，延迟渲染')
    setTimeout(() => renderACFChart(), 200)
    return
  }
  
  // 清除之前的图表
  d3.select(container).selectAll("*").remove()
  
  const margin = { top: 20, right: 20, bottom: 30, left: 50 }
  const width = container.offsetWidth - margin.left - margin.right
  const height = 180 - margin.top - margin.bottom
  
  if (width <= 0 || height <= 0) {
    console.warn('ACF图表计算尺寸无效:', { width, height })
    return
  }
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 设置比例尺
  const xScale = d3.scaleBand()
    .domain(acfData.map(d => d.lag))
    .range([0, width])
    .padding(0.1)
  
  const yScale = d3.scaleLinear()
    .domain(d3.extent(acfData, d => d.acf_value))
    .nice()
    .range([height, 0])
  
  // 绘制置信区间线
  svg.append("line")
    .attr("x1", 0)
    .attr("x2", width)
    .attr("y1", yScale(confidenceInterval))
    .attr("y2", yScale(confidenceInterval))
    .attr("stroke", "#f56c6c")
    .attr("stroke-width", 1)
    .attr("stroke-dasharray", "5,5")
  
  svg.append("line")
    .attr("x1", 0)
    .attr("x2", width)
    .attr("y1", yScale(-confidenceInterval))
    .attr("y2", yScale(-confidenceInterval))
    .attr("stroke", "#f56c6c")
    .attr("stroke-width", 1)
    .attr("stroke-dasharray", "5,5")
  
  // 绘制零线
  svg.append("line")
    .attr("x1", 0)
    .attr("x2", width)
    .attr("y1", yScale(0))
    .attr("y2", yScale(0))
    .attr("stroke", "#999")
    .attr("stroke-width", 1)
  
  // 绘制柱状图
  svg.selectAll(".bar")
    .data(acfData)
    .enter().append("rect")
    .attr("class", "bar")
    .attr("x", d => xScale(d.lag))
    .attr("width", xScale.bandwidth())
    .attr("y", d => yScale(Math.max(0, d.acf_value)))
    .attr("height", d => Math.abs(yScale(d.acf_value) - yScale(0)))
    .attr("fill", d => Math.abs(d.acf_value) > confidenceInterval ? "#e6a23c" : "#409eff")
    .on("mouseover", function(event, d) {
      const tooltip = d3.select("body").append("div")
        .attr("class", "d3-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0, 0, 0, 0.8)")
        .style("color", "white")
        .style("padding", "8px")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("opacity", 0)
      
      tooltip.transition().duration(200).style("opacity", 1)
      tooltip.html(`滞后阶数: ${d.lag}<br/>ACF值: ${d.acf_value.toFixed(4)}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px")
    })
    .on("mouseout", function() {
      d3.selectAll(".d3-tooltip").remove()
    })
  
  // 添加坐标轴
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale))
    .selectAll("text")
    .style("font-size", "10px")
  
  svg.append("g")
    .call(d3.axisLeft(yScale))
    .selectAll("text")
    .style("font-size", "10px")
  
  // 添加轴标签
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "10px")
    .text("ACF值")
  
  svg.append("text")
    .attr("transform", `translate(${width / 2}, ${height + margin.bottom - 5})`)
    .style("text-anchor", "middle")
    .style("font-size", "10px")
    .text("滞后阶数")
}

// 渲染STL分解图表
const renderSTLCharts = () => {
  const stlData = timeSeriesResults.value.analysis.stl
  
  // 渲染趋势分量图
  if (stlTrendChart.value && stlData.trend) {
    renderSTLChart(stlTrendChart.value, stlData.trend, '趋势分量', '#67c23a')
  }
  
  // 渲染季节分量图
  if (stlSeasonalChart.value && stlData.seasonal) {
    renderSTLChart(stlSeasonalChart.value, stlData.seasonal, '季节分量', '#e6a23c')
  }
}

// 渲染STL单个分量图表的通用函数
const renderSTLChart = (container, data, title, color) => {
  console.log(`渲染STL图表: ${title}, 数据点数: ${data?.length || 0}`)
  
  if (!container || !data || data.length === 0) {
    console.warn(`无法渲染${title}图表:`, { hasContainer: !!container, dataLength: data?.length || 0 })
    return
  }
  
  // 检查容器尺寸
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn(`${title}容器尺寸为0，延迟渲染`)
    setTimeout(() => renderSTLChart(container, data, title, color), 200)
    return
  }
  
  // 清除之前的图表
  d3.select(container).selectAll("*").remove()
  
  const margin = { top: 15, right: 20, bottom: 25, left: 50 }
  const width = container.offsetWidth - margin.left - margin.right
  const height = 140 - margin.top - margin.bottom
  
  if (width <= 0 || height <= 0) {
    console.warn(`${title}图表计算尺寸无效:`, { width, height, containerWidth: container.offsetWidth, containerHeight: container.offsetHeight })
    return
  }
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 处理时间数据，尝试多种日期格式
  const parseDate = d3.timeParse("%Y-%m-%d")
  const parseDateTime = d3.timeParse("%Y-%m-%dT%H:%M:%S")
  const parseSimpleDate = d3.timeParse("%Y-%m-%d")
  
  const processedData = data.map((d, index) => {
    let parsedDate = null
    
    // 尝试不同的日期解析方式
    if (typeof d.date === 'string') {
      parsedDate = parseDate(d.date) || parseDateTime(d.date) || parseSimpleDate(d.date.split('T')[0])
    } else if (d.date instanceof Date) {
      parsedDate = d.date
    }
    
    // 如果日期解析失败，使用索引创建假日期
    if (!parsedDate) {
      const startDate = new Date('2023-01-01')
      parsedDate = new Date(startDate.getTime() + index * 24 * 60 * 60 * 1000)
      console.warn(`日期解析失败，使用索引日期: ${d.date} -> ${parsedDate}`)
    }
    
    return {
      date: parsedDate,
      value: parseFloat(d.value) || 0
    }
  }).filter(d => d.date !== null && !isNaN(d.value))
  
  console.log(`${title} 处理后数据点数: ${processedData.length}`)
  
  if (processedData.length === 0) {
    console.error(`${title}: 没有有效数据点`)
    return
  }
  
  // 设置比例尺
  const xScale = d3.scaleTime()
    .domain(d3.extent(processedData, d => d.date))
    .range([0, width])
  
  const yExtent = d3.extent(processedData, d => d.value)
  const yScale = d3.scaleLinear()
    .domain(yExtent)
    .nice()
    .range([height, 0])
  
  // 创建线条生成器
  const line = d3.line()
    .x(d => xScale(d.date))
    .y(d => yScale(d.value))
    .curve(d3.curveMonotoneX)
  
  // 绘制线条
  svg.append("path")
    .datum(processedData)
    .attr("fill", "none")
    .attr("stroke", color)
    .attr("stroke-width", 2)
    .attr("d", line)
  
  // 添加数据点（数据点太多时跳过）
  if (processedData.length <= 100) {
    svg.selectAll(".dot")
      .data(processedData)
      .enter().append("circle")
      .attr("class", "dot")
      .attr("cx", d => xScale(d.date))
      .attr("cy", d => yScale(d.value))
      .attr("r", 2)
      .attr("fill", color)
      .on("mouseover", function(event, d) {
        const tooltip = d3.select("body").append("div")
          .attr("class", "d3-tooltip")
          .style("position", "absolute")
          .style("background", "rgba(0, 0, 0, 0.8)")
          .style("color", "white")
          .style("padding", "8px")
          .style("border-radius", "4px")
          .style("font-size", "12px")
          .style("pointer-events", "none")
          .style("opacity", 0)
        
        tooltip.transition().duration(200).style("opacity", 1)
        tooltip.html(`日期: ${d3.timeFormat("%Y-%m-%d")(d.date)}<br/>值: ${d.value.toFixed(4)}`)
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 28) + "px")
        
        d3.select(this).attr("r", 4)
      })
      .on("mouseout", function() {
        d3.selectAll(".d3-tooltip").remove()
        d3.select(this).attr("r", 2)
      })
  }
  
  // 添加坐标轴 - 智能控制X轴刻度数量
  const dataLength = processedData.length
  let tickCount = 5 // 默认显示5个刻度
  
  if (dataLength <= 10) {
    tickCount = dataLength
  } else if (dataLength <= 30) {
    tickCount = 6
  } else if (dataLength <= 60) {
    tickCount = 8
  } else {
    tickCount = 10
  }
  
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale)
      .ticks(tickCount)
      .tickFormat(d3.timeFormat("%m-%d")))
    .selectAll("text")
    .style("font-size", "10px")
  
  svg.append("g")
    .call(d3.axisLeft(yScale))
    .selectAll("text")
    .style("font-size", "10px")
  
  // 添加轴标签
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "10px")
    .text("值")
}

// 获取排名样式类
const getRankingClass = (index) => {
  if (index === 0) return 'rank-first'
  if (index === 1) return 'rank-second' 
  if (index === 2) return 'rank-third'
  return ''
}

// 清除筛选条件
const clearFilters = () => {
  filters.value.selectedCompanies = []
  filters.value.selectedIndustries = []
  filters.value.selectedCategories = []
  filters.value.selectedIndustryLevel1 = []
  filters.value.selectedIndustryLevel2 = []
  loadDashboardData()
  loadTrendData()
}

// 获取时间粒度标签
const getPeriodLabel = () => {
  const labels = {
    day: '按天',
    week: '按周',
    month: '按月'
  }
  return labels[trendPeriod.value] || '按天'
}

// ========== AI功能相关函数 ==========

// 生成AI报告
const handleGenerateAIReport = async () => {
  if (!filters.value.startDate || !filters.value.endDate) {
    ElMessage.warning('请先选择时间范围')
    return
  }
  
  aiReportLoading.value = true
  try {
    const params = {
      start_date: filters.value.startDate,
      end_date: filters.value.endDate,
      use_ai: true
    }
    
    console.log('生成AI报告，参数:', params)
    const response = await generateAIReport(params)
    
    if (response.data && response.data.success) {
      aiReport.value = response.data.report
      aiReportThinking.value = response.data.thinking || '' // 获取思考过程
      console.log('AI报告生成成功，包含思考过程:', !!response.data.thinking)
      ElMessage.success('AI报告生成成功')
    } else {
      throw new Error(response.data?.error || '报告生成失败')
    }
  } catch (error) {
    console.error('生成AI报告失败:', error)
    ElMessage.error('生成AI报告失败: ' + (error.response?.data?.error || error.message))
  } finally {
    aiReportLoading.value = false
  }
}

// 生成AI回复
const handleGenerateAIReply = async () => {
  if (!complaintInput.value.trim()) {
    ElMessage.warning('请输入投诉内容')
    return
  }
  
  aiReplyLoading.value = true
  try {
    const params = {
      complaint_content: complaintInput.value
    }
    
    console.log('生成AI回复，参数:', params)
    const response = await generateAIReply(params)
    
    if (response.data && response.data.success) {
      aiReply.value = response.data.reply
      aiReplyThinking.value = response.data.thinking || '' // 获取思考过程
      console.log('AI回复生成成功，包含思考过程:', !!response.data.thinking)
      ElMessage.success('AI回复生成成功')
    } else {
      throw new Error(response.data?.error || '回复生成失败')
    }
  } catch (error) {
    console.error('生成AI回复失败:', error)
    ElMessage.error('生成AI回复失败: ' + (error.response?.data?.error || error.message))
  } finally {
    aiReplyLoading.value = false
  }
}

// 使用示例投诉内容
const handleUseExample = () => {
  complaintInput.value = '市民反映，今年2022年4月19日的时候在北京欢乐水魔方公众号上购买的夏季的卡，当时购买的时候说随时可以退款，但是夏天因为一些原因没有过去游玩。当时说只要不开通就可以随时退款，自己没有开通，在公众号申请退款已经申请好几个月了，一直显示退款中，但是一直得不到处理。'
  aiReply.value = ''
}

// 复制回复内容
const handleCopyReply = () => {
  if (aiReply.value) {
    navigator.clipboard.writeText(aiReply.value).then(() => {
      ElMessage.success('已复制到剪贴板')
    }).catch(err => {
      console.error('复制失败:', err)
      ElMessage.error('复制失败，请手动复制')
    })
  }
}

// 清除回复
const handleClearReply = () => {
  aiReply.value = ''
}

// 格式化报告文本（将换行符转换为HTML）
const formatReportText = (text) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br/>')
}


// 组件挂载
onMounted(() => {
  console.log('组件挂载，开始初始化...')
  initializeDashboard()
})
</script>

<style scoped>
/* 容器和整体布局 */
.dashboard-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 8px;
  overflow: hidden;
}

/* Grid 布局 - 3列2行 */
.dashboard-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 2fr 1.2fr;
  grid-template-rows: 1fr 1.33fr;
  gap: 8px;
  min-height: 0;
}

.grid-item {
  min-height: 0;
  min-width: 0;
}

/* 控制台 - 左上 */
.console-panel {
  grid-column: 1;
  grid-row: 1;
}

/* 时序分析 - 中上 */
.timeseries-panel {
  grid-column: 2;
  grid-row: 1;
}

/* AI面板 - 右侧，跨两行 */
.ai-panel {
  grid-column: 3;
  grid-row: 1 / 3;
}

/* 趋势图+企业排名 - 左下+中下，跨两列 */
.combined-panel {
  grid-column: 1 / 3;
  grid-row: 2;
}

/* 卡片样式 */
.full-height-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.full-height-card :deep(.el-card__header) {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.full-height-card :deep(.el-card__body) {
  flex: 1;
  padding: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-header-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  color: #2c3e50;
}

/* 可滚动内容区域 */
.scrollable-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 5px;
}

.scrollable-content::-webkit-scrollbar {
  width: 6px;
}

.scrollable-content::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.scrollable-content::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}

/* 控制台样式 */
.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
}

/* 企业排名样式 */
.ranking-item-compact {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
  transition: all 0.2s ease;
}

.ranking-item-compact:hover {
  background-color: #f8f9fa;
  border-radius: 6px;
  margin: 0 -6px;
  padding: 8px 6px;
}

.ranking-item-compact:last-child {
  border-bottom: none;
}

.rank-number-compact {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
  margin-right: 10px;
  background-color: #ecf0f1;
  color: #7f8c8d;
  flex-shrink: 0;
}

.rank-first .rank-number-compact {
  background: linear-gradient(45deg, #f1c40f, #f39c12);
  color: white;
}

.rank-second .rank-number-compact {
  background: linear-gradient(45deg, #95a5a6, #7f8c8d);
  color: white;
}

.rank-third .rank-number-compact {
  background: linear-gradient(45deg, #e67e22, #d35400);
  color: white;
}

.company-info-compact {
  flex: 1;
  min-width: 0;
}

.company-name-compact {
  font-weight: 500;
  font-size: 13px;
  color: #2c3e50;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.complaint-count-compact {
  color: #7f8c8d;
  font-size: 11px;
}

/* 组合面板样式（统计指标+趋势图+排名） */
.combined-content {
  display: flex;
  gap: 12px;
  height: 100%;
}

/* 左侧统计指标侧边栏 */
.stats-sidebar {
  width: 70px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-right: 1px solid #e4e7ed;
  padding-right: 8px;
}

.stat-item-vertical {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  border-radius: 5px;
  background: #f8f9fa;
  text-align: center;
  flex: 1;
}

.stat-item-vertical .el-icon {
  margin-bottom: 4px;
}

.total-stat {
  border-left: 3px solid #3498db;
}

.company-stat {
  border-left: 3px solid #e74c3c;
}

.industry-stat {
  border-left: 3px solid #2ecc71;
}

.repeat-stat {
  border-left: 3px solid #f39c12;
}

.stat-content-vertical {
  width: 100%;
}

.stat-value-vertical {
  font-size: 16px;
  font-weight: bold;
  color: #2c3e50;
  line-height: 1.1;
  margin-bottom: 2px;
}

.stat-label-vertical {
  color: #7f8c8d;
  font-size: 9px;
  line-height: 1.1;
  word-wrap: break-word;
}

/* 中间趋势图区域 */
.trend-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 右侧企业排名 */
.ranking-section {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e4e7ed;
  padding-left: 12px;
  overflow: hidden;
}

.ranking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 13px;
  color: #2c3e50;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.ranking-list-compact {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 5px;
}

.ranking-list-compact::-webkit-scrollbar {
  width: 6px;
}

.ranking-list-compact::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.ranking-list-compact::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}

.trend-chart-wrapper {
  flex: 1;
  min-height: 0;
}

/* 时序分析样式 */
.analysis-result-compact {
  margin-bottom: 15px;
}

.analysis-result-compact h5 {
  color: #2c3e50;
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
}

.stl-compact {
  margin-bottom: 10px;
}

.stl-label {
  color: #606266;
  font-size: 12px;
  margin: 5px 0;
  font-weight: 500;
}

/* AI面板样式 */
.ai-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.ai-tabs :deep(.el-tabs__header) {
  margin: 0 0 10px 0;
}

.ai-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.ai-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.ai-tab-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-action-bar {
  display: flex;
  gap: 8px;
}

.ai-output-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 5px;
  min-height: 0;
}

.ai-output-area::-webkit-scrollbar {
  width: 6px;
}

.ai-output-area::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.complaint-input-compact {
  font-size: 13px;
}

.complaint-input-compact :deep(textarea) {
  font-size: 13px;
}

/* AI结果内容 */
.ai-result-content {
  font-size: 13px;
  line-height: 1.6;
}

.thinking-section-compact {
  margin-bottom: 12px;
  padding: 10px;
  background: #f0f9ff;
  border-left: 3px solid #409eff;
  border-radius: 4px;
  font-size: 12px;
}

.thinking-label {
  font-weight: 600;
  color: #909399;
}

.thinking-content-compact {
  color: #606266;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  background: #fff;
  padding: 8px;
  border-radius: 3px;
  border: 1px solid #e4e7ed;
  max-height: 100px;
  overflow-y: auto;
  margin-top: 6px;
}

.thinking-content-compact::-webkit-scrollbar {
  width: 4px;
}

.thinking-content-compact::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 2px;
}

.report-text-compact {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  line-height: 1.6;
  font-size: 13px;
}

.reply-text-compact {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  border-left: 3px solid #67c23a;
  line-height: 1.6;
  color: #495057;
  font-size: 13px;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 15px;
  color: #909399;
  text-align: center;
  height: 100%;
}

.empty-state p {
  margin: 10px 0 0 0;
  font-size: 13px;
}

/* 响应式调整 */
@media (max-width: 1600px) {
  .dashboard-grid {
    grid-template-columns: 0.9fr 2fr 1.1fr;
  }
  
  .ranking-section {
    width: 240px;
  }
  
  .stat-value-compact {
    font-size: 15px;
  }
}

@media (max-width: 1400px) {
  .dashboard-grid {
    grid-template-columns: 0.8fr 2fr 1fr;
  }
  
  .ranking-section {
    width: 220px;
  }
  
  .stat-value-compact {
    font-size: 14px;
  }
  
  .stat-label-compact {
    font-size: 9px;
  }
}
</style>