<template>
  <div class="dashboard-container">
    <!-- 4-Column Grid Layout: Zero Gap -->
    <div class="dashboard-grid">
      
      <!-- Column 1: Left (Console -> Sunburst -> Stats -> TimeSeries) -->
      <div class="col-left">
        <!-- 1. Console (Compact with More Filters) -->
        <div class="panel-item console-wrapper">
          <div class="console-content-compact">
            <el-form :model="filters" label-width="35px" size="small" class="compact-form">
              <!-- 日期范围 -->
              <el-row :gutter="4">
                <el-col :span="12">
                  <el-form-item label="开始" class="mb-3">
                    <el-date-picker v-model="filters.startDate" type="date" placeholder="开始" value-format="YYYY-MM-DD" style="width: 100%" :clearable="false" size="small" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="结束" class="mb-3">
                    <el-date-picker v-model="filters.endDate" type="date" placeholder="结束" value-format="YYYY-MM-DD" style="width: 100%" :clearable="false" size="small" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <!-- 企业筛选 -->
              <el-form-item label="企业" class="mb-3">
                <el-select v-model="filters.selectedCompanies" multiple collapse-tags collapse-tags-tooltip placeholder="全部企业" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.companies" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <!-- 行业筛选 -->
              <el-form-item label="分类" class="mb-3">
                <el-select v-model="filters.selectedIndustries" multiple collapse-tags collapse-tags-tooltip placeholder="行业分类" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.industries" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="行1" class="mb-3">
                <el-select v-model="filters.selectedIndustryLevel1" multiple collapse-tags collapse-tags-tooltip placeholder="行业名称(1)" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.industry_level1" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="行2" class="mb-3">
                <el-select v-model="filters.selectedIndustryLevel2" multiple collapse-tags collapse-tags-tooltip placeholder="行业名称(2)" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.industry_level2" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="行3" class="mb-3">
                <el-select v-model="filters.selectedIndustryLevel3" multiple collapse-tags collapse-tags-tooltip placeholder="行业名称(3)" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.industry_level3" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <!-- 问题筛选 -->
              <el-form-item label="问题" class="mb-3">
                <el-select v-model="filters.selectedCategories" multiple collapse-tags collapse-tags-tooltip placeholder="问题分类" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.categories" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="问1" class="mb-3">
                <el-select v-model="filters.selectedIssueLevel1" multiple collapse-tags collapse-tags-tooltip placeholder="涉及问题(1)" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.issue_level1" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="问2" class="mb-3">
                <el-select v-model="filters.selectedIssueLevel2" multiple collapse-tags collapse-tags-tooltip placeholder="涉及问题(2)" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.issue_level2" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <!-- 操作按钮 -->
              <div class="filter-actions">
                <el-button @click="loadDashboardData" type="primary" size="small" plain style="width: 48%">刷新</el-button>
                <el-button @click="clearFilters" size="small" style="width: 48%">重置</el-button>
              </div>
            </el-form>
          </div>
        </div>

        <!-- 2. Sunburst -->
        <div class="panel-item sunburst-wrapper">
          <TheSunburstCharts
            :start-date="filters.startDate"
            :end-date="filters.endDate"
            :selected-companies="filters.selectedCompanies"
            :selected-categories="filters.selectedCategories"
            ref="sunburstChartsRef"
          />
        </div>

        <!-- 3. Stats (Horizontal Table) -->
        <div class="panel-item stats-wrapper">
          <div class="stats-table-horizontal">
            <div class="stats-col">
              <div class="stats-label">投诉总量</div>
              <div class="stats-value">{{ dashboardStats.total_complaints || 0 }}</div>
            </div>
            <div class="stats-col">
              <div class="stats-label">涉及企业</div>
              <div class="stats-value">{{ dashboardStats.companies_count || 0 }}</div>
            </div>
            <div class="stats-col">
              <div class="stats-label">涉及行业</div>
              <div class="stats-value">{{ dashboardStats.industries_count || 0 }}</div>
            </div>
            <div class="stats-col warning">
              <div class="stats-label">预警企业</div>
              <div class="stats-value">{{ dashboardStats.repeat_companies_count || 0 }}</div>
            </div>
          </div>
        </div>

        <!-- 4. TimeSeries Analysis -->
        <div class="panel-item timeseries-wrapper">
          <div class="control-bar-floating">
            <el-button link size="small" @click="performTimeSeriesAnalysis" :loading="analysisLoading">执行时序分析</el-button>
          </div>
          <div class="scrollable-content">
             <div v-if="!timeSeriesResults && !analysisLoading" class="empty-text">点击上方执行分析</div>
             <div v-else-if="timeSeriesResults">
               <!-- ACF -->
               <div class="chart-mini-title">ACF</div>
               <div ref="acfChart" style="width: 100%; height: 100px;"></div>
               <!-- STL -->
               <div class="chart-mini-title">STL趋势</div>
               <div ref="stlTrendChart" style="width: 100%; height: 80px;"></div>
               <div class="chart-mini-title">STL季节</div>
               <div ref="stlSeasonalChart" style="width: 100%; height: 80px;"></div>
             </div>
          </div>
        </div>
      </div>

      <!-- Column 2: Center (Trend -> Quadrant) -->
      <div class="col-center">
        <!-- Top: Trend Chart -->
        <div class="panel-item trend-wrapper">
          <div class="chart-overlay-controls">
             <el-radio-group v-model="trendPeriod" size="small" @change="loadTrendData" class="mini-radio">
                <el-radio-button value="day">天</el-radio-button>
                <el-radio-button value="week">周</el-radio-button>
                <el-radio-button value="month">月</el-radio-button>
              </el-radio-group>
          </div>
          <div class="chart-container" v-loading="trendLoading">
            <div ref="trendChart" style="width: 100%; height: 100%;"></div>
          </div>
        </div>

        <!-- Bottom: Quadrant Chart -->
        <div class="panel-item scatter-wrapper">
          <TheScatterChart
            :start-date="filters.startDate"
            :end-date="filters.endDate"
            :selected-companies="filters.selectedCompanies"
            :selected-categories="filters.selectedCategories"
            @update:selection="handleScatterSelection"
            @click-node="handleScatterNodeClick"
            ref="scatterChartRef"
          />
        </div>
      </div>

      <!-- Column 3: Limit Right (Ranking -> Detail) -->
      <div class="col-right-1">
        <!-- Top: Ranking -->
        <div class="panel-item ranking-wrapper">
          <TheCompanyRanking 
            :ranking-data="filteredCompanyRanking"
            :start-date="filters.startDate"
            :end-date="filters.endDate"
            @select-company="handleCompanySelect"
          />
        </div>

        <!-- Bottom: Detail Panel -->
        <div class="panel-item detail-wrapper">
          <TheCompanyDetail
            :company-name="selectedCompanyForDetail"
            :start-date="filters.startDate"
            :end-date="filters.endDate"
          />
        </div>
      </div>

      <!-- Column 4: Far Right (AI) -->
      <div class="col-right-2">
         <div class="panel-item ai-wrapper">
            <el-tabs v-model="activeAITab" type="border-card" class="ai-tabs-compact">
                <el-tab-pane label="AI报告" name="report">
                    <div class="ai-content-scroll">
                        <el-button size="small" type="primary" plain class="w-full mb-5" @click="handleGenerateAIReport" :loading="aiReportLoading">生成报告</el-button>
                        <div v-if="aiReport" class="ai-text" v-html="formatReportText(aiReport)"></div>
                    </div>
                </el-tab-pane>
                <el-tab-pane label="AI回复" name="reply">
                    <div class="ai-content-scroll">
                        <el-input v-model="complaintInput" type="textarea" :rows="3" placeholder="输入投诉内容" size="small" />
                        <el-button size="small" type="primary" plain class="w-full mt-5" @click="handleGenerateAIReply" :loading="aiReplyLoading">生成回复</el-button>
                        <div v-if="aiReply" class="ai-text mt-5">{{ aiReply }}</div>
                    </div>
                </el-tab-pane>
            </el-tabs>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Setting } from '@element-plus/icons-vue'
