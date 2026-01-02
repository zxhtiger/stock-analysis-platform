# backend/app/utils/data_processor.py
import json
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class DataProcessor:
    """数据处理工具"""

    @staticmethod
    def parse_price_distribution(price_distribution_json: str) -> Optional[Dict]:
        """解析价格分布JSON数据"""
        try:
            data = json.loads(price_distribution_json)
            return {
                "prices": np.array(data.get("p", [])),
                "buy_volumes": np.array(data.get("bv", [])),
                "sell_volumes": np.array(data.get("sv", [])),
                "buy_amounts": np.array(data.get("ba", [])),
                "sell_amounts": np.array(data.get("sa", []))
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析价格分布数据失败: {e}")
            return None

    @staticmethod
    def calculate_vwap(prices: np.ndarray, volumes: np.ndarray) -> float:
        """计算VWAP（成交量加权平均价）"""
        if len(prices) == 0 or len(volumes) == 0:
            return 0.0

        total_value = np.sum(prices * volumes)
        total_volume = np.sum(volumes)

        if total_volume == 0:
            return 0.0

        return float(total_value / total_volume)

    @staticmethod
    def calculate_price_metrics(prices: np.ndarray) -> Dict:
        """计算价格相关指标"""
        if len(prices) == 0:
            return {}

        return {
            "mean": float(np.mean(prices)),
            "median": float(np.median(prices)),
            "std": float(np.std(prices)),
            "min": float(np.min(prices)),
            "max": float(np.max(prices)),
            "range": float(np.max(prices) - np.min(prices)),
            "cv": float(np.std(prices) / np.mean(prices) if np.mean(prices) != 0 else 0)  # 变异系数
        }

    @staticmethod
    def calculate_cost_pressure(buy_vwap: float, sell_vwap: float, current_price: float) -> float:
        """计算成本压力指数"""
        if current_price == 0:
            return 0.0

        # 成本压力 = (买方成本 - 卖方成本) / 当前价格 * 100
        pressure = (buy_vwap - sell_vwap) / current_price * 100
        return float(pressure)

    @staticmethod
    def normalize_data(data: List[float], method: str = "minmax") -> List[float]:
        """数据归一化"""
        if not data:
            return []

        data_array = np.array(data)

        if method == "minmax":
            min_val = np.min(data_array)
            max_val = np.max(data_array)
            if max_val == min_val:
                return [0.5] * len(data)
            return ((data_array - min_val) / (max_val - min_val)).tolist()

        elif method == "zscore":
            mean_val = np.mean(data_array)
            std_val = np.std(data_array)
            if std_val == 0:
                return [0] * len(data)
            return ((data_array - mean_val) / std_val).tolist()

        else:
            return data

    @staticmethod
    def calculate_correlation(x: List[float], y: List[float]) -> float:
        """计算相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        x_array = np.array(x)
        y_array = np.array(y)

        correlation = np.corrcoef(x_array, y_array)[0, 1]
        return float(correlation) if not np.isnan(correlation) else 0.0

    @staticmethod
    def detect_anomalies(data: List[float], threshold: float = 3) -> List[bool]:
        """检测异常值"""
        if len(data) < 3:
            return [False] * len(data)

        data_array = np.array(data)
        mean_val = np.mean(data_array)
        std_val = np.std(data_array)

        if std_val == 0:
            return [False] * len(data)

        z_scores = np.abs((data_array - mean_val) / std_val)
        return (z_scores > threshold).tolist()

    @staticmethod
    def fill_missing_values(data: List[Optional[float]], method: str = "linear") -> List[float]:
        """填充缺失值"""
        if not data:
            return []

        data_array = np.array(data, dtype=float)
        mask = np.isnan(data_array)

        if not mask.any():
            return data_array.tolist()

        if method == "linear":
            # 线性插值
            indices = np.arange(len(data_array))
            data_array[mask] = np.interp(indices[mask], indices[~mask], data_array[~mask])
        elif method == "forward":
            # 前向填充
            data_array = pd.Series(data_array).ffill().values
        elif method == "backward":
            # 后向填充
            data_array = pd.Series(data_array).bfill().values
        elif method == "mean":
            # 均值填充
            mean_val = np.nanmean(data_array)
            data_array[mask] = mean_val

        return data_array.tolist()