<template>
  <div class="dashboard-container">
    <!-- 4-Column Grid Layout: Zero Gap -->
    <div class="dashboard-grid">
      
      <!-- Column 1: Left (Console -> Sunburst -> Stats -> TimeSeries) -->
      <div class="col-left">
        <!-- 1. Console (Compact with More Filters) -->
        <div class="panel-item console-wrapper">
          <div class="console-content-compact">
            <el-form :model="filters" size="small" class="compact-form no-labels">
              <!-- 日期范围 -->
              <el-row :gutter="4">
                <el-col :span="12">
                  <el-form-item class="mb-3">
                    <el-date-picker v-model="filters.startDate" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 100%" :clearable="false" size="small" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item class="mb-3">
                    <el-date-picker v-model="filters.endDate" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 100%" :clearable="false" size="small" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <!-- 企业筛选 -->
              <el-form-item class="mb-3">
                <el-select v-model="filters.selectedCompanies" multiple collapse-tags collapse-tags-tooltip filterable placeholder="企业" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.companies" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              <!-- 行业筛选（两列布局） -->
              <div style="display: flex; gap: 8px;" class="mb-3">
                <el-form-item style="flex: 1; margin-bottom: 0;">
                  <el-select v-model="filters.selectedIndustries" multiple collapse-tags collapse-tags-tooltip filterable placeholder="行业分类" style="width: 100%" size="small">
                    <el-option v-for="c in filterOptions.industry_classification" :key="c" :label="c" :value="c" />
                  </el-select>
                </el-form-item>
                
                <el-form-item style="flex: 1; margin-bottom: 0;">
                  <el-select v-model="filters.selectedIndustryLevel1" multiple collapse-tags collapse-tags-tooltip filterable placeholder="行业名称(1)" style="width: 100%" size="small">
                    <el-option v-for="c in filterOptions.industry_level1" :key="c" :label="c" :value="c" />
                  </el-select>
                </el-form-item>
              </div>
              
              <div style="display: flex; gap: 8px;" class="mb-3">
                <el-form-item style="flex: 1; margin-bottom: 0;">
                  <el-select v-model="filters.selectedIndustryLevel2" multiple collapse-tags collapse-tags-tooltip filterable placeholder="行业名称(2)" style="width: 100%" size="small">
                    <el-option v-for="c in filterOptions.industry_level2" :key="c" :label="c" :value="c" />
                  </el-select>
                </el-form-item>
                
                <el-form-item style="flex: 1; margin-bottom: 0;">
                  <el-select v-model="filters.selectedIndustryLevel3" multiple collapse-tags collapse-tags-tooltip filterable placeholder="行业名称(3)" style="width: 100%" size="small">
                    <el-option v-for="c in filterOptions.industry_level3" :key="c" :label="c" :value="c" />
                  </el-select>
                </el-form-item>
              </div>
              
              
              <!-- 问题筛选 -->
              <el-form-item class="mb-3">
                <el-select v-model="filters.selectedCategories" multiple collapse-tags collapse-tags-tooltip filterable placeholder="问题分类" style="width: 100%" size="small">
                  <el-option v-for="c in filterOptions.categories" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
              
              
              <!-- 涉及问题筛选（两列布局） -->
              <div style="display: flex; gap: 8px;" class="mb-3">
                <el-form-item style="flex: 1; margin-bottom: 0;">
                  <el-select v-model="filters.selectedIssueLevel1" multiple collapse-tags collapse-tags-tooltip filterable placeholder="涉及问题(1)" style="width: 100%" size="small">
                    <el-option v-for="c in filterOptions.issue_level1" :key="c" :label="c" :value="c" />
                  </el-select>
                </el-form-item>
                
                <el-form-item style="flex: 1; margin-bottom: 0;">
                  <el-select v-model="filters.selectedIssueLevel2" multiple collapse-tags collapse-tags-tooltip filterable placeholder="涉及问题(2)" style="width: 100%" size="small">
                    <el-option v-for="c in filterOptions.issue_level2" :key="c" :label="c" :value="c" />
                  </el-select>
                </el-form-item>
              </div>

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

      <!-- Column 4: Far Right (Agent + AI Reply) -->
      <div class="col-right-2">
         <div class="panel-item ai-wrapper">
            <el-tabs v-model="activeAITab" type="border-card" class="ai-tabs-compact">
                <el-tab-pane label="Agent" name="agent">
                    <TheAgentChat 
                      :embedded="true" 
                      :context="agentContext"
                      @action="handleAgentAction" 
                    />
                </el-tab-pane>
                <el-tab-pane label="AI回复" name="reply">
                    <div class="reply-module">
                      <!-- Input card -->
                      <div class="reply-input-card">
                        <div class="reply-input-label">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" class="label-icon"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                          投诉原文
                        </div>
                        <textarea
                          v-model="complaintInput"
                          class="reply-textarea"
                          placeholder="粘贴投诉原文，AI将为您起草官方回复…"
                          rows="4"
                          :disabled="aiReplyLoading"
                        ></textarea>
                        <div class="reply-input-footer">
                          <span class="char-count">{{ complaintInput.length }} 字</span>
                          <button class="reply-generate-btn" @click="handleGenerateAIReply" :disabled="!complaintInput.trim() || aiReplyLoading">
                            <span v-if="aiReplyLoading" class="btn-spinner"></span>
                            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M13 10V3L4 14h7v7l9-11h-7z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            {{ aiReplyLoading ? '生成中…' : '生成回复' }}
                          </button>
                        </div>
                      </div>

                      <!-- Result card -->
                      <transition name="reply-fade">
                        <div v-if="aiReply" class="reply-result-card">
                          <div class="reply-result-header">
                            <div class="result-badge">
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" stroke-linecap="round"/></svg>
                              AI 回复建议
                            </div>
                            <button class="copy-btn" @click="copyReply" :class="{copied: replyJustCopied}">
                              <svg v-if="!replyJustCopied" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="9" y="9" width="13" height="13" rx="2" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke-width="2"/></svg>
                              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20 6L9 17l-5-5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                              {{ replyJustCopied ? '已复制' : '复制' }}
                            </button>
                          </div>
                          <div class="reply-result-body">{{ aiReply }}</div>
                        </div>
                      </transition>
                    </div>
                </el-tab-pane>
            </el-tabs>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Setting } from '@element-plus/icons-vue'
