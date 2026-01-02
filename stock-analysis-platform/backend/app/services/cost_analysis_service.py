# backend/app/services/cost_analysis_service.py
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class HoldingCostAnalysis:
    """持股成本分析服务"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_holding_cost(self, stock_code: str,
                             lookback_days: int = 60) -> Dict:
        """
        分析持股成本
        """
        # 获取价格分布数据
        query = """
        SELECT 
            trade_date,
            price_distribution,
            total_buy_amount,
            total_sell_amount,
            total_buy_volume,
            total_sell_volume
        FROM stock_price_distribution
        WHERE stock_code = :stock_code
          AND trade_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        ORDER BY trade_date DESC
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'days': lookback_days
        }).fetchall()

        if not result:
            return {}

        # 解析价格分布数据并计算成本指标
        cost_analyses = []
        for row in result:
            analysis = self._analyze_daily_cost(row)
            analysis['date'] = str(row.trade_date)
            cost_analyses.append(analysis)

        # 计算多日平均成本
        multi_day_costs = self._calculate_multi_day_cost(cost_analyses)

        # 生成持股成本报告
        report = {
            'stock_code': stock_code,
            'analysis_days': lookback_days,
            'latest_cost': cost_analyses[0] if cost_analyses else {},
            'cost_history': cost_analyses,
            'multi_day_averages': multi_day_costs,
            'cost_trend_analysis': self._analyze_cost_trend(cost_analyses),
            'support_resistance_levels': self._find_cost_levels(cost_analyses)
        }

        return report

    def _analyze_daily_cost(self, row) -> Dict:
        """分析单日持股成本"""
        try:
            price_data = json.loads(row.price_distribution)

            prices = np.array(price_data['p'])
            buy_volumes = np.array(price_data['bv'])
            sell_volumes = np.array(price_data['sv'])
            buy_amounts = np.array(price_data['ba'])
            sell_amounts = np.array(price_data['sa'])

            # 计算买方VWAP
            total_buy_amount = np.sum(buy_amounts)
            total_buy_volume = np.sum(buy_volumes)
            buy_vwap = total_buy_amount / total_buy_volume if total_buy_volume > 0 else 0

            # 计算卖方VWAP
            total_sell_amount = np.sum(sell_amounts)
            total_sell_volume = np.sum(sell_volumes)
            sell_vwap = total_sell_amount / total_sell_volume if total_sell_volume > 0 else 0

            # 计算中位数和相关指标
            price_median = np.median(prices)
            buy_median_diff = buy_vwap - price_median
            sell_median_diff = sell_vwap - price_median

            # 计算成本压力指标
            cost_pressure = (buy_vwap - sell_vwap) / price_median * 100 if price_median > 0 else 0

            # 计算成本集中度
            cost_concentration = self._calculate_cost_concentration(
                prices, buy_volumes, sell_volumes
            )

            return {
                'buy_vwap': float(buy_vwap),
                'sell_vwap': float(sell_vwap),
                'vwap_spread': float(buy_vwap - sell_vwap),
                'price_median': float(price_median),
                'buy_median_diff': float(buy_median_diff),
                'sell_median_diff': float(sell_median_diff),
                'cost_pressure': float(cost_pressure),
                'cost_concentration': cost_concentration,
                'total_buy_amount': float(row.total_buy_amount),
                'total_sell_amount': float(row.total_sell_amount)
            }

        except Exception as e:
            print(f"Error analyzing daily cost: {e}")
            return {}

    def _calculate_cost_concentration(self, prices, buy_volumes, sell_volumes) -> Dict:
        """计算成本集中度"""
        total_volume = np.sum(buy_volumes) + np.sum(sell_volumes)

        if total_volume == 0:
            return {
                'top20_price_range': 0,
                'volume_concentration': 0,
                'price_dispersion': 0
            }

        # 计算价格区间集中度
        price_min = np.min(prices)
        price_max = np.max(prices)
        price_range = price_max - price_min

        # 计算成交量在价格上的分布
        price_levels = 10
        volume_by_level = np.zeros(price_levels)

        for price, buy_vol, sell_vol in zip(prices, buy_volumes, sell_volumes):
            if price_range > 0:
                level = int((price - price_min) / price_range * (price_levels - 1))
                level = min(level, price_levels - 1)
                volume_by_level[level] += buy_vol + sell_vol

        # 计算前20%价格区间的成交量占比
        sorted_indices = np.argsort(volume_by_level)[::-1]
        top20_count = max(1, price_levels // 5)
        top20_volume = np.sum(volume_by_level[sorted_indices[:top20_count]])

        return {
            'top20_price_range': top20_count / price_levels,
            'volume_concentration': top20_volume / total_volume,
            'price_dispersion': price_range / np.mean(prices) if np.mean(prices) > 0 else 0
        }

    def _calculate_multi_day_cost(self, daily_analyses: List[Dict]) -> Dict:
        """计算多日平均成本"""
        if not daily_analyses:
            return {}

        # 按时间窗口计算平均成本
        windows = [2, 5, 20, 60]
        results = {}

        for window in windows:
            if len(daily_analyses) >= window:
                window_data = daily_analyses[:window]

                results[f'{window}d'] = {
                    'avg_buy_vwap': np.mean([d['buy_vwap'] for d in window_data]),
                    'avg_sell_vwap': np.mean([d['sell_vwap'] for d in window_data]),
                    'avg_cost_pressure': np.mean([d['cost_pressure'] for d in window_data]),
                    'cost_trend': self._determine_cost_trend(
                        [d['buy_vwap'] for d in window_data]
                    )
                }

        return results

    def _determine_cost_trend(self, cost_history: List[float]) -> str:
        """确定成本趋势"""
        if len(cost_history) < 2:
            return 'stable'

        # 使用线性回归判断趋势
        x = np.arange(len(cost_history))
        y = np.array(cost_history)

        try:
            slope = np.polyfit(x, y, 1)[0]
            r_squared = self._calculate_r_squared(x, y)

            if r_squared > 0.5:  # 趋势明显
                if slope > 0.01:
                    return 'rising'
                elif slope < -0.01:
                    return 'falling'

            return 'stable'
        except:
            return 'stable'

    def _calculate_r_squared(self, x, y):
        """计算R平方值"""
        if len(x) < 2:
            return 0

        try:
            coeffs = np.polyfit(x, y, 1)
            p = np.poly1d(coeffs)
            yhat = p(x)
            ybar = np.sum(y) / len(y)
            ssreg = np.sum((yhat - ybar) ** 2)
            sstot = np.sum((y - ybar) ** 2)
            return ssreg / sstot if sstot != 0 else 0
        except:
            return 0

    def _analyze_cost_trend(self, cost_history: List[Dict]) -> Dict:
        """分析成本趋势"""
        if len(cost_history) < 5:
            return {'trend': 'insufficient_data'}

        buy_vwaps = [d['buy_vwap'] for d in cost_history]
        cost_pressures = [d['cost_pressure'] for d in cost_history]

        # 计算趋势指标
        trend_strength = self._calculate_trend_strength(buy_vwaps)
        pressure_trend = self._calculate_trend_strength(cost_pressures)

        return {
            'buy_cost_trend': self._determine_trend_direction(buy_vwaps),
            'trend_strength': trend_strength,
            'pressure_trend': pressure_trend,
            'reversal_signals': self._detect_reversal_signals(buy_vwaps),
            'support_levels': self._find_support_levels(buy_vwaps)
        }

    def _find_cost_levels(self, cost_history: List[Dict]) -> List[Dict]:
        """找出重要的成本支撑位和阻力位"""
        if not cost_history:
            return []

        # 使用聚类方法找出成本密集区
        from sklearn.cluster import KMeans

        buy_costs = [d['buy_vwap'] for d in cost_history]
        volumes = [d.get('total_buy_amount', 1) for d in cost_history]

        if len(buy_costs) < 3:
            return []

        # 准备数据
        X = np.array(buy_costs).reshape(-1, 1)

        # 确定最佳聚类数
        n_clusters = min(3, len(set(buy_costs)))

        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(X)

            # 计算每个簇的中心和权重
            levels = []
            for i in range(n_clusters):
                cluster_points = X[clusters == i]
                cluster_volumes = [volumes[j] for j in range(len(volumes)) if clusters[j] == i]

                if len(cluster_points) > 0:
                    center = float(np.mean(cluster_points))
                    weight = len(cluster_points) / len(X)
                    volume_weight = sum(cluster_volumes) / sum(volumes) if sum(volumes) > 0 else 0

                    levels.append({
                        'price_level': center,
                        'frequency_weight': weight,
                        'volume_weight': volume_weight,
                        'sample_count': len(cluster_points),
                        'type': 'support' if i == np.argmin(kmeans.cluster_centers_) else 'resistance'
                    })

            return sorted(levels, key=lambda x: x['price_level'])

        except Exception as e:
            print(f"Error finding cost levels: {e}")
            return []