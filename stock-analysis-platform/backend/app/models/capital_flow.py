# backend/app/models/capital_flow.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, Enum
from sqlalchemy.dialects.mysql import BIGINT, DECIMAL
import enum

from app.core.database import Base


class BlockCapitalFlow(Base):
    """板块资金流向模型"""
    __tablename__ = "block_capital_flow"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, comment="交易日期")
    block_code = Column(String(6), nullable=False, comment="板块代码")
    block_name = Column(String(100), nullable=False, comment="板块名称")
    block_type = Column(String(20), comment="板块类型")
    total_buy_amount = Column(DECIMAL(20, 4), default=0, comment="板块买入总额")
    total_sell_amount = Column(DECIMAL(20, 4), default=0, comment="板块卖出总额")
    net_inflow = Column(DECIMAL(20, 4), default=0, comment="净流入")
    total_amount = Column(DECIMAL(20, 4), default=0, comment="总成交额")
    inflow_ratio = Column(DECIMAL(10, 4), default=0, comment="流入比例%")
    stock_count = Column(Integer, default=0, comment="成分股数量")
    inflow_stock_count = Column(Integer, default=0, comment="资金流入股票数")
    continuity_days = Column(Integer, default=0, comment="连续净流入天数")
    ranking = Column(Integer, comment="当日排名")
    ranking_change = Column(Integer, comment="排名变化")
    created_at = Column(DateTime, default=lambda: datetime.now())

    __table_args__ = (
        {"comment": "板块资金流向分析表"},
    )


class HoldingCostAnalysis(Base):
    """持股成本分析模型"""
    __tablename__ = "holding_cost_analysis"

    class CostTrend(enum.Enum):
        RISING = "rising"
        FALLING = "falling"
        STABLE = "stable"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, comment="交易日期")
    stock_code = Column(String(10), nullable=False, comment="股票代码")
    stock_name = Column(String(50), comment="股票名称")
    buy_vwap = Column(DECIMAL(10, 4), comment="买方加权均价")
    sell_vwap = Column(DECIMAL(10, 4), comment="卖方加权均价")
    vwap_spread = Column(DECIMAL(10, 4), comment="买卖价差")
    price_median = Column(DECIMAL(10, 4), comment="价格中位数")
    buy_median_diff = Column(DECIMAL(10, 4), comment="买方与中位数差")
    cost_pressure = Column(DECIMAL(10, 4), comment="成本压力指数")
    avg_cost_2d = Column(DECIMAL(10, 4), comment="2日平均成本")
    avg_cost_5d = Column(DECIMAL(10, 4), comment="5日平均成本")
    avg_cost_20d = Column(DECIMAL(10, 4), comment="20日平均成本")
    avg_cost_60d = Column(DECIMAL(10, 4), comment="60日平均成本")
    cost_trend = Column(Enum(CostTrend), default=CostTrend.STABLE, comment="成本趋势")
    created_at = Column(DateTime, default=lambda: datetime.now())

    __table_args__ = (
        {"comment": "持股成本分析表"},
    )