import * as d3 from 'd3'
import TheSunburstCharts from '@/components/TheSunburstCharts.vue'
import TheScatterChart from '@/components/TheScatterChart.vue'
import TheCompanyRanking from '@/components/TheCompanyRanking.vue'
import TheCompanyDetail from '@/components/TheCompanyDetail.vue'

import {
  getDashboardStats,
  getTrendData,
  analyzeTimeSeries,
  getDataSummary,
  getFilterOptions,
  generateAIReport,
  generateAIReply
} from '@/stores/complaint-store'

// 状态定义
const loading = ref(false)
const trendLoading = ref(false)
const analysisLoading = ref(false)

const filters = ref({
  startDate: null,
  endDate: null,
  selectedCompanies: [],
  selectedCategories: [],
  selectedIndustries: [], 
  selectedIndustryLevel1: [],
  selectedIndustryLevel2: [],
  selectedIndustryLevel3: [],
  selectedIssueLevel1: [],
  selectedIssueLevel2: []
})

const filterOptions = ref({
  companies: [],
  categories: [],
  industries: [],
  industry_level1: [],
  industry_level2: [],
  industry_level3: [],
  issue_level1: [],
  issue_level2: []
})

const dashboardStats = ref({
  total_complaints: 0,
  companies_count: 0,
  industries_count: 0,
  repeat_companies_count: 0,
  company_ranking: []
})

