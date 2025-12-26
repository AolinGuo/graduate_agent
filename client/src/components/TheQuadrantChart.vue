<template>
  <div class="quadrant-chart-container" v-loading="loading">
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
    
    console.log('加载四象限数据:', params)
    const response = await getQuadrantData(params)
    
    if (response.data && response.data.data) {
      data.value = response.data.data
      console.log('四象限数据加载成功:', data.value.length)
      
      await nextTick()
      renderChart()
    } else if (response.data && response.data.nodes) {
       // 兼容旧API格式（如果有）
       data.value = response.data.nodes
       await nextTick()
       renderChart()
    } else {
      data.value = []
    }
  } catch (error) {
    console.error('加载四象限数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 渲染图表
const renderChart = () => {
  if (!chartRef.value || !data.value || data.value.length === 0) return
  
  const container = chartRef.value
  d3.select(container).selectAll("*").remove()
  
  const width = container.clientWidth
  const height = container.clientHeight
  const margin = { top: 20, right: 30, bottom: 40, left: 50 }
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom
  
  const svg = d3.select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // 数据处理
  // X轴使用Log2 (加1避免log(0))
  const xDomain = [0, d3.max(data.value, d => Math.log2(d.count + 1)) * 1.1 || 10]
  const yDomain = [0, d3.max(data.value, d => d.diversity) * 1.1 || 5]
  
  const xScale = d3.scaleLinear()
    .domain(xDomain)
    .range([0, innerWidth])
    .nice()
  
  const yScale = d3.scaleLinear()
    .domain(yDomain)
    .range([innerHeight, 0])
    .nice()

  // 颜色映射 (基于投诉类型)
  const categories = Array.from(new Set(data.value.map(d => d.category))).filter(Boolean)
  const colorScale = d3.scaleOrdinal(d3.schemeTableau10).domain(categories)
  

  
  // 绘制轴
  svg.append("g")
    .attr("transform", `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale).ticks(5))
    .append("text")
    .attr("x", innerWidth)
    .attr("y", -6)
    .attr("fill", "#666")
    .attr("text-anchor", "end")
    .text("log2(投诉数量)")
    
  svg.append("g")
    .call(d3.axisLeft(yScale).ticks(Math.min(10, d3.max(yDomain))).tickFormat(d3.format("d")))
    .append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 6)
    .attr("dy", "0.71em")
    .attr("fill", "#666")
    .attr("text-anchor", "end")
    .text("涉及问题(2)")
    

    
  // 绘制点
  const circles = svg.selectAll(".dot")
    .data(data.value)
    .enter().append("circle")
    .attr("class", "dot")
    .attr("cx", d => xScale(Math.log2(d.count + 1)))
    .attr("cy", d => yScale(d.diversity))
    .attr("r", dotSize.value)
    .attr("fill", d => colorScale(d.category || '其他'))
    .attr("opacity", 0.7)
    .attr("stroke", "#fff")
    .attr("stroke-width", 0.5)
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      event.stopPropagation()
      emit('click-node', d)
    })
    
  // 添加交互 Tooltip
  const tooltip = d3.select("body").append("div")
    .attr("class", "quadrant-tooltip")
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
        投诉数量: ${d.count}<br/>
        投诉类型数目: ${d.diversity}<br/>
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
      circles.attr("fill", d => colorScale(d.category || '其他'))
      return
    }
    
    const [[x0, y0], [x1, y1]] = event.selection
    const selected = []
    
    circles.attr("fill", d => {
      const cx = xScale(Math.log2(d.count + 1))
      const cy = yScale(d.diversity)
      // 判断点是否在矩形内
      const isSelected = x0 <= cx && cx <= x1 && y0 <= cy && cy <= y1
      
      if (isSelected) {
        selected.push(d.name)
        return "#f56c6c" // 选中时高亮红色，或者保持原色加粗边框？这里暂时用红色以保持选中习惯
      } else {
        return colorScale(d.category || '其他')
      }
    })
    
    emit('update:selection', selected)
  }

  // 添加图例
  const legend = svg.append("g")
    .attr("transform", `translate(${innerWidth - 100}, 10)`)
    
  categories.slice(0, 10).forEach((cat, i) => { // 限制显示数量防止溢出
      const lg = legend.append("g").attr("transform", `translate(0, ${i * 15})`)
      lg.append("circle").attr("r", 4).attr("fill", colorScale(cat))
      lg.append("text").attr("x", 10).attr("y", 4).text(cat).style("font-size", "10px").attr("fill", "#666")
  })
}

// 暴露 chartRef 更新方法供父组件调用
defineExpose({
  updateChart: loadData
})

// 监听配置变化重绘
watch([dotSize], () => {
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
  d3.selectAll(".quadrant-tooltip").remove()
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
  }
})
</script>

<style scoped>
.quadrant-chart-container {
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
