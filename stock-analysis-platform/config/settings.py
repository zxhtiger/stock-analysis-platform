# config/settings.py
import os
from pathlib import Path
from typing import Optional


class Settings:
    """应用配置"""

    # 基础配置
    PROJECT_NAME = "股票分析平台"
    PROJECT_VERSION = "1.0.0"
    DEBUG = True

    # 数据库配置
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://stock:stock%401234@localhost:3306/stock"
    )

    # 数据目录
    DATA_DIR = Path(__file__).parent.parent / "data"

    # API配置
    API_V1_STR = "/api/v1"

    # 缓存配置
    # REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_URL = None  # 或者直接设为None

    # 分析参数
    DEFAULT_ANALYSIS_DAYS = 7
    TOP_N_BLOCKS = 20
    TOP_N_STOCKS = 10

    # 评分权重
    SCORING_WEIGHTS = {
        "capital": 0.40,  # 资金面权重
        "technical": 0.30,  # 技术面权重
        "fundamental": 0.20,  # 基本面权重
        "risk": 0.10  # 风险面权重
    }

    # 预警阈值
    ALERT_THRESHOLDS = {
        "large_outflow": -10000000,  # 大额流出预警
        "high_amplitude": 10.0,  # 高振幅预警
        "high_turnover": 20.0,  # 高换手率预警
        "low_liquidity": 10000000  # 低流动性预警
    }


settings = Settings()