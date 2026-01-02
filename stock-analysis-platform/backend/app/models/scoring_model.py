# backend/app/models/scoring_model.py
from dataclasses import dataclass
from typing import Dict


@dataclass
class ScoringWeights:
    """评分权重配置"""
    capital: float = 0.40  # 资金面权重
    technical: float = 0.30  # 技术面权重
    fundamental: float = 0.20  # 基本面权重
    risk: float = 0.10  # 风险面权重

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "capital": self.capital,
            "technical": self.technical,
            "fundamental": self.fundamental,
            "risk": self.risk
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScoringWeights':
        """从字典创建"""
        return cls(
            capital=data.get("capital", 0.40),
            technical=data.get("technical", 0.30),
            fundamental=data.get("fundamental", 0.20),
            risk=data.get("risk", 0.10)
        )