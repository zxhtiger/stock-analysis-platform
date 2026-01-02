# backend/app/models/stock_analysis.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, Enum
from sqlalchemy.dialects.mysql import DECIMAL
import enum

from app.core.database import Base


class StockScoringResult(Base):
    """股票评分结果模型"""
    __tablename__ = "stock_scoring_result"

    class SignalType(enum.Enum):
        BUY = "buy"
        SELL = "sell"
        HOLD = "hold"
        WARNING = "warning"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, comment="交易日期")
    stock_code = Column(String(10), nullable=False, comment="股票代码")
    stock_name = Column(String(50), comment="股票名称")
    capital_score = Column(DECIMAL(5, 2), default=0, comment="资金面评分")
    technical_score = Column(DECIMAL(5, 2), default=0, comment="技术面评分")
    fundamental_score = Column(DECIMAL(5, 2), default=0, comment="基本面评分")
    risk_score = Column(DECIMAL(5, 2), default=0, comment="风险面评分")
    total_score = Column(DECIMAL(5, 2), default=0, comment="总分")
    capital_weight = Column(DECIMAL(5, 2), default=0.40, comment="资金权重")
    technical_weight = Column(DECIMAL(5, 2), default=0.30, comment="技术权重")
    fundamental_weight = Column(DECIMAL(5, 2), default=0.20, comment="基本面权重")
    risk_weight = Column(DECIMAL(5, 2), default=0.10, comment="风险权重")
    signal_type = Column(Enum(SignalType), default=SignalType.HOLD, comment="信号类型")
    signal_strength = Column(Integer, default=0, comment="信号强度 0-10")
    ranking = Column(Integer, comment="当日排名")
    analysis_summary = Column(JSON, comment="分析摘要")
    created_at = Column(DateTime, default=lambda: datetime.now())

    __table_args__ = (
        {"comment": "股票综合评分结果表"},
    )