import * as d3 from 'd3'
import TheSunburstCharts from '@/components/TheSunburstCharts.vue'
import TheScatterChart from '@/components/TheScatterChart.vue'
import TheCompanyRanking from '@/components/TheCompanyRanking.vue'
import TheCompanyDetail from '@/components/TheCompanyDetail.vue'
import TheAgentChat from '@/components/TheAgentChat.vue'

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
  industry_classification: [],
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
const activeAITab = ref('agent')  // 默认显示Agent标签
const aiReport = ref('')
const aiReportLoading = ref(false)
const aiReply = ref('')
const aiReplyLoading = ref(false)
const complaintInput = ref('')
const replyJustCopied = ref(false)

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
    
    // 清理旧的DOM元素，防止内存泄漏
    d3.select(container).selectAll("*").remove()
    d3.selectAll(".trend-tooltip").remove()
    
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

const copyReply = async () => {
  if (!aiReply.value) return
  try {
    await navigator.clipboard.writeText(aiReply.value)
    replyJustCopied.value = true
    setTimeout(() => { replyJustCopied.value = false }, 2000)
  } catch {
    ElMessage.warning('复制失败，请手动选择文本')
  }
}

const formatReportText = (text) => text ? text.replace(/\n/g, '<br/>') : ''

// 趋势数据智能压缩：≤20个点全传；>20个点改传按周和按月聚合的统计
function computeTrendSummary(rawData) {
  if (!rawData || rawData.length === 0) return { mode: 'empty', data: [] }
  if (rawData.length <= 20) {
    return { mode: 'daily', data: rawData.map(d => ({ time: d.time, count: d.count })) }
  }
  // 按周聚合
  const weeklyMap = {}
  rawData.forEach(d => {
    const date = new Date(d.time)
    if (isNaN(date)) return
    const year = date.getFullYear()
    const startOfYear = new Date(year, 0, 1)
    const week = Math.ceil(((date - startOfYear) / 86400000 + startOfYear.getDay() + 1) / 7)
    const key = `${year}-W${String(week).padStart(2, '0')}`
    weeklyMap[key] = (weeklyMap[key] || 0) + (d.count || 0)
  })
  // 按月聚合
  const monthlyMap = {}
  rawData.forEach(d => {
    const date = new Date(d.time)
    if (isNaN(date)) return
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    monthlyMap[key] = (monthlyMap[key] || 0) + (d.count || 0)
  })
  return {
    mode: 'aggregated',
    weekly: Object.entries(weeklyMap).sort().map(([time, count]) => ({ time, count })),
    monthly: Object.entries(monthlyMap).sort().map(([time, count]) => ({ time, count }))
  }
}

