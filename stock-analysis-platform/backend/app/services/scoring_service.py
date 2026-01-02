# backend/app/services/scoring_service.py
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """评分权重配置"""
    capital: float = 0.40  # 资金面权重
    technical: float = 0.30  # 技术面权重
    fundamental: float = 0.20  # 基本面权重
    risk: float = 0.10  # 风险面权重


class StockScoringModel:
    """股票综合评分模型"""

    def __init__(self, db: Session, weights: ScoringWeights = None):
        self.db = db
        self.weights = weights or ScoringWeights()

    def score_stock(self, stock_code: str, trade_date: str) -> Dict:
        """
        对股票进行综合评分
        """
        # 1. 资金面评分
        capital_score = self._calculate_capital_score(stock_code, trade_date)

        # 2. 技术面评分
        technical_score = self._calculate_technical_score(stock_code, trade_date)

        # 3. 基本面评分（基于板块）
        fundamental_score = self._calculate_fundamental_score(stock_code, trade_date)

        # 4. 风险面评分
        risk_score = self._calculate_risk_score(stock_code, trade_date)

        # 5. 计算总分
        total_score = (
                capital_score * self.weights.capital +
                technical_score * self.weights.technical +
                fundamental_score * self.weights.fundamental +
                risk_score * self.weights.risk
        )

        # 6. 生成买卖信号
        signal = self._generate_signal(total_score, capital_score, technical_score)

        return {
            'stock_code': stock_code,
            'trade_date': trade_date,
            'scores': {
                'capital': round(capital_score, 2),
                'technical': round(technical_score, 2),
                'fundamental': round(fundamental_score, 2),
                'risk': round(risk_score, 2),
                'total': round(total_score, 2)
            },
            'weights': {
                'capital': self.weights.capital,
                'technical': self.weights.technical,
                'fundamental': self.weights.fundamental,
                'risk': self.weights.risk
            },
            'signal': signal,
            'analysis': self._generate_analysis(
                capital_score, technical_score, fundamental_score, risk_score
            )
        }

    def _calculate_capital_score(self, stock_code: str, trade_date: str) -> float:
        """计算资金面评分"""
        # 获取资金流向数据
        query = """
        SELECT 
            net_inflow,
            inflow_ratio,
            large_net_inflow,
            large_inflow_ratio,
            total_amount,
            (SELECT COUNT(*) FROM stock_price_distribution 
             WHERE stock_code = :stock_code 
               AND trade_date BETWEEN DATE_SUB(:date, INTERVAL 5 DAY) AND :date
               AND net_inflow > 0) as positive_days
        FROM stock_price_distribution
        WHERE stock_code = :stock_code 
          AND trade_date = :date
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'date': trade_date
        }).fetchone()

        if not result:
            return 50.0  # 默认中间分

        score = 50.0  # 基础分

        # 1. 净流入评分 (0-25分)
        if result.net_inflow > 0:
            score += min(result.inflow_ratio * 2, 25)

        # 2. 大单净流入评分 (0-25分)
        if result.large_net_inflow > 0:
            score += min(result.large_inflow_ratio * 2, 25)

        # 3. 持续性评分 (0-20分)
        continuity_score = min(result.positive_days * 4, 20)
        score += continuity_score

        # 4. 资金规模调整 (-10到+10分)
        amount_adjust = min(np.log10(max(result.total_amount, 1)) - 6, 10)
        score += amount_adjust

        return min(max(score, 0), 100)

    def _calculate_technical_score(self, stock_code: str, trade_date: str) -> float:
        """计算技术面评分"""
        # 获取技术指标数据
        query = """
        SELECT 
            close_price,
            ma5, ma20, ma60,
            volume, vma5, vma20,
            change_pct,
            amplitude,
            turnover_rate
        FROM stock_day_data
        WHERE stock_code = :stock_code 
          AND trade_date = :date
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'date': trade_date
        }).fetchone()

        if not result:
            return 50.0

        score = 50.0

        # 1. 均线排列评分 (0-30分)
        ma_score = 0
        if result.ma5 and result.ma20 and result.ma60:
            if result.ma5 > result.ma20 > result.ma60:
                ma_score = 30
            elif result.ma5 > result.ma20:
                ma_score = 20
            elif result.close_price > result.ma5:
                ma_score = 10

        score += ma_score

        # 2. 量价配合评分 (0-20分)
        if result.volume and result.vma5:
            volume_ratio = result.volume / result.vma5 if result.vma5 > 0 else 1
            if result.change_pct > 0 and volume_ratio > 1.2:
                score += 20
            elif result.change_pct > 0 and volume_ratio > 1.0:
                score += 10

        # 3. 趋势强度评分 (0-15分)
        if result.ma5 and result.ma20:
            trend_strength = abs((result.ma5 - result.ma20) / result.ma20 * 100)
            score += min(trend_strength, 15)

        # 4. 超买超卖调整 (-10到+10分)
        # 简单的RSI替代计算
        if result.change_pct:
            if result.change_pct > 9:  # 接近涨停
                score -= 10
            elif result.change_pct < -9:  # 接近跌停
                score += 5  # 超卖可能反弹

        return min(max(score, 0), 100)

    def _calculate_fundamental_score(self, stock_code: str, trade_date: str) -> float:
        """计算基本面评分（基于板块）"""
        # 获取板块信息
        query = """
        SELECT 
            b.block_code,
            b.block_name,
            b.block_type,
            bc.inflow_ratio,
            bc.ranking,
            bc.continuity_days
        FROM stock_block_membership b
        LEFT JOIN block_capital_flow bc 
            ON b.block_code = bc.block_code 
            AND bc.trade_date = :date
        WHERE b.stock_code = :stock_code
        LIMIT 1
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'date': trade_date
        }).fetchone()

        if not result:
            return 50.0

        score = 50.0

        # 1. 板块资金流入评分 (0-25分)
        if result.inflow_ratio:
            score += min(result.inflow_ratio * 5, 25)

        # 2. 板块排名评分 (0-20分)
        if result.ranking:
            rank_score = max(0, 20 - result.ranking / 5)
            score += rank_score

        # 3. 板块持续性评分 (0-15分)
        if result.continuity_days:
            score += min(result.continuity_days * 3, 15)

        # 4. 板块类型调整 (-10到+10分)
        if result.block_type == 'concept':  # 概念板块波动大
            score += 5
        elif result.block_type == 'industry':  # 行业板块相对稳定
            score += 10

        return min(max(score, 0), 100)

    def _calculate_risk_score(self, stock_code: str, trade_date: str) -> float:
        """计算风险面评分（越高表示风险越低）"""
        # 获取风险指标
        query = """
        SELECT 
            amplitude,
            turnover_rate,
            total_amount,
            (SELECT STD(change_pct) 
             FROM stock_day_data 
             WHERE stock_code = :stock_code 
               AND trade_date BETWEEN DATE_SUB(:date, INTERVAL 20 DAY) AND :date) as volatility_20d
        FROM stock_day_data
        WHERE stock_code = :stock_code 
          AND trade_date = :date
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'date': trade_date
        }).fetchone()

        if not result:
            return 50.0

        score = 100.0  # 从100开始扣分

        # 1. 波动率扣分 (0-30分)
        if result.amplitude:
            if result.amplitude > 10:
                score -= 30
            elif result.amplitude > 7:
                score -= 20
            elif result.amplitude > 5:
                score -= 10

        # 2. 换手率扣分 (0-25分)
        if result.turnover_rate:
            if result.turnover_rate > 20:
                score -= 25
            elif result.turnover_rate > 10:
                score -= 15
            elif result.turnover_rate > 5:
                score -= 5

        # 3. 流动性扣分 (0-20分)
        if result.total_amount:
            if result.total_amount < 10000000:  # 1000万
                score -= 20
            elif result.total_amount < 50000000:  # 5000万
                score -= 10

        # 4. 历史波动率扣分 (0-15分)
        if result.volatility_20d:
            if result.volatility_20d > 3:
                score -= 15
            elif result.volatility_20d > 2:
                score -= 10

        return min(max(score, 0), 100)

    def _generate_signal(self, total_score: float,
                         capital_score: float,
                         technical_score: float) -> Dict:
        """生成买卖信号"""
        signal_types = {
            'strong_buy': (80, 100),
            'buy': (70, 80),
            'watch': (60, 70),
            'hold': (50, 60),
            'reduce': (40, 50),
            'sell': (30, 40),
            'strong_sell': (0, 30)
        }

        # 确定信号类型
        signal_type = 'hold'
        for sig, (low, high) in signal_types.items():
            if low <= total_score < high:
                signal_type = sig
                break

        # 计算信号强度
        strength = 0
        if signal_type in ['strong_buy', 'strong_sell']:
            strength = 3
        elif signal_type in ['buy', 'sell']:
            strength = 2
        elif signal_type in ['watch', 'reduce']:
            strength = 1

        # 考虑资金和技术面的协调性
        coordination = abs(capital_score - technical_score) / 100
        if coordination > 0.3:  # 不协调
            strength = max(0, strength - 1)

        return {
            'type': signal_type,
            'strength': strength,
            'confidence': min(100, total_score),
            'description': self._get_signal_description(signal_type, strength)
        }

    def _generate_analysis(self, capital_score: float,
                           technical_score: float,
                           fundamental_score: float,
                           risk_score: float) -> Dict:
        """生成分析摘要"""
        strengths = []
        weaknesses = []

        # 分析优势
        if capital_score >= 70:
            strengths.append("资金面强劲，主力资金持续流入")
        elif capital_score >= 60:
            strengths.append("资金面良好，有资金关注")

        if technical_score >= 70:
            strengths.append("技术形态良好，趋势向上")
        elif technical_score >= 60:
            strengths.append("技术面稳健，处于上升通道")

        if fundamental_score >= 70:
            strengths.append("板块效应明显，属于热点板块")

        if risk_score >= 80:
            strengths.append("风险控制良好，波动性较低")

        # 分析劣势
        if capital_score <= 40:
            weaknesses.append("资金面疲弱，主力资金流出")

        if technical_score <= 40:
            weaknesses.append("技术形态走弱，存在下行风险")

        if risk_score <= 40:
            weaknesses.append("风险较高，波动性较大")

        return {
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendation': self._generate_recommendation(
                capital_score, technical_score, risk_score
            ),
            'key_considerations': self._get_key_considerations(
                capital_score, technical_score, fundamental_score, risk_score
            )
        }