const trendPeriod = ref('day')
const trendData = ref([])
const timeSeriesResults = ref(null)

// AI
const activeAITab = ref('report')
const aiReport = ref('')
const aiReportLoading = ref(false)
const aiReply = ref('')
const aiReplyLoading = ref(false)
const complaintInput = ref('')

// Selection & Detail
const scatterSelection = ref([])
const selectedCompanyForDetail = ref('')

// Refs
const trendChart = ref(null)
const acfChart = ref(null)
const stlTrendChart = ref(null)
const stlSeasonalChart = ref(null)
const scatterChartRef = ref(null)
const sunburstChartsRef = ref(null)

// Logic
const initializeDashboard = async () => {
    loading.value = true
    try {
        const [summary, options] = await Promise.all([getDataSummary(), getFilterOptions()])
        
        if (summary.data && summary.data.date_range) {
            filters.value.startDate = summary.data.date_range.start
            filters.value.endDate = summary.data.date_range.end
        } else {
            const end = new Date(); const start = new Date(); start.setFullYear(end.getFullYear() - 1);
            filters.value.startDate = start.toISOString().split('T')[0]
            filters.value.endDate = end.toISOString().split('T')[0]
        }
        
        if (options.data) {
            filterOptions.value = options.data
        }
        
        await loadDashboardData()
        await loadTrendData()
    } catch (err) {
        console.error(err)
        ElMessage.error('初始化失败')
    } finally {
        loading.value = false
    }
}

const loadDashboardData = async () => {
    if (!filters.value.startDate) return
    loading.value = true
    try {
        const params = {
            start_date: filters.value.startDate,
            end_date: filters.value.endDate,
            companies: filters.value.selectedCompanies.length ? filters.value.selectedCompanies : undefined,
            categories: filters.value.selectedCategories.length ? filters.value.selectedCategories : undefined
        }
        const res = await getDashboardStats(params)
        if (res.data) dashboardStats.value = res.data
    } finally { loading.value = false }
}

const loadTrendData = async () => {
    trendLoading.value = true
    try {
         const params = {
            start_date: filters.value.startDate,
            end_date: filters.value.endDate,
            period: trendPeriod.value,
            companies: filters.value.selectedCompanies.length ? filters.value.selectedCompanies : undefined,
            categories: filters.value.selectedCategories.length ? filters.value.selectedCategories : undefined
        }
        const res = await getTrendData(params)
        if (res.data && res.data.data) {
            trendData.value = res.data.data
            await nextTick()
            renderTrendChart()
        }
    } finally { trendLoading.value = false }
}