// Agent Context - 动态提供给Agent的上下文
const agentContext = computed(() => ({
  filters: {
    startDate: filters.value.startDate,
    endDate: filters.value.endDate,
    selectedCompanies: filters.value.selectedCompanies,
    selectedCategories: filters.value.selectedCategories,
    selectedIndustries: filters.value.selectedIndustries
  },
  currentStats: {
    total_complaints: dashboardStats.value.total_complaints || 0,
    companies_count: dashboardStats.value.companies_count || 0,
    industries_count: dashboardStats.value.industries_count || 0,
    repeat_companies_count: dashboardStats.value.repeat_companies_count || 0,
    company_ranking: dashboardStats.value.company_ranking?.slice(0, 10) || []
  },
  selectedCompany: selectedCompanyForDetail.value,
  // 趋势图数据（智能压缩：≤20点全传，>20点传周/月聚合）
  trendData: computeTrendSummary(trendData.value),
  trendPeriod: trendPeriod.value,
  // 旭日图摘要：top-3 问题分类和涉及问题
  sunburstSummary: sunburstChartsRef.value?.getSummary?.() ?? null,
  // 散点图摘要：top-10 企业（含投诉量、问题多样性、预警状态）
  scatterSummary: scatterChartRef.value?.getSummary?.() ?? null,
}))

// Agent动作处理函数
const handleAgentAction = async (action) => {
  console.log('Handling agent action:', action)
  
  try {
    switch (action.type) {
      case 'update_stats':
        await loadDashboardData()
        ElMessage.success('已更新统计数据')
        break
      
      case 'update_trend':
        if (action.parameters?.period) {
          trendPeriod.value = action.parameters.period
        }
        await loadTrendData()
        ElMessage.success('已更新趋势图')
        break
      
      case 'show_company':
        if (action.parameters?.company_name) {
          selectedCompanyForDetail.value = action.parameters.company_name
          ElMessage.success(`已切换到${action.parameters.company_name}的详情`)
        }
        break
      
      case 'switch_chart_sunburst':
        ElMessage.success('旭日图已在左侧显示')
        break
      
      case 'switch_chart_quadrant':
        ElMessage.success('散点图已在中间显示')
        break
      
      case 'show_report':
        if (action.data && action.data.report) {
          aiReport.value = action.data.report
          ElMessage.success('报告已生成并在下方显示')
        } else {
          ElMessage.warning('报告生成成功，但未返回内容')
        }
        break
      
      case 'show_reply':
        if (action.data && action.data.reply) {
          aiReply.value = action.data.reply
          if (action.data.complaint_content) complaintInput.value = action.data.complaint_content
          activeAITab.value = 'reply'
          ElMessage.success('回复建议已生成')
        }
        break

      case 'show_rag':
        ElMessage.success('法律咨询结果已获取')
        break
      
      case 'filter_data':
        if (action.parameters) {
          if (action.parameters.start_date) filters.value.startDate = action.parameters.start_date
          if (action.parameters.end_date) filters.value.endDate = action.parameters.end_date
          if (action.parameters.companies) filters.value.selectedCompanies = action.parameters.companies
          if (action.parameters.industries) filters.value.selectedIndustries = action.parameters.industries
          if (action.parameters.categories) filters.value.selectedCategories = action.parameters.categories
          
          await loadDashboardData()
          ElMessage.success('已应用筛选条件')
        }
        break
      
      default:
        console.warn('Unknown action type:', action.type)
    }
  } catch (error) {
    console.error('Error handling agent action:', error)
    ElMessage.error('执行动作时出错')
  }
}

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

