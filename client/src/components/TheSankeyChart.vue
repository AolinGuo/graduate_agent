<template>
  <el-card class="sankey-card" shadow="hover">
    <template #header>
      <div class="card-header-compact">
        <span>行业分层流转桑基图</span>
      </div>
    </template>
    <div class="sankey-chart-container">
      <!-- 调试信息 -->
      <div style="font-size: 12px; color: #666; padding: 5px; background: #f0f0f0; border: 1px solid #ccc;">
        调试信息:<br>
        - sankeyData: {{ sankeyData }}<br>
        - sankeyData存在: {{ !!sankeyData }}<br>
        - nodes长度: {{ sankeyData?.nodes?.length || 0 }}<br>
        - links长度: {{ sankeyData?.links?.length || 0 }}<br>
        - 条件判断结果: {{ !sankeyData || !sankeyData.nodes || sankeyData.nodes.length === 0 }}<br>
        - 类型: {{ typeof sankeyData }}
      </div>

      <!-- 图表容器 -->
      <div ref="sankeyChart" class="sankey-chart" style="border: 2px solid red; min-height: 200px;">
        <!-- 测试文本 -->
        <div style="padding: 20px; background: yellow; color: black;">
          图表容器已加载 - sankeyData: {{ JSON.stringify(sankeyData) }}
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { getSankeyData } from '@/stores/complaint-store'
import * as d3 from 'd3'
import { sankey as d3Sankey, sankeyLinkHorizontal } from 'd3-sankey'

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
const sankeyData = ref({
  nodes: [
    { name: "来源A", category: "source" },
    { name: "来源B", category: "source" },
    { name: "类别1", category: "category" },
    { name: "类别2", category: "category" },
    { name: "单位1", category: "unit" },
    { name: "单位2", category: "unit" }
  ],
  links: [
    { source: 0, target: 2, value: 10 },
    { source: 0, target: 3, value: 5 },
    { source: 1, target: 2, value: 8 },
    { source: 1, target: 3, value: 3 },
    { source: 2, target: 4, value: 12 },
    { source: 2, target: 5, value: 6 },
    { source: 3, target: 4, value: 4 },
    { source: 3, target: 5, value: 4 }
  ]
})

// Chart引用
const sankeyChart = ref(null)

// 更新桑基图
const updateSankeyChart = async () => {
  console.log('桑基图更新参数:', {
    startDate: props.startDate,
    endDate: props.endDate,
    selectedCompanies: props.selectedCompanies,
    selectedIndustries: props.selectedIndustries,
    selectedCategories: props.selectedCategories,
    selectedIndustryLevel1: props.selectedIndustryLevel1,
    selectedIndustryLevel2: props.selectedIndustryLevel2
  })

  if (!props.startDate || !props.endDate) {
    console.log('时间范围未设置，跳过桑基图更新')
    return
  }

  try {
    const requestParams = {
      start_date: props.startDate,
      end_date: props.endDate,
      companies: props.selectedCompanies.length > 0 ? props.selectedCompanies : undefined,
      industries: props.selectedIndustries.length > 0 ? props.selectedIndustries : undefined,
      categories: props.selectedCategories.length > 0 ? props.selectedCategories : undefined,
      industry_level1: props.selectedIndustryLevel1.length > 0 ? props.selectedIndustryLevel1 : undefined,
      industry_level2: props.selectedIndustryLevel2.length > 0 ? props.selectedIndustryLevel2 : undefined
    }
    console.log('发送桑基图请求参数:', requestParams)

    const response = await getSankeyData(requestParams)
    console.log('桑基图API响应:', response)
    console.log('响应状态:', response.status)
    console.log('响应数据类型:', typeof response.data)
    console.log('响应数据:', response.data)

    if (response.data && !response.data.error) {
      console.log('接收到桑基图数据:', response.data)
      console.log('节点数量:', response.data.nodes?.length || 0)
      console.log('链接数量:', response.data.links?.length || 0)

      // 直接赋值数据
      sankeyData.value = response.data
      console.log('设置sankeyData后:', sankeyData.value)

      await nextTick()
      renderSankeyChart()
    } else {
      console.error('桑基图数据格式错误:', response.data)
      console.log('设置sankeyData为空对象')
      sankeyData.value = { nodes: [], links: [] }
    }
  } catch (error) {
    console.error('获取桑基图数据失败:', error)
    console.error('错误详情:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      config: error.config
    })
    sankeyData.value = null
  }
}

