<template>
  <div class="sunburst-container">
    <div class="sunburst-charts-wrapper">
      <!-- 问题分类旭日图 -->
      <div class="sunburst-chart-item">
        <div ref="categorySunburstChart" class="sunburst-chart"></div>
        <div class="chart-label">问题分类</div>
      </div>

      <!-- 涉及问题旭日图 -->
      <div class="sunburst-chart-item">
        <div ref="issueSunburstChart" class="sunburst-chart"></div>
        <div class="chart-label">涉及问题</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { getSunburstData } from '@/stores/complaint-store'
import * as d3 from 'd3'

// Props定义
const props = defineProps({
  startDate: {
    type: String,
    default: null
  },
  endDate: {
    type: String,
    default: null
  },
  selectedCompanies: {
    type: Array,
    default: () => []
  },
  selectedIndustries: {
    type: Array,
    default: () => []
  },
  selectedCategories: {
    type: Array,
    default: () => []
  },
  selectedIndustryLevel1: {
    type: Array,
    default: () => []
  },
  selectedIndustryLevel2: {
    type: Array,
    default: () => []
  }
})

// 响应式数据
const categorySunburstData = ref(null)
const issueSunburstData = ref(null)

// Chart引用
const categorySunburstChart = ref(null)
const issueSunburstChart = ref(null)

// 更新旭日图（根据当前筛选条件）
const updateSunburstCharts = async () => {
  if (!props.startDate || !props.endDate) {
    return
  }

  try {
    // 并行获取两个图表的数据
    const [categoryResponse, issueResponse] = await Promise.all([
      getSunburstData({
        start_date: props.startDate,
        end_date: props.endDate,
        chart_type: 'category',
        companies: props.selectedCompanies.length > 0 ? props.selectedCompanies : undefined,
        industries: props.selectedIndustries.length > 0 ? props.selectedIndustries : undefined,
        categories: props.selectedCategories.length > 0 ? props.selectedCategories : undefined,
        industry_level1: props.selectedIndustryLevel1.length > 0 ? props.selectedIndustryLevel1 : undefined,
        industry_level2: props.selectedIndustryLevel2.length > 0 ? props.selectedIndustryLevel2 : undefined
      }).catch(err => {
        console.error('获取问题分类数据失败:', err)
        return { data: { error: '获取问题分类数据失败' } }
      }),
      getSunburstData({
        start_date: props.startDate,
        end_date: props.endDate,
        chart_type: 'issue',
        companies: props.selectedCompanies.length > 0 ? props.selectedCompanies : undefined,
        industries: props.selectedIndustries.length > 0 ? props.selectedIndustries : undefined,
        categories: props.selectedCategories.length > 0 ? props.selectedCategories : undefined,
        industry_level1: props.selectedIndustryLevel1.length > 0 ? props.selectedIndustryLevel1 : undefined,
        industry_level2: props.selectedIndustryLevel2.length > 0 ? props.selectedIndustryLevel2 : undefined
      }).catch(err => {
        console.error('获取涉及问题数据失败:', err)
        return { data: { error: '获取涉及问题数据失败' } }
      })
    ])

    // 更新数据
    if (categoryResponse.data && !categoryResponse.data.error) {
      categorySunburstData.value = categoryResponse.data
      await nextTick()
      renderCategorySunburstChart()
    }

    if (issueResponse.data && !issueResponse.data.error) {
      issueSunburstData.value = issueResponse.data
      await nextTick()
      renderIssueSunburstChart()
    }

  } catch (error) {
    console.error('更新旭日图失败:', error)
  }
}

// 渲染问题分类小型旭日图
const renderCategorySunburstChart = () => {
  if (!categorySunburstChart.value || !categorySunburstData.value) {
    console.warn('问题分类旭日图容器或数据不存在')
    return
  }

  const container = categorySunburstChart.value
  const data = categorySunburstData.value

  // 检查容器尺寸
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn('问题分类旭日图容器尺寸为0，延迟渲染')
    setTimeout(() => renderCategorySunburstChart(), 200)
    return
  }

  // 清除之前的图表
  d3.select(container).selectAll("*").remove()

  const width = container.offsetWidth
  const height = container.offsetHeight
  const radius = Math.min(width, height) / 2 - 5

  const svg = d3.select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${width / 2}, ${height / 2})`)

  // 创建分层数据
  const root = d3.hierarchy(data)
    .sum(d => d.value || 1)
    .sort((a, b) => b.value - a.value)

  // 创建旭日图布局
  const partition = d3.partition()
    .size([2 * Math.PI, radius])

  partition(root)

  // 创建颜色比例尺
  const color = d3.scaleOrdinal(d3.schemeCategory10)

  // 创建弧生成器
  const arc = d3.arc()
    .startAngle(d => d.x0)
    .endAngle(d => d.x1)
    .innerRadius(d => d.y0)
    .outerRadius(d => d.y1)

  // 绘制弧
  const path = svg.selectAll("path")
    .data(root.descendants().filter(d => d.depth > 0))
    .enter()
    .append("path")
    .attr("d", arc)
    .style("fill", d => color(d.data.name))
    .style("stroke", "#fff")
    .style("stroke-width", "1px")
    .on("mouseover", function(event, d) {
      // 高亮当前节点
      d3.select(this).style("stroke", "#000").style("stroke-width", "2px")

      // 显示提示框
      const tooltip = d3.select("body").append("div")
        .attr("class", "d3-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0, 0, 0, 0.8)")
        .style("color", "white")
        .style("padding", "6px")
        .style("border-radius", "4px")
        .style("font-size", "11px")
        .style("pointer-events", "none")
        .style("opacity", 0)

      tooltip.transition().duration(200).style("opacity", 1)
      tooltip.html(`${d.data.name}<br/>数量: ${d.value}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px")
    })
    .on("mouseout", function() {
      d3.select(this).style("stroke", "#fff").style("stroke-width", "1px")
      d3.selectAll(".d3-tooltip").remove()
    })
}

