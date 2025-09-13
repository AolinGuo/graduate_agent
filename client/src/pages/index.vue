<template>
  <div class="dashboard-container">
    <!-- 头部标题和筛选区域 -->
    <div class="dashboard-header">
      <div class="title-section">
        <h1>工商投诉可视分析系统</h1>
        <p>AI赋能投诉数据统计分析平台</p>
      </div>
      
      <div class="filter-section">
        <el-card class="filter-card" shadow="never">
          <el-form :model="filters" label-width="80px" size="small">
            <!-- 时间筛选 -->
            <el-row :gutter="20">
              <el-col :span="6">
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
              </el-col>
              
              <el-col :span="6">
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
              </el-col>
              
              <el-col :span="6">
                <el-form-item label="企业选择">
                  <el-select
                    v-model="filters.selectedCompanies"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择企业"
                    style="width: 100%"
                    :max-collapse-tags="2"
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
              </el-col>
              
              <el-col :span="6">
                <el-form-item>
                  <el-button type="primary" @click="loadDashboardData" :loading="loading" style="width: 100%">
                    <el-icon><Refresh /></el-icon>
                    刷新数据
                  </el-button>
                </el-form-item>
              </el-col>
            </el-row>
            
            <!-- 分类筛选 -->
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="行业大类">
                  <el-select
                    v-model="filters.selectedIndustryLevel1"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择行业大类"
                    style="width: 100%"
                    :max-collapse-tags="2"
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
              </el-col>
              <el-col :span="8">
                <el-form-item label="行业中类">
                  <el-select
                    v-model="filters.selectedIndustryLevel2"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择行业中类"
                    style="width: 100%"
                    :max-collapse-tags="2"
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
              </el-col>
              <el-col :span="8">
                <el-form-item label="详细分类">
                  <el-select
                    v-model="filters.selectedIndustries"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择详细分类"
                    style="width: 100%"
                    :max-collapse-tags="2"
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
              </el-col>
            </el-row>
            
            <!-- 问题分类单独一行 -->
            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item label="问题分类">
                  <el-select
                    v-model="filters.selectedCategories"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择问题分类"
                    style="width: 100%"
                    :max-collapse-tags="5"
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
              </el-col>
            </el-row>
            
            <!-- 快速筛选按钮 -->
            <el-row>
              <el-col :span="24">
                <el-form-item>
                  <el-space>
                    <el-button @click="clearFilters" size="small">
                      <el-icon><RefreshLeft /></el-icon>
                      重置筛选
                    </el-button>
                    <el-tag v-if="filters.selectedCompanies.length > 0" type="info" closable @close="filters.selectedCompanies = []; loadDashboardData()">
                      已选企业: {{ filters.selectedCompanies.length }}个
                    </el-tag>
                    <el-tag v-if="filters.selectedIndustries.length > 0" type="success" closable @close="filters.selectedIndustries = []; loadDashboardData()">
                      已选行业: {{ filters.selectedIndustries.length }}个
                    </el-tag>
                    <el-tag v-if="filters.selectedCategories.length > 0" type="warning" closable @close="filters.selectedCategories = []; loadDashboardData()">
                      已选问题: {{ filters.selectedCategories.length }}个
                    </el-tag>
                  </el-space>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </div>
    </div>

    <!-- 统计指标卡片区域 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <div class="stat-icon total-icon">
                <el-icon size="24"><Document /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardStats.total_complaints || 0 }}</div>
                <div class="stat-label">投诉总量</div>
              </div>
          </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <div class="stat-icon company-icon">
                <el-icon size="24"><OfficeBuilding /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardStats.companies_count || 0 }}</div>
                <div class="stat-label">涉及企业数</div>
              </div>
            </div>
          </el-card>
          </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <div class="stat-icon industry-icon">
                <el-icon size="24"><Grid /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardStats.industries_count || 0 }}</div>
                <div class="stat-label">涉及行业数</div>
    </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <div class="stat-icon repeat-icon">
                <el-icon size="24"><Warning /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ dashboardStats.repeat_companies_count || 0 }}</div>
                <div class="stat-label">月内重复投诉企业数</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <el-row :gutter="20">
        <!-- 投诉趋势图表 -->
        <el-col :span="16">
          <el-card class="chart-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>投诉趋势分析</span>
                <div class="period-selector">
                  <el-radio-group v-model="trendPeriod" size="small" @change="loadTrendData">
                    <el-radio-button label="day">按天</el-radio-button>
                    <el-radio-button label="week">按周</el-radio-button>
                    <el-radio-button label="month">按月</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
            </template>
            <div v-loading="trendLoading" style="position: relative;">
              <div ref="trendChart" style="width: 100%; height: 400px;"></div>
            </div>
          </el-card>
        </el-col>
        
        <!-- 企业投诉排名 -->
        <el-col :span="8">
          <el-card class="ranking-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>企业投诉量排名</span>
                <el-tag type="info" size="small">TOP 10</el-tag>
              </div>
            </template>
            <div v-loading="loading">
              <div class="ranking-list">
                <div 
                  v-for="(item, index) in dashboardStats.company_ranking || []" 
                  :key="index"
                  class="ranking-item"
                  :class="getRankingClass(index)"
                >
                  <div class="rank-number">{{ index + 1 }}</div>
                  <div class="company-info">
                    <div class="company-name" :title="item.name">{{ item.name }}</div>
                    <div class="complaint-count">{{ item.count }} 件投诉</div>
                  </div>
                </div>
              </div>
              
              <div v-if="(!dashboardStats.company_ranking || dashboardStats.company_ranking.length === 0) && !loading" class="empty-ranking">
                <el-empty description="暂无数据" :image-size="80"></el-empty>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 时间序列分析区域 -->
    <div class="analysis-section">
      <el-card class="analysis-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>时间序列分析</span>
            <el-button type="text" @click="performTimeSeriesAnalysis" :loading="analysisLoading">
              <el-icon><TrendCharts /></el-icon>
              执行分析
            </el-button>
          </div>
        </template>
        
        <div v-if="timeSeriesResults">
          <!-- ACF分析结果 -->
          <div v-if="timeSeriesResults.analysis.acf && !timeSeriesResults.analysis.acf.error" class="analysis-result">
            <h4>ACF自相关分析</h4>
            <p class="analysis-info">置信区间: ±{{ timeSeriesResults.analysis.acf.confidence_interval?.toFixed(4) }}</p>
            <div ref="acfChart" style="width: 100%; height: 300px;"></div>
          </div>
          
          <!-- STL分解结果 -->
          <div v-if="timeSeriesResults.analysis.stl && !timeSeriesResults.analysis.stl.error" class="analysis-result">
            <h4>STL季节性分解（月周期）</h4>
            
            <!-- 趋势分量 -->
            <div class="stl-chart-container">
              <h5>趋势分量</h5>
              <div ref="stlTrendChart" style="width: 100%; height: 280px; margin-bottom: 20px;"></div>
            </div>
            
            <!-- 季节分量 -->
            <div class="stl-chart-container">
              <h5>季节分量</h5>
              <div ref="stlSeasonalChart" style="width: 100%; height: 280px;"></div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 分析说明 -->
    <div class="analysis-info" v-if="timeSeriesResults || analysisLoading">
      <el-alert
        title="时间序列分析"
        description="以下图表显示投诉数据的自相关性分析和季节性分解结果"
        type="info"
        show-icon
        :closable="false"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Refresh, Document, OfficeBuilding, Grid, Warning, TrendCharts, RefreshLeft 
} from '@element-plus/icons-vue'
import { 
  getDashboardStats, 
  getTrendData, 
  analyzeTimeSeries,
  getDataSummary,
  getFilterOptions
} from '@/stores/complaint-store'
import * as d3 from 'd3'