// 渲染桑基图
const renderSankeyChart = () => {
  console.log('开始渲染桑基图，容器存在:', !!sankeyChart.value, '数据存在:', !!sankeyData.value)

  if (!sankeyChart.value) {
    console.warn('桑基图容器不存在')
    return
  }

  const container = sankeyChart.value
  const data = sankeyData.value

  if (!container || !data || !data.nodes || data.nodes.length === 0) {
    console.log('数据无效，跳过渲染')
    return
  }

  const width = container.offsetWidth
  const height = container.offsetHeight

  const svg = d3.select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height)

  const g = svg.append("g")
    .attr("transform", `translate(10, 10)`)

  const innerWidth = width - 20
  const innerHeight = height - 20

  console.log('SVG创建完成，尺寸:', { width, height, innerWidth, innerHeight })

  // 2. 使用引入的 d3Sankey 替代 d3.sankey
  const sankeyGenerator = d3Sankey()
    .nodeWidth(15)
    .nodePadding(10)
    .extent([[10, 10], [innerWidth - 10, innerHeight - 10]])

  // 转换数据格式 - 深拷贝以避免修改原始数据
  const graph = {
    nodes: JSON.parse(JSON.stringify(data.nodes)),
    links: JSON.parse(JSON.stringify(data.links))
  }

  console.log('转换后的graph:', {
    nodesCount: graph.nodes.length,
    linksCount: graph.links.length,
    firstFewNodes: graph.nodes.slice(0, 5),
    firstFewLinks: graph.links.slice(0, 5)
  })

  console.log('节点名称映射检查:')
  graph.nodes.forEach((node, index) => {
    console.log(`节点${index}: ${node.name} (${node.category})`)
  })

  // 检查节点索引是否超出范围
  const maxNodeIndex = graph.nodes.length - 1
  const invalidLinks = graph.links.filter(link =>
    link.source > maxNodeIndex || link.target > maxNodeIndex ||
    link.source < 0 || link.target < 0
  )

  if (invalidLinks.length > 0) {
    console.error('发现无效的节点索引:', invalidLinks.slice(0, 5))
    console.error('最大节点索引:', maxNodeIndex)
    console.error('节点名称映射检查:')
    graph.nodes.forEach((node, index) => {
      console.log(`节点${index}: ${node.name}`)
    })
    return
  }

  // 计算布局
  try {
    sankeyGenerator(graph)
    console.log('桑基图计算成功')
    console.log('计算后的前3个节点坐标:', graph.nodes.slice(0, 3).map(n => ({
      name: n.name,
      x0: n.x0,
      y0: n.y0,
      x1: n.x1,
      y1: n.y1
    })))
  } catch (err) {
    console.error("Sankey 计算失败:", err)
    console.error('错误堆栈:', err.stack)
    return
  }

  // 创建颜色比例尺
  const color = d3.scaleOrdinal(d3.schemeCategory10)

  // 4. 绘制链接：使用 sankeyLinkHorizontal()
  g.append("g")
    .selectAll("path")
    .data(graph.links)
    .enter()
    .append("path")
    .attr("d", sankeyLinkHorizontal())
    .attr("stroke", d => color(d.source.name))
    .attr("stroke-width", d => Math.max(1, d.width))
    .attr("fill", "none")
    .attr("opacity", 0.4)

  console.log('链接绘制完成')

  // 5. 绘制节点 (保持你原有的逻辑，但使用 graph.nodes 而不是 data.nodes)
  const node = g.append("g")
    .selectAll("rect")
    .data(graph.nodes)
    .enter()
    .append("rect")
    .attr("x", d => d.x0)
    .attr("y", d => d.y0)
    .attr("height", d => d.y1 - d.y0)
    .attr("width", d => d.x1 - d.x0)
    .attr("fill", d => {
      if (d.name === "空白") return "#cccccc"             // 灰色 - 空值
      if (d.category === "source") return "#409eff"        // 蓝色 - 来源
      if (d.category === "industry_l1") return "#67c23a"   // 绿色 - 行业一级
      if (d.category === "industry_l2") return "#f5a623"   // 橙黄色 - 行业二级
      if (d.category === "unit") return "#e6a23c"          // 橙色 - 处理单位
      return color(d.name)
    })
    .attr("rx", 2)
    .attr("stroke", "#fff")
    .attr("stroke-width", 1)
    .on("mouseover", function(event, d) {
      // 高亮当前节点
      d3.select(this).attr("stroke", "#000").attr("stroke-width", 2)

      // 显示详细信息
      const tooltip = d3.select("body").append("div")
        .attr("class", "d3-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0, 0, 0, 0.8)")
        .style("color", "white")
        .style("padding", "10px")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("opacity", 0)
        .style("max-width", "300px")

      // 统计该节点的相关信息
      let tooltipContent = `<strong>${d.name}</strong><br/>`

      if (d.category === "unit") {
        // 处理单位：显示主要来源和类别
        const incomingLinks = graph.links.filter(link => link.target.index === d.index)
        const sources = {}
        const industries_l1 = {}
        const industries_l2 = {}

        incomingLinks.forEach(link => {
          const sourceNode = graph.nodes[link.source.index]
          const industryNode = graph.nodes.find(n =>
            graph.links.some(l => l.source.index === n.index && l.target.index === d.index)
          )

          if (sourceNode.category === "source") {
            sources[sourceNode.name] = (sources[sourceNode.name] || 0) + link.value
          }
          if (industryNode && industryNode.category === "industry_l1") {
            industries_l1[industryNode.name] = (industries_l1[industryNode.name] || 0) + link.value
          }
          if (industryNode && industryNode.category === "industry_l2") {
            industries_l2[industryNode.name] = (industries_l2[industryNode.name] || 0) + link.value
          }
        })

        tooltipContent += "<br/><strong>主要来源:</strong><br/>"
        Object.entries(sources)
          .sort(([,a], [,b]) => b - a)
          .slice(0, 3)
          .forEach(([name, count]) => {
            tooltipContent += `${name}: ${count}<br/>`
          })

        if (Object.keys(industries_l1).length > 0) {
          tooltipContent += "<br/><strong>行业一级:</strong><br/>"
          Object.entries(industries_l1)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 3)
            .forEach(([name, count]) => {
              tooltipContent += `${name}: ${count}<br/>`
            })
        }

        if (Object.keys(industries_l2).length > 0) {
          tooltipContent += "<br/><strong>行业二级:</strong><br/>"
          Object.entries(industries_l2)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 3)
            .forEach(([name, count]) => {
              tooltipContent += `${name}: ${count}<br/>`
            })
        }
      } else {
        // 其他节点：显示流入和流出
        const incoming = graph.links.filter(link => link.target.index === d.index)
          .reduce((sum, link) => sum + link.value, 0)
        const outgoing = graph.links.filter(link => link.source.index === d.index)
          .reduce((sum, link) => sum + link.value, 0)

        tooltipContent += `流入: ${incoming}<br/>流出: ${outgoing}`
      }

      tooltip.transition().duration(200).style("opacity", 1)
      tooltip.html(tooltipContent)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px")
    })
    .on("mouseout", function() {
      d3.select(this).attr("stroke", "#fff").attr("stroke-width", 1)
      d3.selectAll(".d3-tooltip").remove()
    })

  console.log('节点绘制完成')

  // 6. 绘制文字 (同理使用 graph.nodes)
  g.append("g")
    .selectAll("text")
    .data(graph.nodes)
    .enter()
    .append("text")
    .attr("x", d => d.x0 < innerWidth / 3 ? d.x1 + 6 : d.x0 > innerWidth * 2 / 3 ? d.x0 - 6 : (d.x0 + d.x1) / 2)
    .attr("y", d => (d.y0 + d.y1) / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", d => d.x0 < innerWidth / 3 ? "start" : d.x0 > innerWidth * 2 / 3 ? "end" : "middle")
    .attr("font-size", "10px")
    .attr("fill", "#333")
    .text(d => d.name.length > 12 ? d.name.substring(0, 12) + "..." : d.name)

  console.log('桑基图渲染完成！')
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
  updateSankeyChart()
}, { deep: true })

// 暴露更新方法给父组件调用
defineExpose({
  updateSankeyChart
})

// 组件挂载时初始化
onMounted(() => {
  console.log('TheSankeyChart组件已挂载')
  console.log('初始数据:', sankeyData.value)

  // 渲染图表
  nextTick().then(() => {
    renderSankeyChart()
  })
})
</script>

<style scoped>
.sankey-card {
  /* 确保 card 有足够高度承载图表 */
  min-height: 450px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sankey-card :deep(.el-card__header) {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.sankey-card :deep(.el-card__body) {
  flex: 1;
  padding: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sankey-chart-container {
  flex: 1;
  min-height: 0;
}

.sankey-chart {
  width: 100%;
  height: 400px; /* 建议先写死一个高度测试，确保护理容器有空间 */
  min-height: 300px;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
  text-align: center;
  height: 100%;
}

.empty-state p {
  margin: 10px 0 0 0;
  font-size: 13px;
}
</style>
