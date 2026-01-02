# backend/app/api/v1/strategy.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.services.scoring_service import StockScoringModel

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


@router.get("/top-scoring")
async def get_top_scoring_stocks(
        min_score: float = Query(70, description="最低评分"),
        max_count: int = Query(50, description="最大返回数量"),
        trade_date: Optional[str] = Query(None, description="交易日期"),
        db: Session = Depends(get_db)
):
    """获取高评分股票"""
    try:
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        scoring_model = StockScoringModel(db)

        # 获取所有股票评分（实际应用中应该分批处理）
        query = """
        SELECT DISTINCT stock_code 
        FROM stock_price_distribution 
        WHERE trade_date = :trade_date
        LIMIT 1000
        """

        stocks = db.execute(query, {'trade_date': trade_date}).fetchall()

        results = []
        for stock in stocks:
            try:
                score_result = scoring_model.score_stock(stock.stock_code, trade_date)
                if score_result['scores']['total'] >= min_score:
                    results.append(score_result)
            except Exception:
                continue

        # 按总分排序
        results.sort(key=lambda x: x['scores']['total'], reverse=True)
        results = results[:max_count]

        return {
            "code": 0,
            "message": "success",
            "data": {
                "trade_date": trade_date,
                "min_score": min_score,
                "stocks": results,
                "count": len(results)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capital-flow")
async def capital_flow_strategy(
        min_inflow_ratio: float = Query(1.0, description="最小流入比例"),
        min_continuity_days: int = Query(3, description="最小连续流入天数"),
        trade_date: Optional[str] = Query(None, description="交易日期"),
        limit: int = Query(20, description="返回数量"),
        db: Session = Depends(get_db)
):
    """资金流向策略"""
    try:
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        # 查询连续资金流入的股票
        query = """
        WITH recent_flows AS (
            SELECT 
                stock_code,
                trade_date,
                inflow_ratio,
                net_inflow,
                LAG(inflow_ratio) OVER (PARTITION BY stock_code ORDER BY trade_date) as prev_inflow_ratio
            FROM stock_price_distribution
            WHERE trade_date BETWEEN DATE_SUB(:trade_date, INTERVAL 10 DAY) AND :trade_date
        ),
        continuity_counts AS (
            SELECT 
                stock_code,
                COUNT(*) as positive_days
            FROM recent_flows
            WHERE inflow_ratio > :min_inflow_ratio
            GROUP BY stock_code
        )
        SELECT 
            d.stock_code,
            d.stock_name,
            d.close_price,
            d.change_pct,
            p.inflow_ratio,
            p.net_inflow,
            c.positive_days,
            (SELECT inflow_ratio FROM stock_price_distribution 
             WHERE stock_code = d.stock_code 
               AND trade_date = DATE_SUB(:trade_date, INTERVAL 1 DAY)) as prev_inflow_ratio
        FROM stock_day_data d
        INNER JOIN stock_price_distribution p 
            ON d.stock_code = p.stock_code 
            AND d.trade_date = p.trade_date
        INNER JOIN continuity_counts c 
            ON d.stock_code = c.stock_code
        WHERE d.trade_date = :trade_date
          AND p.inflow_ratio > :min_inflow_ratio
          AND c.positive_days >= :min_continuity_days
        ORDER BY p.inflow_ratio DESC
        LIMIT :limit
        """

        result = db.execute(query, {
            'trade_date': trade_date,
            'min_inflow_ratio': min_inflow_ratio,
            'min_continuity_days': min_continuity_days,
            'limit': limit
        }).fetchall()

        stocks = []
        for row in result:
            stocks.append({
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'close_price': float(row.close_price) if row.close_price else 0,
                'change_pct': float(row.change_pct) if row.change_pct else 0,
                'inflow_ratio': float(row.inflow_ratio) if row.inflow_ratio else 0,
                'net_inflow': float(row.net_inflow) if row.net_inflow else 0,
                'continuity_days': row.positive_days,
                'trend': 'improving' if row.prev_inflow_ratio and row.inflow_ratio > row.prev_inflow_ratio else 'stable'
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "strategy_name": "资金连续流入策略",
                "trade_date": trade_date,
                "parameters": {
                    "min_inflow_ratio": min_inflow_ratio,
                    "min_continuity_days": min_continuity_days
                },
                "stocks": stocks,
                "count": len(stocks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/breakout")
async def breakout_strategy(
        ma_period: int = Query(20, description="均线周期"),
        volume_ratio: float = Query(1.2, description="量比阈值"),
        trade_date: Optional[str] = Query(None, description="交易日期"),
        limit: int = Query(20, description="返回数量"),
        db: Session = Depends(get_db)
):
    """突破策略"""
    try:
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        # 查询突破均线的股票
        query = f"""
        SELECT 
            d.stock_code,
            d.stock_name,
            d.close_price,
            d.open_price,
            d.high_price,
            d.low_price,
            d.volume,
            d.vma{ma_period},
            d.change_pct,
            d.ma{ma_period},
            (SELECT close_price FROM stock_day_data 
             WHERE stock_code = d.stock_code 
               AND trade_date = DATE_SUB(:trade_date, INTERVAL 1 DAY)) as prev_close
        FROM stock_day_data d
        WHERE d.trade_date = :trade_date
          AND d.close_price > d.ma{ma_period}
          AND d.volume > d.vma{ma_period} * :volume_ratio
          AND d.close_price > d.open_price  -- 阳线
        ORDER BY (d.close_price - d.ma{ma_period}) / d.ma{ma_period} DESC
        LIMIT :limit
        """

        result = db.execute(query, {
            'trade_date': trade_date,
            'volume_ratio': volume_ratio,
            'limit': limit
        }).fetchall()

        stocks = []
        for row in result:
            volume_ratio_value = row.volume / row[f'vma{ma_period}'] if row[f'vma{ma_period}'] and row[
                f'vma{ma_period}'] > 0 else 0
            break_ratio = (row.close_price - row[f'ma{ma_period}']) / row[f'ma{ma_period}'] * 100 if row[
                                                                                                         f'ma{ma_period}'] and \
                                                                                                     row[
                                                                                                         f'ma{ma_period}'] > 0 else 0

            stocks.append({
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'close_price': float(row.close_price) if row.close_price else 0,
                'break_ratio': float(break_ratio),
                'volume_ratio': float(volume_ratio_value),
                'change_pct': float(row.change_pct) if row.change_pct else 0,
                'signal_strength': min(10, int(abs(break_ratio) * 2 + volume_ratio_value))
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "strategy_name": f"MA{ma_period}突破策略",
                "trade_date": trade_date,
                "parameters": {
                    "ma_period": ma_period,
                    "volume_ratio": volume_ratio
                },
                "stocks": stocks,
                "count": len(stocks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener")
async def stock_screener(
        min_inflow_ratio: float = Query(0, description="最小流入比例"),
        min_change_pct: float = Query(-10, description="最小涨跌幅"),
        max_change_pct: float = Query(10, description="最大涨跌幅"),
        min_amount: float = Query(10000000, description="最小成交额"),
        trade_date: Optional[str] = Query(None, description="交易日期"),
        limit: int = Query(50, description="返回数量"),
        db: Session = Depends(get_db)
):
    """股票筛选器"""
    try:
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        query = """
        SELECT 
            d.stock_code,
            d.stock_name,
            d.close_price,
            d.change_pct,
            d.amount,
            d.turnover_rate,
            d.volume,
            p.inflow_ratio,
            p.net_inflow,
            d.ma5,
            d.ma20
        FROM stock_day_data d
        LEFT JOIN stock_price_distribution p 
            ON d.stock_code = p.stock_code 
            AND d.trade_date = p.trade_date
        WHERE d.trade_date = :trade_date
          AND (p.inflow_ratio IS NULL OR p.inflow_ratio >= :min_inflow_ratio)
          AND d.change_pct >= :min_change_pct
          AND d.change_pct <= :max_change_pct
          AND d.amount >= :min_amount
        ORDER BY d.amount DESC
        LIMIT :limit
        """

        result = db.execute(query, {
            'trade_date': trade_date,
            'min_inflow_ratio': min_inflow_ratio,
            'min_change_pct': min_change_pct,
            'max_change_pct': max_change_pct,
            'min_amount': min_amount,
            'limit': limit
        }).fetchall()

        stocks = []
        for row in result:
            ma_trend = "up" if row.ma5 and row.ma20 and row.ma5 > row.ma20 else "down"

            stocks.append({
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'close_price': float(row.close_price) if row.close_price else 0,
                'change_pct': float(row.change_pct) if row.change_pct else 0,
                'amount': float(row.amount) if row.amount else 0,
                'turnover_rate': float(row.turnover_rate) if row.turnover_rate else 0,
                'inflow_ratio': float(row.inflow_ratio) if row.inflow_ratio else 0,
                'net_inflow': float(row.net_inflow) if row.net_inflow else 0,
                'ma_trend': ma_trend,
                'score': self._calculate_screener_score(row)
            })

        # 按分数排序
        stocks.sort(key=lambda x: x['score'], reverse=True)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "trade_date": trade_date,
                "filters": {
                    "min_inflow_ratio": min_inflow_ratio,
                    "min_change_pct": min_change_pct,
                    "max_change_pct": max_change_pct,
                    "min_amount": min_amount
                },
                "stocks": stocks,
                "count": len(stocks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    def _calculate_screener_score(self, row) -> float:
        """计算筛选器分数"""
        score = 50.0

        # 资金流入加分
        if row.inflow_ratio:
            score += min(row.inflow_ratio * 10, 20)

        # 成交额加分
        if row.amount:
            score += min(np.log10(max(row.amount, 1)) - 6, 10)

        # 换手率适中加分
        if row.turnover_rate and 2 <= row.turnover_rate <= 10:
            score += 5

        # 均线趋势加分
        if hasattr(row, 'ma5') and hasattr(row, 'ma20'):
            if row.ma5 and row.ma20 and row.ma5 > row.ma20:
                score += 10

        return min(max(score, 0), 100)