const renderTrendChart = () => {
    if (!trendChart.value || !trendData.value.length) return
    const container = trendChart.value
    d3.select(container).selectAll("*").remove()
    
    const margin = {top: 10, right: 10, bottom: 20, left: 30}
    const width = container.offsetWidth - margin.left - margin.right
    const height = container.offsetHeight - margin.top - margin.bottom
    
    const svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g").attr("transform", `translate(${margin.left},${margin.top})`)
        
    const xScale = d3.scaleBand().domain(trendData.value.map(d=>d.time)).range([0, width]).padding(0.1)
    const yScale = d3.scaleLinear().domain([0, d3.max(trendData.value, d=>d.count)]).nice().range([height, 0])
    
    const area = d3.area()
        .x(d => xScale(d.time) + xScale.bandwidth()/2)
        .y0(height).y1(d => yScale(d.count)).curve(d3.curveMonotoneX)
    const line = d3.line()
        .x(d => xScale(d.time) + xScale.bandwidth()/2)
        .y(d => yScale(d.count)).curve(d3.curveMonotoneX)
        
    svg.append("path").datum(trendData.value).attr("fill", "#ecf5ff").attr("d", area)
    svg.append("path").datum(trendData.value).attr("fill", "none").attr("stroke", "#409eff").attr("stroke-width", 2).attr("d", line)
    
    // Add tooltip
    const tooltip = d3.select("body").append("div")
        .attr("class", "trend-tooltip")
        .style("opacity", 0)
        .style("position", "absolute")
        .style("background", "rgba(0,0,0,0.8)")
        .style("color", "#fff")
        .style("padding", "8px 12px")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("z-index", 9999)
    
    // Add interactive dots
    svg.selectAll(".dot")
        .data(trendData.value)
        .enter().append("circle")
        .attr("class", "dot")
        .attr("cx", d => xScale(d.time) + xScale.bandwidth()/2)
        .attr("cy", d => yScale(d.count))
        .attr("r", 4)
        .attr("fill", "#409eff")
        .style("cursor", "pointer")
        .on("mouseover", function(event, d) {
            d3.select(this).attr("r", 6)
            tooltip.transition().duration(200).style("opacity", 0.9)
            tooltip.html(`<strong>${d.time}</strong><br/>投诉数: ${d.count}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px")
        })
        .on("mouseout", function() {
            d3.select(this).attr("r", 4)
            tooltip.transition().duration(500).style("opacity", 0)
        })
    
    // Axis
    let tickValues = xScale.domain()
    if (tickValues.length > 8) {
        const interval = Math.ceil(tickValues.length / 8)
        tickValues = tickValues.filter((d, i) => i % interval === 0)
    }
    
    svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(xScale).tickValues(tickValues))
       .selectAll("text").style("font-size","9px")
    svg.append("g").call(d3.axisLeft(yScale).ticks(5))
       .selectAll("text").style("font-size","9px")
}

const performTimeSeriesAnalysis = async () => {
    analysisLoading.value = true
    try {
        const params = { start_date: filters.value.startDate, end_date: filters.value.endDate, methods: ['acf', 'stl'] }
        const res = await analyzeTimeSeries(params)
        if (res.data && res.data.analysis) {
            timeSeriesResults.value = res.data
            await nextTick()
            renderAnalysisCharts()
        }
    } finally { analysisLoading.value = false }
}

const renderAnalysisCharts = async () => {
  if (!timeSeriesResults.value || !timeSeriesResults.value.analysis) {
    return
  }
  await nextTick()
  if (acfChart.value && timeSeriesResults.value.analysis.acf && !timeSeriesResults.value.analysis.acf.error) {
     renderACFChart()
  }
  if (timeSeriesResults.value.analysis.stl && !timeSeriesResults.value.analysis.stl.error) {
     renderSTLCharts()
  }
}

const renderACFChart = () => {
  const container = acfChart.value
  if (!container) return
  const data = timeSeriesResults.value.analysis.acf.acf_values
  const conf = timeSeriesResults.value.analysis.acf.confidence_interval
  d3.select(container).selectAll("*").remove()
  const margin = {top: 5, right: 5, bottom: 15, left: 25}
  const w = container.offsetWidth - margin.left - margin.right
  const h = container.offsetHeight - margin.top - margin.bottom
  const svg = d3.select(container).append("svg").attr("width", w+margin.left+margin.right).attr("height", h+margin.top+margin.bottom)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`)
  const x = d3.scaleBand().domain(data.map(d=>d.lag)).range([0, w]).padding(0.2)
  const y = d3.scaleLinear().domain(d3.extent(data, d=>d.acf_value)).range([h, 0])
  svg.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x).tickValues(x.domain().filter((d,i)=>i%5===0))).selectAll("text").style("font-size","8px")
  svg.append("g").call(d3.axisLeft(y).ticks(3)).selectAll("text").style("font-size","8px")
  svg.selectAll("rect").data(data).enter().append("rect").attr("x", d=>x(d.lag)).attr("y", d=>y(Math.max(0, d.acf_value))).attr("width", x.bandwidth()).attr("height", d=>Math.abs(y(d.acf_value)-y(0))).attr("fill", "#409eff")
}