// 渲染涉及问题小型旭日图
const renderIssueSunburstChart = () => {
  if (!issueSunburstChart.value || !issueSunburstData.value) {
    console.warn('涉及问题旭日图容器或数据不存在')
    return
  }

  const container = issueSunburstChart.value
  const data = issueSunburstData.value

  // 检查容器尺寸
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn('涉及问题旭日图容器尺寸为0，延迟渲染')
    setTimeout(() => renderIssueSunburstChart(), 200)
    return
  }

  // 清除之前的图表
  d3.select(container).selectAll("*").remove()

  const width = container.offsetWidth
  const height = container.offsetHeight
  const radius = Math.min(width, height) / 2 - 5

  const svg = d3.select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${width / 2}, ${height / 2})`)

  // 创建分层数据
  const root = d3.hierarchy(data)
    .sum(d => d.value || 1)
    .sort((a, b) => b.value - a.value)

  // 创建旭日图布局
  const partition = d3.partition()
    .size([2 * Math.PI, radius])

  partition(root)

  // 创建颜色比例尺
  const color = d3.scaleOrdinal(d3.schemeSet3)

  // 创建弧生成器
  const arc = d3.arc()
    .startAngle(d => d.x0)
    .endAngle(d => d.x1)
    .innerRadius(d => d.y0)
    .outerRadius(d => d.y1)

  // 绘制弧
  const path = svg.selectAll("path")
    .data(root.descendants().filter(d => d.depth > 0))
    .enter()
    .append("path")
    .attr("d", arc)
    .style("fill", d => color(d.data.name))
    .style("stroke", "#fff")
    .style("stroke-width", "1px")
    .on("mouseover", function(event, d) {
      // 高亮当前节点
      d3.select(this).style("stroke", "#000").style("stroke-width", "2px")

      // 显示提示框
      const tooltip = d3.select("body").append("div")
        .attr("class", "d3-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0, 0, 0, 0.8)")
        .style("color", "white")
        .style("padding", "6px")
        .style("border-radius", "4px")
        .style("font-size", "11px")
        .style("pointer-events", "none")
        .style("opacity", 0)

      tooltip.transition().duration(200).style("opacity", 1)
      tooltip.html(`${d.data.name}<br/>数量: ${d.value}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px")
    })
    .on("mouseout", function() {
      d3.select(this).style("stroke", "#fff").style("stroke-width", "1px")
      d3.selectAll(".d3-tooltip").remove()
    })
}

// 监听props变化，自动更新图表
watch([
  () => props.startDate,
  () => props.endDate,
  () => props.selectedCompanies,
  () => props.selectedIndustries,
  () => props.selectedCategories,
  () => props.selectedIndustryLevel1,
  () => props.selectedIndustryLevel2
], () => {
  updateSunburstCharts()
}, { deep: true })

// 从旭日图树形数据中提取 top-N 分类（仅取 depth=1 的子项）
function extractTopCategories(treeData, topN = 3) {
  if (!treeData || !treeData.children) return []
  const total = treeData.children.reduce((s, c) => s + (c.value || 0), 0)
  return treeData.children
    .slice()
    .sort((a, b) => (b.value || 0) - (a.value || 0))
    .slice(0, topN)
    .map(c => ({
      name: c.name,
      count: c.value || 0,
      percent: total > 0 ? +((c.value / total) * 100).toFixed(1) : 0
    }))
}

// 暴露更新方法和数据摘要给父组件调用
defineExpose({
  updateSunburstCharts,
  getSummary() {
    return {
      category_top3: extractTopCategories(categorySunburstData.value, 3),
      issue_top3: extractTopCategories(issueSunburstData.value, 3)
    }
  }
})

// 组件挂载时初始化
onMounted(() => {
  updateSunburstCharts()
})
</script>

<style scoped>
/* 旭日图容器样式 - 紧凑扁平 */
.sunburst-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 5px;
  background: transparent;
}

/* 旭日图样式 - 无边框 */
.sunburst-charts-wrapper {
  flex: 1;
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.sunburst-chart-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.sunburst-chart {
  flex: 1;
  min-height: 100px;
  width: 100%;
  background: transparent;
}

.chart-label {
  text-align: center;
  padding: 4px 2px 0 2px;
  font-size: 11px;
  font-weight: 500;
  color: #606266;
  background: transparent;
}

/* 响应式调整 */
@media (max-width: 1600px) {
  .sunburst-charts-wrapper {
    gap: 6px;
  }

  .chart-label {
    font-size: 10px;
    padding: 3px 2px 0 2px;
  }

  .sunburst-chart {
    min-height: 80px;
  }
}

@media (max-width: 1200px) {
  .sunburst-charts-wrapper {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