// 响应式数据
const loading = ref(false)
const trendLoading = ref(false)
const analysisLoading = ref(false)

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
  
  const margin = { top: 40, right: 30, bottom: 40, left: 50 }
  const width = container.offsetWidth - margin.left - margin.right
  const height = 400 - margin.top - margin.bottom
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 添加标题
  svg.append("text")
    .attr("x", width / 2)
    .attr("y", -10)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "600")
    .style("fill", "#2c3e50")
    .text(`投诉数量趋势 (${getPeriodLabel()})`)
  
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
  
  // 添加X轴
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale))
    .selectAll("text")
    .style("text-anchor", "end")
    .attr("dx", "-.8em")
    .attr("dy", ".15em")
    .attr("transform", "rotate(-45)")
  
  // 添加Y轴
  svg.append("g")
    .call(d3.axisLeft(yScale))
  
  // 添加Y轴标签
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "12px")
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
  
  // 渲染ACF图表
  if (timeSeriesResults.value.analysis.acf && !timeSeriesResults.value.analysis.acf.error && acfChart.value) {
    console.log('渲染ACF图表')
    renderACFChart()
  } else if (timeSeriesResults.value.analysis.acf && timeSeriesResults.value.analysis.acf.error) {
    console.error('ACF分析错误:', timeSeriesResults.value.analysis.acf.error)
  }
  
  // 渲染STL分解图表
  if (timeSeriesResults.value.analysis.stl && !timeSeriesResults.value.analysis.stl.error) {
    console.log('渲染STL分解图表')
    renderSTLCharts()
  } else if (timeSeriesResults.value.analysis.stl && timeSeriesResults.value.analysis.stl.error) {
    console.error('STL分解错误:', timeSeriesResults.value.analysis.stl.error)
  }
}

