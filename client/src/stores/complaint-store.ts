/**
 * 工商投诉数据分析系统 - API接口和状态管理
 */

import { defineStore } from 'pinia'
import axios from 'axios'

// 配置axios基础URL
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  error => {
    console.error('请求错误:', error.response?.status, error.config?.url, error.message)
    return Promise.reject(error)
  }
)

// ============ 系统信息相关接口 ============

export const getSystemData = () => {
  return apiClient.get('/data/summary')
}

export const getHealthStatus = () => {
  return apiClient.get('/health')
}

// ============ 数据管理相关接口 ============

export const getDataPreview = (limit = 10) => {
  return apiClient.get(`/data/preview?limit=${limit}`)
}

export const getDataSummary = () => {
  return apiClient.get('/data/summary')
}

export const filterData = (params) => {
  return apiClient.post('/data/filter', params)
}

export const getDataFields = () => {
  return apiClient.get('/data/fields')
}

// ============ 分析相关接口 ============

export const analyzeTimeSeries = (params) => {
  return apiClient.post('/analysis/time-series', params)
}

export const performACFAnalysis = (params) => {
  return apiClient.post('/analysis/acf', params)
}

export const performSTLDecomposition = (params) => {
  return apiClient.post('/analysis/stl', params)
}

export const generateReport = (params) => {
  return apiClient.post('/analysis/report', params)
}

// ============ 仪表板相关接口 ============

export const getFilterOptions = () => {
  return apiClient.get('/dashboard/filter-options')
}

export const getDashboardStats = (params) => {
  return apiClient.post('/dashboard/stats', params)
}

export const getTrendData = (params) => {
  return apiClient.post('/dashboard/trend', params)
}

// ============ 兼容原va-framework接口 ============

export const getAllEntities = () => {
  return apiClient.get('/get_all_entities')
}

export const getComplaintTimeSeries = (params) => {
  return apiClient.post('/get_complaint_time_series', params)
}

export const getComplaintAnalysis = (params) => {
  return apiClient.post('/get_complaint_analysis', params)
}

// ============ Pinia Store ============

export const useComplaintStore = defineStore('complaint', {
  state: () => ({
    // 系统状态
    systemData: null,
    loading: false,
    
    // 数据状态
    dataPreview: [],
    totalRecords: 0,
    dataFields: [],
    
    // 分析状态
    analysisResults: null,
    reportData: null,
    
    // 时间范围
    dateInterval: ['2020-01-01', '2024-12-31'],
    
    // 筛选条件
    selectedEntities: [],
    filterConditions: {}
  }),
  
  getters: {
    // 获取可用的数据字段
    availableFields: (state) => {
      return state.dataFields || []
    },
    
    // 获取系统状态摘要
    systemSummary: (state) => {
      if (!state.systemData) return null
      return {
        totalRecords: state.systemData.total_records || 0,
        fieldCount: state.systemData.field_count || 0,
        dateRange: state.systemData.date_range || null
      }
    }
  },
  
  actions: {
    // 初始化系统数据
    async initialize() {
      this.loading = true
      try {
        const [systemResponse, previewResponse] = await Promise.all([
          getSystemData(),
          getDataPreview(10)
        ])
        
        this.systemData = systemResponse.data
        this.dataPreview = previewResponse.data.sample_data || []
        this.totalRecords = previewResponse.data.total_records || 0
        this.dataFields = previewResponse.data.fields || []
        
        console.log('系统初始化完成')
      } catch (error) {
        console.error('系统初始化失败:', error)
      } finally {
        this.loading = false
      }
    },
    
    // 更新数据预览
    async updateDataPreview(limit = 10) {
      try {
        const response = await getDataPreview(limit)
        this.dataPreview = response.data.sample_data || []
        this.totalRecords = response.data.total_records || 0
      } catch (error) {
        console.error('更新数据预览失败:', error)
      }
    },
    
    // 执行时序分析
    async performTimeSeriesAnalysis(params) {
      this.loading = true
      try {
        const response = await analyzeTimeSeries(params)
        this.analysisResults = response.data
        return response.data
      } catch (error) {
        console.error('时序分析失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // 生成分析报告
    async createReport(params) {
      this.loading = true
      try {
        const response = await generateReport(params)
        this.reportData = response.data
        return response.data
      } catch (error) {
        console.error('报告生成失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // 通用HTTP GET请求
    async get(api, callback = null) {
      try {
        const response = await apiClient.get(api)
        if (callback) callback(response.data)
        return response.data
      } catch (error) {
        console.error('GET请求失败:', error)
        throw error
      }
    },
    
    // 通用HTTP POST请求
    async post(api, params, callback = null) {
      try {
        const response = await apiClient.post(api, params)
        if (callback) callback(response.data)
        return response.data
      } catch (error) {
        console.error('POST请求失败:', error)
        throw error
      }
    }
  }
})

