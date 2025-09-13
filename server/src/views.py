#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工商投诉数据分析系统 - API接口 
整合了数据管理、分析功能的Flask路由
"""

from src import app
from src.models import Model
from flask import request, jsonify
import json
import logging

logger = logging.getLogger(__name__)

# 初始化模型
model = Model()
print("================================================================")
print("工商投诉数据分析系统 API 初始化完成")
print("================================================================")

# ============ 基础信息接口 ============

@app.route('/')
def index():
    """首页"""
    return {
        "message": "工商投诉数据分析系统 API",
        "version": "1.0.0",
        "status": "running"
    }

@app.route('/health')
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "工商投诉数据分析系统",
        "version": "1.0.0"
    }

# ============ 数据管理接口 ============

@app.route('/data/summary')
def get_data_summary():
    """获取数据摘要"""
    try:
        summary = model.get_data_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"获取数据摘要失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/data/preview')
def get_data_preview():
    """获取数据预览"""
    try:
        limit = request.args.get('limit', 10, type=int)
        preview = model.get_data_preview(limit=limit)
        return jsonify(preview)
    except Exception as e:
        logger.error(f"获取数据预览失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/data/filter', methods=['GET', 'POST'])
def filter_data():
    """筛选数据"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            entity_field = data.get('entity_field')
            entity_values = data.get('entity_values')
            limit = data.get('limit', 100)
        else:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            entity_field = request.args.get('entity_field')
            entity_values = request.args.get('entity_values')
            limit = request.args.get('limit', 100, type=int)
            
            # 处理逗号分隔的值
            if entity_values:
                entity_values = entity_values.split(',')
        
        result = model.filter_data(
            start_date=start_date,
            end_date=end_date,
            entity_field=entity_field,
            entity_values=entity_values,
            limit=limit
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"数据筛选失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 分析接口 ============

@app.route('/analysis/time-series', methods=['POST'])
def analyze_time_series():
    """时序分析"""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        methods = data.get('methods', ['acf', 'stl'])
        
        result = model.analyze_time_series(
            start_date=start_date,
            end_date=end_date,
            methods=methods
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"时序分析失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analysis/acf', methods=['GET', 'POST'])
def acf_analysis():
    """ACF自相关分析"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            lags = data.get('lags', 40)
        else:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            lags = request.args.get('lags', 40, type=int)
        
        # 使用时序分析功能
        result = model.analyze_time_series(
            start_date=start_date,
            end_date=end_date,
            methods=['acf']
        )
        
        # 返回ACF分析结果
        acf_result = result.get('analysis', {}).get('acf', {})
        
        return jsonify({
            "analysis_type": "acf",
            "results": acf_result
        })
        
    except Exception as e:
        logger.error(f"ACF分析失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analysis/stl', methods=['GET', 'POST'])
def stl_decomposition():
    """STL季节性分解"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            seasonal = data.get('seasonal', 7)
        else:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            seasonal = request.args.get('seasonal', 7, type=int)
        
        # 使用时序分析功能
        result = model.analyze_time_series(
            start_date=start_date,
            end_date=end_date,
            methods=['stl']
        )
        
        # 返回STL分析结果
        stl_result = result.get('analysis', {}).get('stl', {})
        
        return jsonify({
            "analysis_type": "stl",
            "results": stl_result
        })
        
    except Exception as e:
        logger.error(f"STL分解失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analysis/report', methods=['POST'])
def generate_report():
    """生成分析报告"""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        entity_field = data.get('entity_field', '企业名称')
        
        result = model.generate_report(
            start_date=start_date,
            end_date=end_date,
            entity_field=entity_field
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 仪表板接口 ============

@app.route('/dashboard/filter-options')
def get_filter_options():
    """获取筛选选项"""
    try:
        result = model.get_filter_options()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/stats', methods=['GET', 'POST'])
def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            companies = data.get('companies', [])
            industries = data.get('industries', [])
            categories = data.get('categories', [])
        else:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            companies = request.args.getlist('companies')
            industries = request.args.getlist('industries')
            categories = request.args.getlist('categories')
        
        # 调试日志
        logger.info(f"仪表板统计请求参数: start_date={start_date}, end_date={end_date}")
        logger.info(f"筛选条件: companies={len(companies) if companies else 0}, industries={len(industries) if industries else 0}, categories={len(categories) if categories else 0}")
        
        result = model.get_dashboard_stats(
            start_date=start_date,
            end_date=end_date,
            companies=companies if companies else None,
            industries=industries if industries else None,
            categories=categories if categories else None
        )
        
        logger.info(f"返回统计结果: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取仪表板统计失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/trend', methods=['GET', 'POST'])
def get_trend_data():
    """获取投诉趋势数据"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            period = data.get('period', 'day')
            companies = data.get('companies', [])
            industries = data.get('industries', [])
            categories = data.get('categories', [])
        else:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            period = request.args.get('period', 'day')
            companies = request.args.getlist('companies')
            industries = request.args.getlist('industries')
            categories = request.args.getlist('categories')
        
        result = model.get_trend_data(
            start_date=start_date,
            end_date=end_date,
            period=period,
            companies=companies if companies else None,
            industries=industries if industries else None,
            categories=categories if categories else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 兼容原va-framework接口 ============

@app.route('/get_all_entities')
def get_all_entities():
    """获取所有实体（兼容接口）"""
    try:
        summary = model.get_data_summary()
        
        # 构造兼容格式的实体数据
        entities = {}
        
        if 'entity_stats' in summary:
            for field, stats in summary['entity_stats'].items():
                entities[field] = list(stats.keys())
        
        return jsonify(entities)
        
    except Exception as e:
        logger.error(f"获取实体数据失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_complaint_time_series', methods=['POST'])
def get_complaint_time_series():
    """获取投诉时间序列（新接口）"""
    try:
        post_data = request.data.decode()
        post_data = json.loads(post_data)
        start_date = post_data.get("start_date")
        end_date = post_data.get("end_date")
        entity_field = post_data.get("entity_field")
        entity_values = post_data.get("entity_values")
        
        # 筛选数据
        filtered_result = model.filter_data(
            start_date=start_date,
            end_date=end_date,
            entity_field=entity_field,
            entity_values=entity_values,
            limit=10000  # 大量数据用于时序分析
        )
        
        # 进行时序分析
        analysis_result = model.analyze_time_series(
            start_date=start_date,
            end_date=end_date,
            methods=['acf', 'stl']
        )
        
        return jsonify({
            "filtered_data": filtered_result,
            "time_series_analysis": analysis_result
        })
        
    except Exception as e:
        logger.error(f"时序数据获取失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_complaint_analysis', methods=['POST'])
def get_complaint_analysis():
    """获取投诉分析（新接口）"""
    try:
        post_data = request.data.decode()
        post_data = json.loads(post_data)
        start_date = post_data.get("start_date")
        end_date = post_data.get("end_date")
        analysis_type = post_data.get("analysis_type", "summary")
        
        if analysis_type == "report":
            result = model.generate_report(
                start_date=start_date,
                end_date=end_date
            )
        else:
            result = model.get_data_summary()
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"投诉分析失败: {e}")
        return jsonify({"error": str(e)}), 500

# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "接口不存在"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500