// 渲染ACF图表
const renderACFChart = () => {
  if (!acfChart.value) return
  
  const container = acfChart.value
  const acfData = timeSeriesResults.value.analysis.acf.acf_values
  const confidenceInterval = timeSeriesResults.value.analysis.acf.confidence_interval
  
  // 清除之前的图表
  d3.select(container).selectAll("*").remove()
  
  const margin = { top: 40, right: 30, bottom: 40, left: 60 }
  const width = container.offsetWidth - margin.left - margin.right
  const height = 300 - margin.top - margin.bottom
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 添加标题
  svg.append("text")
    .attr("x", width / 2)
    .attr("y", -10)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "600")
    .text("自相关函数(ACF)")
  
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
  
  svg.append("g")
    .call(d3.axisLeft(yScale))
  
  // 添加轴标签
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "12px")
    .text("ACF值")
  
  svg.append("text")
    .attr("transform", `translate(${width / 2}, ${height + margin.bottom - 5})`)
    .style("text-anchor", "middle")
    .style("font-size", "12px")
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
  console.log(`渲染STL图表: ${title}, 数据点数: ${data.length}`)
  
  if (!container || !data || data.length === 0) {
    console.warn(`无法渲染${title}图表:`, { hasContainer: !!container, dataLength: data.length })
    return
  }
  
  // 清除之前的图表
  d3.select(container).selectAll("*").remove()
  
  const margin = { top: 40, right: 30, bottom: 40, left: 60 }
  const width = container.offsetWidth - margin.left - margin.right
  const height = 250 - margin.top - margin.bottom
  
  if (width <= 0 || height <= 0) {
    console.warn('图表容器尺寸无效:', { width, height })
    return
  }
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 添加标题
  svg.append("text")
    .attr("x", width / 2)
    .attr("y", -10)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "600")
    .text(title)
  
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
  
  // 添加坐标轴
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%m-%d")))
  
  svg.append("g")
    .call(d3.axisLeft(yScale))
  
  // 添加轴标签
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "12px")
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

// 组件挂载
onMounted(() => {
  console.log('组件挂载，开始初始化...')
  initializeDashboard()
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

.dashboard-header {
  margin-bottom: 30px;
}

.title-section {
  text-align: center;
  margin-bottom: 20px;
}

.title-section h1 {
  font-size: 32px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 10px 0;
  background: linear-gradient(45deg, #3498db, #2980b9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-section p {
  color: #7f8c8d;
  font-size: 16px;
  margin: 0;
}

.filter-card {
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.stats-section {
  margin-bottom: 30px;
}

.stat-card {
  border: none;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.stat-item {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.total-icon {
  background: linear-gradient(45deg, #3498db, #2980b9);
  color: white;
}

.company-icon {
  background: linear-gradient(45deg, #e74c3c, #c0392b);
  color: white;
}

.industry-icon {
  background: linear-gradient(45deg, #2ecc71, #27ae60);
  color: white;
}

.repeat-icon {
  background: linear-gradient(45deg, #f39c12, #d68910);
  color: white;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #2c3e50;
  line-height: 1;
  margin-bottom: 5px;
}

.stat-label {
  color: #7f8c8d;
  font-size: 14px;
  font-weight: 500;
}

.main-content, .analysis-section {
  margin-bottom: 30px;
}

.chart-card, .ranking-card, .analysis-card {
  border: none;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #2c3e50;
}

.period-selector .el-radio-button {
  border-radius: 6px;
}

.ranking-list {
  max-height: 400px;
  overflow-y: auto;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.3s ease;
}

.ranking-item:hover {
  background-color: #f8f9fa;
  border-radius: 8px;
  margin: 0 -8px;
  padding: 12px 8px;
}

.ranking-item:last-child {
  border-bottom: none;
}

.rank-number {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
  background-color: #ecf0f1;
  color: #7f8c8d;
}

.rank-first .rank-number {
  background: linear-gradient(45deg, #f1c40f, #f39c12);
  color: white;
}

.rank-second .rank-number {
  background: linear-gradient(45deg, #95a5a6, #7f8c8d);
  color: white;
}

.rank-third .rank-number {
  background: linear-gradient(45deg, #e67e22, #d35400);
  color: white;
}

.company-info {
  flex: 1;
  min-width: 0;
}

.company-name {
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.complaint-count {
  color: #7f8c8d;
  font-size: 13px;
}

.analysis-result {
  margin-bottom: 30px;
}

.analysis-result h4 {
  color: #2c3e50;
  margin: 0 0 15px 0;
  font-size: 16px;
}

.stl-chart-container {
  background: #fafafa;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
}

.stl-chart-container h5 {
  color: #606266;
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: bold;
}

.analysis-info {
  color: #7f8c8d;
  margin: 0 0 15px 0;
  font-size: 14px;
}

.analysis-info {
  margin-bottom: 20px;
}

.empty-ranking {
  padding: 40px 0;
  text-align: center;
}
</style>