const renderSTLCharts = () => {
    const stl = timeSeriesResults.value.analysis.stl
    if (stlTrendChart.value && stl.trend) renderSTLComponent(stlTrendChart.value, stl.trend, "#67c23a")
    if (stlSeasonalChart.value && stl.seasonal) renderSTLComponent(stlSeasonalChart.value, stl.seasonal, "#e6a23c")
}

const renderSTLComponent = (container, data, color) => {
    d3.select(container).selectAll("*").remove()
    const margin = {top: 5, right: 5, bottom: 15, left: 25}
    const w = container.offsetWidth - margin.left - margin.right
    const h = container.offsetHeight - margin.top - margin.bottom
    const svg = d3.select(container).append("svg").attr("width", w+margin.left+margin.right).attr("height", h+margin.top+margin.bottom)
        .append("g").attr("transform", `translate(${margin.left},${margin.top})`)
    const pData = data.map((d,i)=>({date: new Date(2023,0,i), value: d.value})) // Simplified date
    const x = d3.scaleTime().domain(d3.extent(pData, d=>d.date)).range([0, w])
    const y = d3.scaleLinear().domain(d3.extent(pData, d=>d.value)).range([h, 0])
    const line = d3.line().x(d=>x(d.date)).y(d=>y(d.value))
    svg.append("path").datum(pData).attr("fill","none").attr("stroke", color).attr("stroke-width", 1.5).attr("d", line)
    svg.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x).ticks(3)).selectAll("text").style("font-size","8px")
    svg.append("g").call(d3.axisLeft(y).ticks(3)).selectAll("text").style("font-size","8px")
}

// Interactions
const handleScatterSelection = (selection) => {
    scatterSelection.value = selection
}

const handleScatterNodeClick = (node) => {
    selectedCompanyForDetail.value = node.name || node.company
}

const handleCompanySelect = (name) => {
    selectedCompanyForDetail.value = name
}

const clearFilters = () => {
    filters.value.selectedCompanies = []
    filters.value.selectedCategories = []
    filters.value.selectedIndustries = []
    filters.value.selectedIndustryLevel1 = []
    filters.value.selectedIndustryLevel2 = []
    filters.value.selectedIndustryLevel3 = []
    filters.value.selectedIssueLevel1 = []
    filters.value.selectedIssueLevel2 = []
    loadDashboardData()
}

// AI
const handleGenerateAIReport = async () => {
    aiReportLoading.value = true
    try {
        const res = await generateAIReport({start_date: filters.value.startDate, end_date: filters.value.endDate, use_ai: true})
        if (res.data && res.data.success) aiReport.value = res.data.report
    } finally { aiReportLoading.value = false }
}