// 方案B：监听日期变化，自动刷新其他图表
watch(
  [() => filters.value.startDate, () => filters.value.endDate],
  async ([newStart, newEnd], [oldStart, oldEnd]) => {
    if (!newStart || !newEnd) return
    if (newStart === oldStart && newEnd === oldEnd) return
    // 刷新仪表板统计、趋势图（及子组件通过prop响应）
    await loadDashboardData()
    await loadTrendData()
    // 旭日图和散点图通过 :start-date/:end-date prop 自动响应
  }
)

// 方案A：监听日期变化，仅在已执行过时序分析时自动刷新
watch(
  [() => filters.value.startDate, () => filters.value.endDate],
  ([newStart, newEnd], [oldStart, oldEnd]) => {
    if (!newStart || !newEnd) return
    if (newStart === oldStart && newEnd === oldEnd) return
    if (timeSeriesResults.value) {
      performTimeSeriesAnalysis()
    }
  }
)
</script>

<style scoped>
/* 全局样式：确保页面铺满整个视口 */
:global(html, body, #app) {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.dashboard-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  padding: 0;
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
  gap: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden; /* 防止子元素溢出导致整体页面滚动 */
  border-right: 1px solid #e0e0e0;
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
  max-height: 350px; /* 添加最大高度，保证自适应的同时不会过高 */
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 防止外层溢出 */
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
  overflow: hidden;
  padding: 0;
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
    overflow-x: hidden;
    padding: 5px;
    min-height: 0;
}
.chart-mini-title { font-size: 10px; color: #999; margin: 2px 0 0 5px; }
.empty-text { font-size: 12px; color: #ccc; text-align: center; margin-top: 20px; }

/* AI Tabs Styles */
.ai-tabs-compact {
    height: 100%;
    border: none;
    box-shadow: none;
    display: flex;
    flex-direction: column;
}
.ai-tabs-compact :deep(.el-tabs__header) {
    margin-bottom: 0;
    flex-shrink: 0;
}
.ai-tabs-compact :deep(.el-tabs__content) {
    flex: 1;
    overflow: hidden;
    padding: 0;
    display: flex;
    flex-direction: column;
}
.ai-tabs-compact :deep(.el-tab-pane) {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
/* ───────── AI Reply Module ───────── */
.reply-module {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  overflow-y: auto;
  background: #f8f9ff;
}

.reply-input-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e8e4f8;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.07);
}

.reply-input-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: #6366f1;
  letter-spacing: 0.3px;
}

.label-icon {
  width: 13px;
  height: 13px;
}

.reply-textarea {
  width: 100%;
  resize: none;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.6;
  padding: 8px 10px;
  color: #1f2937;
  background: #fafbff;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.reply-textarea:focus {
  outline: none;
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
  background: white;
}

.reply-textarea:disabled {
  background: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.reply-textarea::placeholder { color: #c4c9d4; }

.reply-input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.char-count {
  font-size: 10px;
  color: #9ca3af;
}

.reply-generate-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.reply-generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45);
}

.reply-generate-btn:disabled {
  background: #d1d5db;
  box-shadow: none;
  cursor: not-allowed;
}

.reply-generate-btn svg {
  width: 13px;
  height: 13px;
}

.btn-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Result card */
.reply-result-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #d1fae5;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(5, 150, 105, 0.08);
}

.reply-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  border-bottom: 1px solid #a7f3d0;
}

.result-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: #065f46;
}

.result-badge svg {
  width: 13px;
  height: 13px;
  color: #10b981;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 500;
  color: #065f46;
  background: rgba(5, 150, 105, 0.1);
  border: 1px solid #6ee7b7;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: #10b981;
  color: white;
  border-color: #10b981;
}

.copy-btn.copied {
  background: #10b981;
  color: white;
  border-color: #10b981;
}

.copy-btn svg {
  width: 11px;
  height: 11px;
}

.reply-result-body {
  padding: 12px;
  font-size: 12px;
  line-height: 1.7;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Transition */
.reply-fade-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.reply-fade-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.97);
}

/* Keep old ai-content-scroll for other potential uses */
.ai-content-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
}
</style>