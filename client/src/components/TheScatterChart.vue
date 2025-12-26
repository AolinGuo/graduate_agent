<template>
  <div class="scatter-chart-container" v-loading="loading">
    <div class="chart-controls">
      <el-popover
        placement="right-start"
        title="图表设置"
        :width="250"
        trigger="click"
      >
        <template #reference>
          <el-button size="small" circle :icon="Setting" class="settings-btn" />
        </template>
        
        <div class="settings-content">
          <div class="setting-item">
            <span class="label">点大小:</span>
            <el-slider v-model="dotSize" :min="1" :max="10" size="small" />
          </div>
          <div class="setting-item">
            <span class="label">投诉数量阈值:</span>
            <el-input-number v-model="countThreshold" :min="0" :max="1000" size="small" style="width: 100%" />
            <p class="info-text">小于等于此值的点不显示</p>
          </div>
        </div>
      </el-popover>
    </div>

    <div ref="chartRef" class="chart-wrapper"></div>
    
    <div v-if="!loading && (!data || data.length === 0)" class="empty-state">
      <el-empty description="暂无数据" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import { getQuadrantData } from '@/stores/complaint-store'
import { ElMessage } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'

const props = defineProps({
  startDate: String,
  endDate: String,
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

const emit = defineEmits(['update:selection', 'click-node'])

const chartRef = ref(null)
const loading = ref(false)
const data = ref([])
const resizeObserver = ref(null)

// 视觉设置
const dotSize = ref(3)
const countThreshold = ref(0) // 投诉数量阈值

// 加载数据
const loadData = async () => {
  if (!props.startDate || !props.endDate) return
  
  loading.value = true
  try {
    const params = {
      start_date: props.startDate,
      end_date: props.endDate,
      companies: props.selectedCompanies.length > 0 ? props.selectedCompanies : undefined,
      industries: props.selectedIndustries.length > 0 ? props.selectedIndustries : undefined,
      categories: props.selectedCategories.length > 0 ? props.selectedCategories : undefined,
      industry_level1: props.selectedIndustryLevel1.length > 0 ? props.selectedIndustryLevel1 : undefined,
      industry_level2: props.selectedIndustryLevel2.length > 0 ? props.selectedIndustryLevel2 : undefined
    }
    
    const response = await getQuadrantData(params)
    
    if (response.data && response.data.data) {
      data.value = response.data.data
      await nextTick()
      renderChart()
    } else if (response.data && response.data.nodes) {
       // 兼容旧API格式
       data.value = response.data.nodes
       await nextTick()
       renderChart()
    } else {
      data.value = []
    }
  } catch (error) {
    console.error('加载散点图数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 渲染图表
let retryCount = 0
const MAX_RETRY = 5

const renderChart = () => {
  if (!chartRef.value) {
    console.warn('散点图容器不存在')
    return
  }
  
  if (!data.value || data.value.length === 0) {
    console.warn('散点图数据为空')
    return
  }
  
  const container = chartRef.value
  
  // 检查容器尺寸，限制重试次数防止死循环
  if (container.clientWidth === 0 || container.clientHeight === 0) {
    if (retryCount < MAX_RETRY) {
      retryCount++
      console.warn(`散点图容器尺寸为0，延迟渲染 (重试 ${retryCount}/${MAX_RETRY})`)
      setTimeout(() => renderChart(), 200)
      return
    } else {
      console.error('散点图容器尺寸始终为0，放弃渲染')
      retryCount = 0 // 重置重试计数器
      return
    }
  }
  
  // 成功开始渲染，重置重试计数器
  retryCount = 0
  
  d3.select(container).selectAll("*").remove()
  
  const width = container.clientWidth
  const height = container.clientHeight
  const margin = { top: 20, right: 30, bottom: 40, left: 60 } // 增加左边距以容纳更长的Y轴标签
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom
  
  // 数据验证：过滤掉无效数据和低于阈值的数据
  const validData = data.value.filter(d => {
    const hasValidCount = d.count != null && !isNaN(d.count) && d.count >= 0
    const hasValidDiversity = d.diversity != null && !isNaN(d.diversity) && d.diversity >= 0
    const aboveThreshold = d.count > countThreshold.value // 投诉数量大于阈值
    return hasValidCount && hasValidDiversity && aboveThreshold
  })
  
  if (validData.length === 0) {
    console.warn('散点图没有有效数据（可能被阈值过滤）')
    return
  }
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 数据处理
  // X轴使用Log2 (加1避免log(0))
  const xDomain = [0, d3.max(validData, d => Math.log2(d.count + 1)) * 1.1 || 10]
  const yDomain = [0, d3.max(validData, d => d.diversity) * 1.1 || 5]
  
  const xScale = d3.scaleLinear()
    .domain(xDomain)
    .range([0, innerWidth])
    .nice()
  
  const yScale = d3.scaleLinear()
    .domain(yDomain)
    .range([innerHeight, 0])
    .nice()

  // 颜色定义：蓝色=正常企业，红色=预警企业（频繁投诉）
  const normalColor = "#409eff"  // 蓝色 - 正常企业
  const warningColor = "#f56c6c" // 红色 - 预警企业（min_interval < 30天）
  const selectedColor = "#e6a23c" // 黄色 - 框选后的颜色
  
  // 绘制轴
  svg.append("g")
    .attr("transform", `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale).ticks(5))
    .append("text")
    .attr("x", innerWidth)
    .attr("y", -6)
    .attr("fill", "#666")
    .attr("text-anchor", "end")
    .text("log2(投诉总数)")
    
  svg.append("g")
    .call(d3.axisLeft(yScale).ticks(Math.min(10, d3.max(yDomain))).tickFormat(d3.format("d")))
    .append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 6)
    .attr("dy", "0.71em")
    .attr("fill", "#666")
    .attr("text-anchor", "end")
    .text("涉及问题(2)类型个数")
    
  // Force Simulation
  // 初始化节点位置
  validData.forEach(d => {
    d.x = xScale(Math.log2(d.count + 1))
    d.y = yScale(d.diversity)
  })

  const simulation = d3.forceSimulation(validData)
    .force("x", d3.forceX(d => xScale(Math.log2(d.count + 1))).strength(1)) // 强力拉向X轴目标
    .force("y", d3.forceY(d => yScale(d.diversity)).strength(1)) // 强力拉向Y轴目标
    .force("collide", d3.forceCollide(dotSize.value + 1)) // 避免重叠
    .stop()

  // 预计算迭代
  for (let i = 0; i < 120; ++i) simulation.tick()

  // 绘制点
  const circles = svg.selectAll(".dot")
    .data(validData)
    .enter().append("circle")
    .attr("class", "dot")
    .attr("cx", d => d.x) // 使用模拟后的位置
    .attr("cy", d => d.y)
    .attr("r", dotSize.value)
    .attr("fill", d => {
        // 红色 = 预警企业（频繁投诉），蓝色 = 正常企业
        if (d.min_interval < 30) return warningColor
        return normalColor
    })
    .attr("opacity", 0.7)
    .attr("stroke", "#fff")
    .attr("stroke-width", 1)
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      event.stopPropagation()
      emit('click-node', d)
    })
    
  // 添加交互 Tooltip
  const tooltip = d3.select("body").append("div")
    .attr("class", "scatter-tooltip")
    .style("opacity", 0)
    .style("position", "absolute")
    .style("background", "rgba(0,0,0,0.8)")
    .style("color", "#fff")
    .style("padding", "8px")
    .style("border-radius", "4px")
    .style("font-size", "12px")
    .style("pointer-events", "none")
    .style("z-index", 9999)
    
  circles
    .on("mouseover", function(event, d) {
      d3.select(this).attr("r", dotSize.value + 2).attr("opacity", 1)
      tooltip.transition().duration(200).style("opacity", 0.9)
      tooltip.html(`
        <strong>${d.name}</strong><br/>
        log2(投诉总数): ${Math.log2(d.count + 1).toFixed(2)} (${d.count})<br/>
        涉及问题(2)类型个数: ${d.diversity}<br/>
        主要问题: ${d.category || '未知'}
      `)
      .style("left", (event.pageX + 10) + "px")
      .style("top", (event.pageY - 28) + "px")
    })
    .on("mousemove", function(event) {
      tooltip
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px")
    })
    .on("mouseout", function() {
      d3.select(this).attr("r", dotSize.value).attr("opacity", 0.7)
      tooltip.transition().duration(500).style("opacity", 0)
    })
    
  // 框选功能
  const brush = d3.brush()
    .extent([[0, 0], [innerWidth, innerHeight]])
    .on("end", brushed)
    
  svg.append("g")
    .attr("class", "brush")
    .call(brush)
    
  function brushed(event) {
    if (!event.selection) {
      emit('update:selection', [])
      circles.attr("fill", d => {
          // 恢复原始颜色：红色=预警，蓝色=正常
          if (d.min_interval < 30) return warningColor
          return normalColor
      })
      return
    }
    
    const [[x0, y0], [x1, y1]] = event.selection
    const selected = []
    
    circles.attr("fill", d => {
      const cx = d.x // Use simulated coordinates
      const cy = d.y
      // 判断点是否在矩形内
      const isSelected = x0 <= cx && cx <= x1 && y0 <= cy && cy <= y1
      
      if (isSelected) {
        selected.push(d.name)
        return selectedColor // 选中后变黄色
      } else {
        // 未选中时：红色=预警，蓝色=正常
        if (d.min_interval < 30) return warningColor
        return normalColor
      }
    })
    
    emit('update:selection', selected)
  }

  // 添加图例
  const legend = svg.append("g")
    .attr("transform", `translate(${innerWidth - 100}, 10)`)
    
  // 图例项：蓝色=正常企业，红色=预警企业
  const legendItems = [
    { label: '正常企业', color: normalColor },
    { label: '预警企业', color: warningColor }
  ]
  
  legendItems.forEach((item, i) => {
    const lg = legend.append("g").attr("transform", `translate(0, ${i * 18})`)
    lg.append("circle").attr("r", 5).attr("fill", item.color).attr("opacity", 0.7)
    lg.append("text").attr("x", 12).attr("y", 4).text(item.label).style("font-size", "11px").attr("fill", "#666")
  })
}

// 暴露 chartRef 更新方法供父组件调用
defineExpose({
  updateChart: loadData
})

// 监听配置变化重绘
watch([dotSize, countThreshold], () => {
  renderChart()
})

// 监听属性变化重新加载
watch(() => [
  props.startDate,
  props.endDate,
  props.selectedCompanies,
  props.selectedIndustries,
  props.selectedCategories,
  props.selectedIndustryLevel1,
  props.selectedIndustryLevel2
], () => {
  loadData()
}, { deep: true })

onMounted(() => {
  loadData()
  if (chartRef.value) {
    resizeObserver.value = new ResizeObserver(() => {
      renderChart()
    })
    resizeObserver.value.observe(chartRef.value)
  }
})

onUnmounted(() => {
  d3.selectAll(".scatter-tooltip").remove()
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
  }
})
</script>

<style scoped>
.scatter-chart-container {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
}

.chart-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
}

.chart-wrapper {
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.settings-content {
  padding: 5px;
}

.setting-item {
  margin-bottom: 10px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sub-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
  font-size: 12px;
  color: #606266;
}

.info-text {
  font-size: 12px;
  color: #909399;
  font-style: italic;
}

.label {
  font-weight: 500;
  margin-right: 8px;
}
</style>