const handleGenerateAIReply = async () => {
    aiReplyLoading.value = true
    try {
        const res = await generateAIReply({complaint_content: complaintInput.value})
        if (res.data && res.data.success) aiReply.value = res.data.reply
    } finally { aiReplyLoading.value = false }
}

const formatReportText = (text) => text ? text.replace(/\n/g, '<br/>') : ''

const filteredCompanyRanking = computed(() => {
    if (!dashboardStats.value.company_ranking) return []
    if (scatterSelection.value.length > 0) {
        return dashboardStats.value.company_ranking.filter(item => scatterSelection.value.includes(item.name))
    }
    return dashboardStats.value.company_ranking
})

onMounted(() => {
    initializeDashboard()
})
</script>

<style scoped>
.dashboard-container {
  height: 100vh;
  padding: 0; /* Zero padding as requested */
  background: #f8f9fa;
  overflow: hidden;
  box-sizing: border-box;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 260px 1fr 260px 220px; /* 4 Columns */
  gap: 0; /* Zero gap */
  height: 100%;
}

.col-left, .col-center, .col-right-1, .col-right-2 {
  display: flex;
  flex-direction: column;
  gap: 0; /* Zero gap between modules */
  min-height: 0; 
  height: 100%;
  border-right: 1px solid #e0e0e0; /* Visual separator */
}

.col-right-2 {
  border-right: none;
}

.panel-item {
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  position: relative;
}

/* Left Column Specifics */
.console-wrapper {
  flex-shrink: 0;
  padding: 5px;
}
.console-content-compact {
  padding: 0 5px; /* Reduced side padding */
}
.mb-3 { margin-bottom: 3px !important; }
.mb-5 { margin-bottom: 5px !important; }
.w-full { width: 100%; }
.mt-5 { margin-top: 5px; }

.sunburst-wrapper {
  flex: 1; 
  min-height: 150px; /* Reduced from 200px */
}
.stats-wrapper {
  flex-shrink: 0;
  padding: 3px 5px; /* Reduced padding */
}

/* Stats - Horizontal Table Style */
.stats-table-horizontal {
    display: flex;
    width: 100%;
    gap: 0;
}
.stats-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    text-align: center;
    border-right: 1px solid #e0e0e0;
}
.stats-col:last-child {
    border-right: none;
}
.stats-col.warning .stats-value {
    color: #e6a23c;
}
.stats-label {
    background: #f5f7fa;
    padding: 3px 2px;
    font-size: 10px;
    color: #606266;
    font-weight: 500;
    border-bottom: 1px solid #e0e0e0;
}
.stats-value {
    background: #fff;
    padding: 3px 2px;
    font-size: 14px;
    font-weight: bold;
    color: #303133;
}
.timeseries-wrapper {
  flex: 1;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.filter-actions {
  display: flex;
  gap: 4%;
  width: 100%;
}

/* Center Column Specifics */
.trend-wrapper {
  height: 40%;
}
.scatter-wrapper {
  height: 60%;
}

/* Right Columns */
.ranking-wrapper {
  height: 50%;
  display: flex;
  flex-direction: column;
}
.detail-wrapper {
  height: 50%;
  display: flex;
  flex-direction: column;
}
.ai-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Controls */
.chart-overlay-controls {
  position: absolute;
  top: 5px;
  right: 5px;
  z-index: 10;
}
.control-bar-floating {
  position: absolute;
  top: 5px;
  right: 5px;
  z-index: 10;
}

/* Charts */
.chart-container {
  width: 100%;
  height: 100%;
}
.scrollable-content {
    flex: 1;
    overflow-y: auto;
    padding: 5px;
}
.chart-mini-title { font-size: 10px; color: #999; margin: 2px 0 0 5px; }
.empty-text { font-size: 12px; color: #ccc; text-align: center; margin-top: 20px; }

/* AI Tabs Styles */
.ai-tabs-compact {
    height: 100%;
    border: none;
    box-shadow: none;
}
.ai-tabs-compact :deep(.el-tabs__header) {
    margin-bottom: 0;
}
.ai-tabs-compact :deep(.el-tabs__content) {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
}
</style>