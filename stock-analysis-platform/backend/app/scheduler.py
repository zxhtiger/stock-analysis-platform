# backend/app/scheduler.py
"""
数据更新调度器
"""
import schedule
import time
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.analysis_service import CapitalFlowAnalysis
from app.services.scoring_service import StockScoringModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_daily_analysis():
    """每日收盘后更新分析数据"""
    db = SessionLocal()
    try:
        # 获取最近交易日（假设T+1数据）
        trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        logger.info(f"开始更新 {trade_date} 的分析数据...")

        # 更新板块资金流向
        analyzer = CapitalFlowAnalysis(db)
        analyzer.calculate_and_store_block_flows(trade_date)

        logger.info("板块资金流向分析完成")

        # 批量更新股票评分
        scoring_model = StockScoringModel(db)

        # 获取当日有交易的股票
        query = """
        SELECT DISTINCT stock_code 
        FROM stock_price_distribution 
        WHERE trade_date = :trade_date
        LIMIT 100  # 测试时限制数量
        """

        stocks = db.execute(query, {'trade_date': trade_date}).fetchall()

        for i, stock in enumerate(stocks, 1):
            try:
                scoring_model.score_and_store(stock.stock_code, trade_date)
                if i % 10 == 0:
                    logger.info(f"已评分 {i}/{len(stocks)} 只股票")
            except Exception as e:
                logger.error(f"评分股票 {stock.stock_code} 失败: {e}")

        logger.info(f"成功更新 {trade_date} 的分析数据")

    except Exception as e:
        logger.error(f"更新分析数据失败: {e}")
    finally:
        db.close()


def update_holding_cost_analysis():
    """更新持股成本分析"""
    db = SessionLocal()
    try:
        logger.info("开始更新持股成本分析...")

        # 这里可以添加持股成本分析的更新逻辑
        # 目前先记录日志

        logger.info("持股成本分析更新完成")

    except Exception as e:
        logger.error(f"更新持股成本分析失败: {e}")
    finally:
        db.close()


def main():
    """调度器主函数"""
    logger.info("股票分析平台调度器启动...")

    # 设置定时任务
    schedule.every().day.at("18:00").do(update_daily_analysis)  # 每日18:00更新
    schedule.every().day.at("09:00").do(update_holding_cost_analysis)  # 每日09:00更新

    logger.info("调度器配置完成，开始运行...")

    # 立即运行一次（用于测试）
    update_daily_analysis()

    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    main()