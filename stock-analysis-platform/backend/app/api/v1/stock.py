# backend/app/api/v1/stock.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.services.cost_analysis_service import HoldingCostAnalysis
from app.services.scoring_service import StockScoringModel
from app.utils.indicators import TechnicalIndicators

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


@router.get("/{stock_code}/details")
async def get_stock_details(
        stock_code: str,
        start_date: Optional[str] = Query(None, description="开始日期"),
        end_date: Optional[str] = Query(None, description="结束日期"),
        db: Session = Depends(get_db)
):
    """获取股票详细信息"""
    try:
        # 设置默认日期范围
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # 查询股票基本信息
        query = """
        SELECT 
            d.stock_code,
            d.stock_name,
            d.trade_date,
            d.close_price,
            d.open_price,
            d.high_price,
            d.low_price,
            d.volume,
            d.amount,
            d.turnover_rate,
            d.change_pct,
            d.ma5,
            d.ma20,
            d.ma60,
            p.net_inflow,
            p.inflow_ratio,
            p.large_net_inflow
        FROM stock_day_data d
        LEFT JOIN stock_price_distribution p 
            ON d.stock_code = p.stock_code 
            AND d.trade_date = p.trade_date
        WHERE d.stock_code = :stock_code
          AND d.trade_date BETWEEN :start_date AND :end_date
        ORDER BY d.trade_date
        """

        result = db.execute(query, {
            'stock_code': stock_code,
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        if not result:
            raise HTTPException(status_code=404, detail="未找到股票数据")

        # 组织数据
        dates = []
        prices = []
        volumes = []
        inflows = []

        for row in result:
            dates.append(str(row.trade_date))
            prices.append({
                'open': float(row.open_price) if row.open_price else 0,
                'high': float(row.high_price) if row.high_price else 0,
                'low': float(row.low_price) if row.low_price else 0,
                'close': float(row.close_price) if row.close_price else 0,
                'volume': int(row.volume) if row.volume else 0,
                'amount': float(row.amount) if row.amount else 0
            })
            volumes.append(int(row.volume) if row.volume else 0)
            inflows.append({
                'net_inflow': float(row.net_inflow) if row.net_inflow else 0,
                'inflow_ratio': float(row.inflow_ratio) if row.inflow_ratio else 0
            })

        # 计算技术指标
        close_prices = [p['close'] for p in prices]
        technical_indicators = {
            'ma5': TechnicalIndicators.calculate_ma(close_prices, 5),
            'ma20': TechnicalIndicators.calculate_ma(close_prices, 20),
            'ma60': TechnicalIndicators.calculate_ma(close_prices, 60),
            'rsi': TechnicalIndicators.calculate_rsi(close_prices, 14)
        }

        return {
            "code": 0,
            "message": "success",
            "data": {
                "stock_code": stock_code,
                "stock_name": result[0].stock_name,
                "dates": dates,
                "prices": prices,
                "volumes": volumes,
                "inflows": inflows,
                "technical_indicators": technical_indicators,
                "summary": {
                    "total_days": len(result),
                    "avg_volume": sum(volumes) / len(volumes) if volumes else 0,
                    "total_inflow": sum(inflow['net_inflow'] for inflow in inflows),
                    "price_change": close_prices[-1] - close_prices[0] if close_prices else 0
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stock_code}/cost-analysis")
async def get_stock_cost_analysis(
        stock_code: str,
        days: int = Query(60, description="分析天数"),
        db: Session = Depends(get_db)
):
    """获取股票持股成本分析"""
    try:
        cost_analyzer = HoldingCostAnalysis(db)
        analysis = cost_analyzer.analyze_holding_cost(stock_code, days)

        if not analysis:
            raise HTTPException(status_code=404, detail="未找到成本分析数据")

        return {
            "code": 0,
            "message": "success",
            "data": analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stock_code}/score")
async def get_stock_score(
        stock_code: str,
        trade_date: Optional[str] = Query(None, description="交易日期"),
        db: Session = Depends(get_db)
):
    """获取股票综合评分"""
    try:
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        scoring_model = StockScoringModel(db)
        score_result = scoring_model.score_stock(stock_code, trade_date)

        return {
            "code": 0,
            "message": "success",
            "data": score_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stock_code}/alerts")
async def get_stock_alerts(
        stock_code: str,
        trade_date: Optional[str] = Query(None, description="交易日期"),
        db: Session = Depends(get_db)
):
    """获取股票预警信息"""
    try:
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        from app.services.alert_service import AlertService
        alert_service = AlertService(db)
        alerts = alert_service.check_alerts(stock_code, trade_date)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "stock_code": stock_code,
                "trade_date": trade_date,
                "alerts": alerts,
                "alert_count": len(alerts)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_stocks(
        keyword: str = Query(..., description="搜索关键词（代码或名称）"),
        limit: int = Query(20, description="返回数量"),
        db: Session = Depends(get_db)
):
    """搜索股票"""
    try:
        query = """
        SELECT DISTINCT 
            d.stock_code,
            d.stock_name,
            d.market,
            d.close_price,
            d.change_pct,
            p.net_inflow
        FROM stock_day_data d
        LEFT JOIN stock_price_distribution p 
            ON d.stock_code = p.stock_code 
            AND d.trade_date = (SELECT MAX(trade_date) FROM stock_day_data)
        WHERE d.stock_code LIKE :keyword 
           OR d.stock_name LIKE :keyword
        ORDER BY d.stock_code
        LIMIT :limit
        """

        result = db.execute(query, {
            'keyword': f"%{keyword}%",
            'limit': limit
        }).fetchall()

        stocks = []
        for row in result:
            stocks.append({
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'market': row.market,
                'close_price': float(row.close_price) if row.close_price else 0,
                'change_pct': float(row.change_pct) if row.change_pct else 0,
                'net_inflow': float(row.net_inflow) if row.net_inflow else 0
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "keyword": keyword,
                "stocks": stocks,
                "count": len(stocks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))