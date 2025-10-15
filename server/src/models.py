#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工商投诉数据分析系统 - 核心模型
整合了数据服务、分析服务等核心业务逻辑
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import logging

# 尝试导入分析库，如果失败则禁用相关功能
try:
    from statsmodels.tsa.stattools import acf
    from statsmodels.tsa.seasonal import STL

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logging.warning("缺少statsmodels库，时序分析功能将被禁用")


logger = logging.getLogger(__name__)


class Model:
    """工商投诉数据分析核心模型"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"

        # 数据缓存
        self._data_cache = None
        self._total_records = 0

        # 初始化数据
        self._load_data()
        logger.info("工商投诉数据分析模型初始化完成")

    def _load_data(self):
        """加载数据"""
        try:
            # 尝试加载不同的数据文件
            data_files = [
                "processed_data.csv",
                "original_data.csv",
                "train_dataset.json",
            ]

            for filename in data_files:
                file_path = self.data_dir / filename
                if file_path.exists():
                    logger.info(f"找到数据文件: {file_path}")

                    if filename.endswith(".csv"):
                        try:
                            self._data_cache = pd.read_csv(
                                file_path, encoding="utf-8", low_memory=False
                            )
                        except UnicodeDecodeError:
                            logger.warning("UTF-8编码失败，尝试GBK编码...")
                            self._data_cache = pd.read_csv(
                                file_path, encoding="gbk", low_memory=False
                            )

                    elif filename.endswith(".json"):
                        with open(file_path, "r", encoding="utf-8") as f:
                            json_data = json.load(f)

                        if isinstance(json_data, list):
                            self._data_cache = pd.DataFrame(json_data)
                        elif isinstance(json_data, dict) and "data" in json_data:
                            self._data_cache = pd.DataFrame(json_data["data"])
                        else:
                            self._data_cache = pd.DataFrame([json_data])

                    self._total_records = len(self._data_cache)
                    logger.info(f"成功加载数据集: {len(self._data_cache)} 条记录")

                    # 处理时间字段
                    self._process_date_fields()
                    break

            if self._data_cache is None:
                logger.warning("未找到有效的数据文件，创建空数据集")
                self._data_cache = pd.DataFrame()
                self._total_records = 0

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self._data_cache = pd.DataFrame()
            self._total_records = 0

    def _process_date_fields(self):
        """处理日期字段"""
        if self._data_cache is None or self._data_cache.empty:
            return

        # 定义需要处理的时间字段
        timestamp_fields = [
            "市派单时间",
            "转派时间",
            "处理时间",
            "处理截止时间",
            "结案时间",
            "回访时间",
            "上报时间",
        ]

        # 转换时间字段
        for field in timestamp_fields:
            if field in self._data_cache.columns:
                try:
                    self._data_cache[field] = pd.to_datetime(
                        self._data_cache[field], errors="coerce"
                    )
                    logger.info(f"✓ 转换时间字段: {field}")
                except Exception as e:
                    logger.warning(f"处理时间字段 {field} 失败: {e}")

        # 基于市派单时间创建分析用的时间字段
        if (
            "市派单时间" in self._data_cache.columns
            and not self._data_cache["市派单时间"].isna().all()
        ):
            try:
                # 确保市派单时间字段是datetime类型
                if not pd.api.types.is_datetime64_any_dtype(
                    self._data_cache["市派单时间"]
                ):
                    logger.warning("市派单时间字段不是datetime类型，尝试重新转换")
                    self._data_cache["市派单时间"] = pd.to_datetime(
                        self._data_cache["市派单时间"], errors="coerce"
                    )

                # 检查转换后的数据类型
                if pd.api.types.is_datetime64_any_dtype(self._data_cache["市派单时间"]):
                    valid_dates = self._data_cache["市派单时间"].notna()
                    if valid_dates.any():
                        # 安全地使用.dt访问器
                        datetime_series = self._data_cache.loc[
                            valid_dates, "市派单时间"
                        ]
                        self._data_cache.loc[valid_dates, "日期"] = (
                            datetime_series.dt.date
                        )
                        self._data_cache.loc[valid_dates, "年份"] = (
                            datetime_series.dt.year
                        )
                        self._data_cache.loc[valid_dates, "月份"] = (
                            datetime_series.dt.month
                        )

                        logger.info("✓ 创建分析用时间字段")
                        logger.info(f"✓ 有效日期记录数: {valid_dates.sum()}")
                    else:
                        logger.warning("没有有效的市派单时间数据")
                else:
                    logger.error("无法将市派单时间转换为datetime类型")
            except Exception as e:
                logger.error(f"创建分析时间字段失败: {e}")
                import traceback

                logger.error(f"详细错误信息: {traceback.format_exc()}")

    def get_data_summary(self):
        """获取数据摘要"""
        if self._data_cache is None or self._data_cache.empty:
            return {"message": "没有数据", "total_records": 0}

        summary = {
            "total_records": len(self._data_cache),
            "field_count": len(self._data_cache.columns),
            "fields": list(self._data_cache.columns),
        }

        # 时间范围
        if "日期" in self._data_cache.columns:
            date_range = {
                "start": str(self._data_cache["日期"].min()),
                "end": str(self._data_cache["日期"].max()),
            }
            summary["date_range"] = date_range

        # 热门实体统计
        entity_stats = {}
        for field in ["企业名称", "问题分类", "行业分类"]:
            if field in self._data_cache.columns:
                top_values = self._data_cache[field].value_counts().head(5).to_dict()
                entity_stats[field] = top_values

        summary["entity_stats"] = entity_stats

        return summary

    def get_data_preview(self, limit=10):
        """获取数据预览"""
        if self._data_cache is None or self._data_cache.empty:
            return {"total_records": 0, "sample_data": [], "fields": []}

        sample_data = self._data_cache.head(limit).to_dict("records")

        # 处理日期序列化
        for record in sample_data:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = str(value)

        return {
            "total_records": len(self._data_cache),
            "sample_data": sample_data,
            "fields": list(self._data_cache.columns),
        }

    def filter_data(
        self,
        start_date=None,
        end_date=None,
        entity_field=None,
        entity_values=None,
        limit=100,
    ):
        """筛选数据"""
        if self._data_cache is None or self._data_cache.empty:
            return {"data": [], "total": 0, "filtered": 0}

        filtered_data = self._data_cache.copy()

        # 时间筛选
        if start_date and "日期" in filtered_data.columns:
            start_date_obj = pd.to_datetime(start_date).date()
            filtered_data = filtered_data[filtered_data["日期"] >= start_date_obj]

        if end_date and "日期" in filtered_data.columns:
            end_date_obj = pd.to_datetime(end_date).date()
            filtered_data = filtered_data[filtered_data["日期"] <= end_date_obj]

        # 实体筛选
        if entity_field and entity_values and entity_field in filtered_data.columns:
            if isinstance(entity_values, str):
                entity_values = entity_values.split(",")
            filtered_data = filtered_data[
                filtered_data[entity_field].isin(entity_values)
            ]

        # 限制记录数
        result_data = filtered_data.head(limit)

        # 转换为字典格式
        data_list = result_data.to_dict("records")

        # 处理日期序列化
        for record in data_list:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = str(value)

        return {
            "data": data_list,
            "total": len(self._data_cache),
            "filtered": len(filtered_data),
            "returned": len(result_data),
        }

    def analyze_time_series(self, start_date=None, end_date=None, methods=None):
        """时序分析（向后兼容）"""
        return self.analyze_time_series_enhanced(start_date, end_date, methods)

    def analyze_time_series_enhanced(
        self,
        start_date=None,
        end_date=None,
        methods=None,
        companies=None,
        industries=None,
        categories=None,
        industry_level1=None,
        industry_level2=None,
    ):
        """增强版时序分析，支持筛选条件"""
        if methods is None:
            methods = ["acf", "stl"]

        # 使用增强的筛选功能
        filtered_data = self._get_filtered_data_enhanced(
            start_date,
            end_date,
            companies,
            industries,
            categories,
            industry_level1,
            industry_level2,
        )

        if filtered_data.empty:
            return {"analysis": {}, "charts": [], "message": "没有数据可供分析"}

        # 创建时间序列数据
        if "日期" not in filtered_data.columns:
            return {"analysis": {}, "charts": [], "message": "数据中缺少日期字段"}

        time_series = filtered_data.groupby("日期").size().reset_index(name="投诉数量")
        # 按日期排序确保时间序列的连续性
        time_series = time_series.sort_values("日期").reset_index(drop=True)

        logger.info(
            f"时序分析数据: {len(time_series)}个数据点, 日期范围: {time_series['日期'].min()} 至 {time_series['日期'].max()}"
        )

        results = {"time_series": time_series.to_dict("records")}
        charts = []

        # ACF分析
        if "acf" in methods and HAS_STATSMODELS:
            acf_result = self._acf_analysis(time_series)
            results["acf"] = acf_result
            charts.append(
                {"type": "acf", "title": "自相关函数(ACF)分析", "data": acf_result}
            )
        elif "acf" in methods:
            results["acf"] = {"error": "缺少statsmodels库，无法进行ACF分析"}

        # STL分解
        if "stl" in methods and HAS_STATSMODELS:
            stl_result = self._stl_decomposition(time_series)
            results["stl"] = stl_result
            charts.extend(
                [
                    {
                        "type": "line",
                        "title": "STL分解 - 趋势",
                        "data": stl_result.get("trend", []),
                    },
                    {
                        "type": "line",
                        "title": "STL分解 - 季节性",
                        "data": stl_result.get("seasonal", []),
                    },
                ]
            )
        elif "stl" in methods:
            results["stl"] = {"error": "缺少statsmodels库，无法进行STL分解"}

        return {"analysis": results, "charts": charts}

    def _get_filtered_data(self, start_date=None, end_date=None):
        """获取筛选后的数据"""
        return self._get_filtered_data_enhanced(start_date, end_date)

    def _get_filtered_data_enhanced(
        self,
        start_date=None,
        end_date=None,
        companies=None,
        industries=None,
        categories=None,
        industry_level1=None,
        industry_level2=None,
    ):
        """获取增强筛选后的数据"""
        if self._data_cache is None or self._data_cache.empty:
            logger.warning("数据缓存为空")
            return pd.DataFrame()

        data = self._data_cache.copy()
        logger.info(f"原始数据量: {len(data)} 条")

        # 时间筛选
        if start_date and "日期" in data.columns:
            try:
                start_date_obj = pd.to_datetime(start_date).date()
                # 确保日期字段不为空且有数据
                if data["日期"].notna().any():
                    data = data[data["日期"] >= start_date_obj]
                    logger.info(f"开始日期筛选后: {len(data)} 条")
                else:
                    logger.warning("日期字段全部为空，无法进行时间筛选")
            except Exception as e:
                logger.error(f"开始日期筛选失败: {e}")

        if end_date and "日期" in data.columns:
            try:
                end_date_obj = pd.to_datetime(end_date).date()
                if data["日期"].notna().any():
                    data = data[data["日期"] <= end_date_obj]
                    logger.info(f"结束日期筛选后: {len(data)} 条")
                else:
                    logger.warning("日期字段全部为空，无法进行时间筛选")
            except Exception as e:
                logger.error(f"结束日期筛选失败: {e}")

        # 企业筛选
        if companies and "企业名称" in data.columns:
            # 处理空值选项
            actual_companies = [c for c in companies if not c.startswith("[空值]")]
            has_null_option = any(c.startswith("[空值]") for c in companies)

            if has_null_option and actual_companies:
                # 包含空值和实际企业
                data = data[
                    (data["企业名称"].isin(actual_companies))
                    | (data["企业名称"].isnull())
                ]
            elif has_null_option:
                # 只选择空值
                data = data[data["企业名称"].isnull()]
            else:
                # 只选择实际企业
                data = data[data["企业名称"].isin(actual_companies)]
            logger.info(f"企业筛选后: {len(data)} 条")

        # 行业大类筛选
        if industry_level1 and "行业名称(1)" in data.columns:
            actual_level1 = [i for i in industry_level1 if not i.startswith("[空值]")]
            has_null_option = any(i.startswith("[空值]") for i in industry_level1)

            if has_null_option and actual_level1:
                data = data[
                    (data["行业名称(1)"].isin(actual_level1))
                    | (data["行业名称(1)"].isnull())
                ]
            elif has_null_option:
                data = data[data["行业名称(1)"].isnull()]
            else:
                data = data[data["行业名称(1)"].isin(actual_level1)]
            logger.info(f"行业大类筛选后: {len(data)} 条")

        # 行业中类筛选
        if industry_level2 and "行业名称(2)" in data.columns:
            actual_level2 = [i for i in industry_level2 if not i.startswith("[空值]")]
            has_null_option = any(i.startswith("[空值]") for i in industry_level2)

            if has_null_option and actual_level2:
                data = data[
                    (data["行业名称(2)"].isin(actual_level2))
                    | (data["行业名称(2)"].isnull())
                ]
            elif has_null_option:
                data = data[data["行业名称(2)"].isnull()]
            else:
                data = data[data["行业名称(2)"].isin(actual_level2)]
            logger.info(f"行业中类筛选后: {len(data)} 条")

        # 详细行业分类筛选（保持向后兼容）
        if industries and "行业分类" in data.columns:
            actual_industries = [i for i in industries if not i.startswith("[空值]")]
            has_null_option = any(i.startswith("[空值]") for i in industries)

            if has_null_option and actual_industries:
                data = data[
                    (data["行业分类"].isin(actual_industries))
                    | (data["行业分类"].isnull())
                ]
            elif has_null_option:
                data = data[data["行业分类"].isnull()]
            else:
                data = data[data["行业分类"].isin(actual_industries)]
            logger.info(f"详细行业分类筛选后: {len(data)} 条")

        # 问题分类筛选
        if categories and "问题分类" in data.columns:
            actual_categories = [c for c in categories if not c.startswith("[空值]")]
            has_null_option = any(c.startswith("[空值]") for c in categories)

            if has_null_option and actual_categories:
                data = data[
                    (data["问题分类"].isin(actual_categories))
                    | (data["问题分类"].isnull())
                ]
            elif has_null_option:
                data = data[data["问题分类"].isnull()]
            else:
                data = data[data["问题分类"].isin(actual_categories)]
            logger.info(f"问题分类筛选后: {len(data)} 条")

        return data

    def _acf_analysis(self, time_series, lags=40):
        """ACF分析"""
        if not HAS_STATSMODELS:
            return {"error": "缺少statsmodels库"}

        try:
            ts_values = time_series["投诉数量"].values

            if len(ts_values) < 10:
                return {"error": "数据量不足，无法进行ACF分析"}

            # 计算ACF
            acf_values = acf(ts_values, nlags=min(lags, len(ts_values) - 1))

            # 构建结果
            acf_data = []
            for i, val in enumerate(acf_values):
                acf_data.append({"lag": i, "acf_value": float(val)})

            # 计算显著性阈值
            n = len(ts_values)
            confidence_interval = 1.96 / np.sqrt(n)

            return {
                "acf_values": acf_data,
                "confidence_interval": confidence_interval,
                "interpretation": "在95%置信水平下进行ACF分析",
            }

        except Exception as e:
            logger.error(f"ACF分析失败: {e}")
            return {"error": str(e)}

    def _stl_decomposition(self, time_series, seasonal=12):
        """STL分解"""
        if not HAS_STATSMODELS:
            return {"error": "缺少statsmodels库"}

        try:
            ts_values = time_series["投诉数量"].values

            if len(ts_values) < seasonal * 2:
                return {"error": f"数据量不足，至少需要 {seasonal * 2} 个观测值"}

            # 使用真实的日期索引
            if "日期" in time_series.columns:
                # 将日期转换为 pandas Timestamp 索引
                dates = pd.to_datetime(time_series["日期"])
                # 确保日期是唯一且排序的
                dates = dates.sort_values()
                dates_unique = dates.drop_duplicates()

                if len(dates_unique) != len(ts_values):
                    logger.warning(
                        f"日期数量({len(dates_unique)})与数值数量({len(ts_values)})不匹配，使用日期范围填充"
                    )
                    # 创建连续的日期范围
                    start_date = dates.min()
                    end_date = dates.max()
                    date_index = pd.date_range(
                        start=start_date, end=end_date, freq="D"
                    )[: len(ts_values)]
                else:
                    date_index = dates_unique

                # 重新索引数据以匹配日期
                if len(date_index) > len(ts_values):
                    date_index = date_index[: len(ts_values)]
                elif len(date_index) < len(ts_values):
                    ts_values = ts_values[: len(date_index)]
            else:
                # 如果没有日期列，创建虚拟日期索引
                date_index = pd.date_range(
                    start="2023-01-01", periods=len(ts_values), freq="D"
                )

            # 创建带有真实日期索引的时间序列
            ts = pd.Series(ts_values, index=date_index)
            ts = ts.sort_index()  # 确保按日期排序

            logger.info(
                f"STL分解: 数据点数={len(ts)}, 日期范围={ts.index.min()}至{ts.index.max()}"
            )

            # 进行STL分解，显式指定周期
            try:
                # 对于日数据，月周期使用30天，年周期使用365天
                if len(ts) >= 30:
                    # 根据数据长度选择合适的周期
                    if seasonal == 12:  # 月周期，对于日数据约30天
                        actual_seasonal = min(29, len(ts) // 2)  # 确保是奇数
                        if actual_seasonal % 2 == 0:
                            actual_seasonal -= 1
                        actual_seasonal = max(7, actual_seasonal)  # 至少为7
                    else:
                        actual_seasonal = seasonal
                        if actual_seasonal % 2 == 0:
                            actual_seasonal += 1  # 转换为奇数
                        actual_seasonal = min(actual_seasonal, len(ts) // 2)
                        actual_seasonal = max(3, actual_seasonal)  # 至少为3

                    logger.info(
                        f"STL分解使用周期: {actual_seasonal} (数据点数: {len(ts)})"
                    )
                    stl = STL(ts, seasonal=actual_seasonal)
                    result = stl.fit()
                else:
                    return {
                        "error": f"数据量不足，需要至少30个观测值进行月周期分析，当前只有{len(ts)}个"
                    }
            except Exception as e:
                logger.warning(f"标准STL分解失败: {e}")
                # 尝试使用更简单的周期设置
                try:
                    simple_period = min(7, len(ts) // 3)  # 使用更小的周期
                    if simple_period % 2 == 0:
                        simple_period -= 1
                    simple_period = max(3, simple_period)  # 确保至少为3
                    logger.info(f"尝试使用简化周期: {simple_period}")
                    stl = STL(ts, seasonal=simple_period)
                    result = stl.fit()
                except Exception as e2:
                    logger.error(f"简化STL分解也失败: {e2}")
                    return {"error": f"STL分解失败: {str(e2)}"}

            # 构建结果，使用真实的日期索引
            date_strings = [d.strftime("%Y-%m-%d") for d in ts.index]

            return {
                "original": [
                    {"date": date_strings[i], "value": float(val)}
                    for i, val in enumerate(ts.values)
                ],
                "trend": [
                    {"date": date_strings[i], "value": float(val)}
                    for i, val in enumerate(result.trend.values)
                ],
                "seasonal": [
                    {"date": date_strings[i], "value": float(val)}
                    for i, val in enumerate(result.seasonal.values)
                ],
                "resid": [
                    {"date": date_strings[i], "value": float(val)}
                    for i, val in enumerate(result.resid.values)
                ],
            }

        except Exception as e:
            logger.error(f"STL分解失败: {e}")
            import traceback

            logger.error(f"STL分解详细错误: {traceback.format_exc()}")
            return {"error": str(e)}

    def get_filter_options(self):
        """获取筛选选项（企业、行业、问题分类）"""
        try:
            if self._data_cache is None or self._data_cache.empty:
                return {
                    "companies": [],
                    "industry_level1": [],
                    "industry_level2": [],
                    "industry_classification": [],
                    "categories": [],
                }

            companies = []
            industry_level1 = []  # 行业名称(1) - 大类
            industry_level2 = []  # 行业名称(2) - 中类
            industry_classification = []  # 行业分类 - 详细分类
            categories = []

            # 获取企业列表（包含空值选项）
            if "企业名称" in self._data_cache.columns:
                # 获取所有非空企业名称
                non_null_companies = (
                    self._data_cache["企业名称"].dropna().unique().tolist()
                )
                companies.extend(sorted(non_null_companies))

                # 检查是否有空值，如果有则添加空值选项
                null_count = self._data_cache["企业名称"].isnull().sum()
                if null_count > 0:
                    companies.append(f"[空值] ({null_count}条记录)")

            # 获取行业大类（行业名称1）
            if "行业名称(1)" in self._data_cache.columns:
                non_null_level1 = (
                    self._data_cache["行业名称(1)"].dropna().unique().tolist()
                )
                industry_level1.extend(sorted(non_null_level1))

                null_count = self._data_cache["行业名称(1)"].isnull().sum()
                if null_count > 0:
                    industry_level1.append(f"[空值] ({null_count}条记录)")

            # 获取行业中类（行业名称2）
            if "行业名称(2)" in self._data_cache.columns:
                non_null_level2 = (
                    self._data_cache["行业名称(2)"].dropna().unique().tolist()
                )
                industry_level2.extend(sorted(non_null_level2))

                null_count = self._data_cache["行业名称(2)"].isnull().sum()
                if null_count > 0:
                    industry_level2.append(f"[空值] ({null_count}条记录)")

            # 获取详细行业分类
            if "行业分类" in self._data_cache.columns:
                non_null_classification = (
                    self._data_cache["行业分类"].dropna().unique().tolist()
                )
                industry_classification.extend(sorted(non_null_classification))

                null_count = self._data_cache["行业分类"].isnull().sum()
                if null_count > 0:
                    industry_classification.append(f"[空值] ({null_count}条记录)")

            # 获取问题分类列表（包含空值选项）
            if "问题分类" in self._data_cache.columns:
                non_null_categories = (
                    self._data_cache["问题分类"].dropna().unique().tolist()
                )
                categories.extend(sorted(non_null_categories))

                null_count = self._data_cache["问题分类"].isnull().sum()
                if null_count > 0:
                    categories.append(f"[空值] ({null_count}条记录)")

            logger.info(
                f"筛选选项统计: 企业数={len(companies)}, 行业大类={len(industry_level1)}, 行业中类={len(industry_level2)}, 详细行业分类={len(industry_classification)}, 问题分类数={len(categories)}"
            )

            return {
                "companies": companies,  # 显示全部值，不截断
                "industry_level1": industry_level1,  # 行业大类
                "industry_level2": industry_level2,  # 行业中类
                "industry_classification": industry_classification,  # 详细行业分类
                "categories": categories,
            }

        except Exception as e:
            logger.error(f"获取筛选选项失败: {e}")
            return {
                "companies": [],
                "industry_level1": [],
                "industry_level2": [],
                "industry_classification": [],
                "categories": [],
            }

    def get_dashboard_stats(
        self,
        start_date=None,
        end_date=None,
        companies=None,
        industries=None,
        categories=None,
        industry_level1=None,
        industry_level2=None,
    ):
        """获取仪表板统计数据"""
        try:
            filtered_data = self._get_filtered_data_enhanced(
                start_date,
                end_date,
                companies,
                industries,
                categories,
                industry_level1,
                industry_level2,
            )

            if filtered_data.empty:
                logger.warning("筛选后数据为空")
                return {
                    "total_complaints": 0,
                    "companies_count": 0,
                    "industries_count": 0,
                    "repeat_companies_count": 0,
                    "company_ranking": [],
                    "date_range": {},
                }

            logger.info(f"筛选后数据量: {len(filtered_data)} 条")

            # 基础统计
            total_complaints = len(filtered_data)

            # 涉及企业数
            companies_count = 0
            if "企业名称" in filtered_data.columns:
                companies_count = filtered_data["企业名称"].nunique()

            # 涉及行业数
            industries_count = 0
            if "行业分类" in filtered_data.columns:
                industries_count = filtered_data["行业分类"].nunique()

            # 月内重复投诉企业数
            repeat_companies_count = 0
            if "企业名称" in filtered_data.columns and "日期" in filtered_data.columns:
                try:
                    # 按企业和月份分组，统计每个企业每月的投诉次数
                    filtered_data_copy = filtered_data.copy()
                    # 确保日期字段是datetime类型
                    filtered_data_copy["日期"] = pd.to_datetime(
                        filtered_data_copy["日期"]
                    )
                    filtered_data_copy["年月"] = filtered_data_copy[
                        "日期"
                    ].dt.to_period("M")
                    monthly_complaints = filtered_data_copy.groupby(
                        ["企业名称", "年月"]
                    ).size()
                    # 找出在任何月份有多次投诉的企业
                    repeat_companies = (
                        monthly_complaints[monthly_complaints > 1]
                        .groupby("企业名称")
                        .size()
                    )
                    repeat_companies_count = len(repeat_companies)
                except Exception as e:
                    logger.error(f"计算月内重复投诉企业数失败: {e}")
                    repeat_companies_count = 0

            # 企业投诉量排名（前10名）
            company_ranking = []
            if "企业名称" in filtered_data.columns:
                company_stats = filtered_data["企业名称"].value_counts().head(10)
                for company, count in company_stats.items():
                    company_ranking.append({"name": company, "count": int(count)})

            # 时间范围
            date_range = {}
            if "日期" in filtered_data.columns:
                date_range = {
                    "start": str(filtered_data["日期"].min()),
                    "end": str(filtered_data["日期"].max()),
                }

            return {
                "total_complaints": total_complaints,
                "companies_count": companies_count,
                "industries_count": industries_count,
                "repeat_companies_count": repeat_companies_count,
                "company_ranking": company_ranking,
                "date_range": date_range,
            }

        except Exception as e:
            logger.error(f"获取仪表板统计失败: {e}")
            return {"error": str(e)}

    def get_trend_data(
        self,
        start_date=None,
        end_date=None,
        period="day",
        companies=None,
        industries=None,
        categories=None,
        industry_level1=None,
        industry_level2=None,
    ):
        """获取投诉趋势数据"""
        try:
            filtered_data = self._get_filtered_data_enhanced(
                start_date,
                end_date,
                companies,
                industries,
                categories,
                industry_level1,
                industry_level2,
            )

            if filtered_data.empty or "日期" not in filtered_data.columns:
                return {"error": "没有有效的时间数据"}

            # 根据period参数选择时间粒度
            if period == "day":
                # 按天统计
                try:
                    trend_data = (
                        filtered_data.groupby("日期")
                        .size()
                        .reset_index(name="投诉数量")
                    )
                    # 确保日期字段是datetime类型再使用.dt访问器
                    if not pd.api.types.is_datetime64_any_dtype(trend_data["日期"]):
                        trend_data["日期"] = pd.to_datetime(trend_data["日期"])
                    trend_data["时间"] = trend_data["日期"].dt.strftime("%Y-%m-%d")
                except Exception as e:
                    logger.error(f"按天统计失败: {e}")
                    return {"error": f"按天统计失败: {str(e)}"}
            elif period == "week":
                # 按周统计
                try:
                    filtered_data_copy = filtered_data.copy()
                    # 将日期转换为datetime以便使用.dt访问器
                    filtered_data_copy["日期"] = pd.to_datetime(
                        filtered_data_copy["日期"]
                    )
                    filtered_data_copy["周"] = filtered_data_copy["日期"].dt.to_period(
                        "W"
                    )
                    trend_data = (
                        filtered_data_copy.groupby("周")
                        .size()
                        .reset_index(name="投诉数量")
                    )
                    trend_data["时间"] = trend_data["周"].dt.strftime("%Y年第%U周")
                except Exception as e:
                    logger.error(f"按周统计失败: {e}")
                    return {"error": f"按周统计失败: {str(e)}"}
            elif period == "month":
                # 按月统计
                try:
                    filtered_data_copy = filtered_data.copy()
                    # 将日期转换为datetime以便使用.dt访问器
                    filtered_data_copy["日期"] = pd.to_datetime(
                        filtered_data_copy["日期"]
                    )
                    filtered_data_copy["月份"] = filtered_data_copy[
                        "日期"
                    ].dt.to_period("M")
                    trend_data = (
                        filtered_data_copy.groupby("月份")
                        .size()
                        .reset_index(name="投诉数量")
                    )
                    trend_data["时间"] = trend_data["月份"].dt.strftime("%Y年%m月")
                except Exception as e:
                    logger.error(f"按月统计失败: {e}")
                    return {"error": f"按月统计失败: {str(e)}"}
            else:
                return {"error": "不支持的时间粒度"}

            # 转换为字典格式
            result = []
            for _, row in trend_data.iterrows():
                result.append({"time": row["时间"], "count": int(row["投诉数量"])})

            return {"period": period, "data": result}

        except Exception as e:
            logger.error(f"获取趋势数据失败: {e}")
            return {"error": str(e)}

    def generate_report(self, start_date=None, end_date=None, entity_field="企业名称"):
        """生成分析报告"""
        try:
            filtered_data = self._get_filtered_data(start_date, end_date)

            if filtered_data.empty:
                return {"error": "没有数据可供生成报告"}

            # 基础统计
            total_complaints = len(filtered_data)

            # 时间分析
            time_analysis = {}
            if "日期" in filtered_data.columns:
                daily_counts = filtered_data.groupby("日期").size()
                time_analysis = {
                    "daily_avg": float(daily_counts.mean()),
                    "daily_max": int(daily_counts.max()),
                    "daily_min": int(daily_counts.min()),
                    "date_range": {
                        "start": str(filtered_data["日期"].min()),
                        "end": str(filtered_data["日期"].max()),
                    },
                }

            # 实体分析
            entity_analysis = {}
            if entity_field in filtered_data.columns:
                top_entities = filtered_data[entity_field].value_counts().head(10)
                entity_analysis = {
                    "top_entities": top_entities.to_dict(),
                    "unique_count": filtered_data[entity_field].nunique(),
                }

            # 生成报告内容
            report_content = {
                "summary": {
                    "total_complaints": total_complaints,
                    "analysis_period": f"{start_date or '开始'} 至 {end_date or '结束'}",
                },
                "time_analysis": time_analysis,
                "entity_analysis": entity_analysis,
                "generated_at": datetime.now().isoformat(),
            }

            return {
                "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "title": "工商投诉数据分析报告",
                "content": report_content,
            }

        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {"error": str(e)}
