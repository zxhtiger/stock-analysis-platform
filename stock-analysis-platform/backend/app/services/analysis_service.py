# backend/app/services/analysis_service.py
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_


class CapitalFlowAnalysis:
    """资金流向分析服务"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_block_capital_flow(self, trade_date: str,
                                     days: int = 7) -> List[Dict]:
        """
        计算板块资金流向
        """
        # 获取指定日期的板块资金数据
        query = """
        SELECT 
            b.block_code,
            b.block_name,
            b.block_type,
            DATE_FORMAT(p.trade_date, '%Y-%m-%d') as trade_date,
            SUM(p.total_buy_amount) as total_buy,
            SUM(p.total_sell_amount) as total_sell,
            SUM(p.net_inflow) as net_inflow,
            SUM(p.total_amount) as total_amount,
            COUNT(DISTINCT p.stock_code) as stock_count,
            SUM(CASE WHEN p.net_inflow > 0 THEN 1 ELSE 0 END) as inflow_stocks
        FROM stock_block_membership b
        INNER JOIN stock_price_distribution p 
            ON b.stock_code = p.stock_code
        WHERE p.trade_date BETWEEN :start_date AND :end_date
        GROUP BY b.block_code, b.block_name, b.block_type, p.trade_date
        ORDER BY net_inflow DESC
        """

        start_date = (datetime.strptime(trade_date, '%Y-%m-%d') -
                      timedelta(days=days - 1)).strftime('%Y-%m-%d')

        result = self.db.execute(query, {
            'start_date': start_date,
            'end_date': trade_date
        }).fetchall()

        # 计算流入比例和连续天数
        blocks = {}
        for row in result:
            block_code = row.block_code
            if block_code not in blocks:
                blocks[block_code] = {
                    'block_code': block_code,
                    'block_name': row.block_name,
                    'block_type': row.block_type,
                    'daily_flows': []
                }

            inflow_ratio = (row.net_inflow / row.total_amount * 100
                            if row.total_amount > 0 else 0)

            blocks[block_code]['daily_flows'].append({
                'date': row.trade_date,
                'net_inflow': float(row.net_inflow),
                'inflow_ratio': float(inflow_ratio),
                'total_amount': float(row.total_amount),
                'stock_count': row.stock_count,
                'inflow_stocks': row.inflow_stocks
            })

        # 计算连续净流入天数
        final_results = []
        for block_data in blocks.values():
            flows = sorted(block_data['daily_flows'], key=lambda x: x['date'])

            # 计算连续净流入天数
            continuity = 0
            for flow in reversed(flows):
                if flow['net_inflow'] > 0:
                    continuity += 1
                else:
                    break

            # 计算平均流入比例
            avg_inflow_ratio = np.mean([f['inflow_ratio'] for f in flows])

            final_results.append({
                **block_data,
                'continuity_days': continuity,
                'avg_inflow_ratio': avg_inflow_ratio,
                'latest_flow': flows[-1] if flows else None
            })

        # 按流入比例排序
        final_results.sort(key=lambda x: x['avg_inflow_ratio'], reverse=True)

        return final_results[:20]

    def analyze_stock_capital_flow(self, stock_code: str,
                                   start_date: str, end_date: str) -> Dict:
        """
        分析个股资金流向
        """
        query = """
        SELECT 
            trade_date,
            total_buy_amount,
            total_sell_amount,
            net_inflow,
            inflow_ratio,
            large_net_inflow,
            large_inflow_ratio,
            total_amount
        FROM stock_price_distribution
        WHERE stock_code = :stock_code 
          AND trade_date BETWEEN :start_date AND :end_date
        ORDER BY trade_date
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        if not result:
            return {}

        # 计算资金流向指标
        dates = [r.trade_date for r in result]
        net_inflows = [float(r.net_inflow) for r in result]
        inflow_ratios = [float(r.inflow_ratio) for r in result]

        analysis = {
            'stock_code': stock_code,
            'analysis_period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_net_inflow': sum(net_inflows),
            'avg_daily_inflow': np.mean(net_inflows),
            'max_inflow': max(net_inflows),
            'min_inflow': min(net_inflows),
            'inflow_continuity': self._calculate_continuity(net_inflows),
            'inflow_stability': self._calculate_stability(net_inflows),
            'recent_trend': self._analyze_trend(net_inflows[-5:]),
            'daily_details': [
                {
                    'date': str(r.trade_date),
                    'net_inflow': float(r.net_inflow),
                    'inflow_ratio': float(r.inflow_ratio),
                    'large_net_inflow': float(r.large_net_inflow),
                    'total_amount': float(r.total_amount)
                }
                for r in result
            ]
        }

        return analysis

    def _calculate_continuity(self, flows: List[float]) -> Dict:
        """计算连续性指标"""
        positive_days = sum(1 for f in flows if f > 0)
        negative_days = sum(1 for f in flows if f < 0)

        return {
            'positive_days': positive_days,
            'negative_days': negative_days,
            'continuity_score': positive_days / len(flows) if flows else 0
        }

    def _calculate_stability(self, flows: List[float]) -> float:
        """计算稳定性指标"""
        if len(flows) < 2:
            return 1.0

        mean = np.mean(flows)
        std = np.std(flows)

        return 1 - (std / abs(mean)) if mean != 0 else 1.0

    def _analyze_trend(self, recent_flows: List[float]) -> str:
        """分析近期趋势"""
        if len(recent_flows) < 2:
            return 'stable'

        # 线性回归判断趋势
        x = np.arange(len(recent_flows))
        y = np.array(recent_flows)

        try:
            slope = np.polyfit(x, y, 1)[0]
            if slope > 0.1:
                return 'improving'
            elif slope < -0.1:
                return 'deteriorating'
            else:
                return 'stable'
        except:
            return 'stable'