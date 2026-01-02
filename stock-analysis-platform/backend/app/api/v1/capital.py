# backend/app/api/v1/capital.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from app.core.database import get_db
from app.services.analysis_service import CapitalFlowAnalysis
from app.services.scoring_service import StockScoringModel

router = APIRouter(prefix="/api/v1/capital", tags=["capital"])


@router.get("/block-flows")
async def get_block_capital_flows(
        trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
        days: int = Query(7, description="分析天数"),
        block_type: Optional[str] = Query(None, description="板块类型：industry/region/concept"),
        limit: int = Query(20, description="返回数量"),
        db: Session = Depends(get_db)
):
    """
    获取板块资金流向排名
    """
    if not trade_date:
        trade_date = datetime.now().strftime('%Y-%m-%d')

    try:
        analyzer = CapitalFlowAnalysis(db)
        results = analyzer.calculate_block_capital_flow(trade_date, days)

        # 过滤板块类型
        if block_type:
            results = [r for r in results if r['block_type'] == block_type]

        # 限制返回数量
        results = results[:limit]

        return {
            "code": 0,
            "message": "success",
            "data": {
                "trade_date": trade_date,
                "analysis_days": days,
                "total_blocks": len(results),
                "blocks": results
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-flows/{stock_code}")
async def get_stock_capital_flow(
        stock_code: str,
        start_date: str = Query(..., description="开始日期"),
        end_date: str = Query(..., description="结束日期"),
        db: Session = Depends(get_db)
):
    """
    获取个股资金流向分析
    """
    try:
        analyzer = CapitalFlowAnalysis(db)
        result = analyzer.analyze_stock_capital_flow(stock_code, start_date, end_date)

        if not result:
            raise HTTPException(status_code=404, detail="未找到数据")

        return {
            "code": 0,
            "message": "success",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-score/{stock_code}")
async def get_stock_score(
        stock_code: str,
        trade_date: Optional[str] = Query(None, description="交易日期"),
        db: Session = Depends(get_db)
):
    """
    获取股票综合评分
    """
    if not trade_date:
        trade_date = datetime.now().strftime('%Y-%m-%d')

    try:
        scoring_model = StockScoringModel(db)
        result = scoring_model.score_stock(stock_code, trade_date)

        return {
            "code": 0,
            "message": "success",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-stocks")
async def get_top_stocks(
        trade_date: Optional[str] = Query(None, description="交易日期"),
        min_score: float = Query(70, description="最低评分"),
        limit: int = Query(50, description="返回数量"),
        db: Session = Depends(get_db)
):
    """
    获取高评分股票列表
    """
    if not trade_date:
        trade_date = datetime.now().strftime('%Y-%m-%d')

    try:
        # 这里可以批量评分，简化实现
        scoring_model = StockScoringModel(db)

        # 获取当日有交易的股票
        query = """
        SELECT DISTINCT stock_code 
        FROM stock_price_distribution 
        WHERE trade_date = :date
        LIMIT 1000
        """

        stocks = db.execute(query, {'date': trade_date}).fetchall()

        results = []
        for stock in stocks[:500]:  # 限制数量，避免性能问题
            try:
                score_result = scoring_model.score_stock(stock.stock_code, trade_date)
                if score_result['scores']['total'] >= min_score:
                    results.append(score_result)
            except:
                continue

        # 按总分排序
        results.sort(key=lambda x: x['scores']['total'], reverse=True)
        results = results[:limit]

        return {
            "code": 0,
            "message": "success",
            "data": {
                "trade_date": trade_date,
                "min_score": min_score,
                "total_count": len(results),
                "stocks": results
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))