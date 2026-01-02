# backend/app/api/v1/block.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.services.analysis_service import CapitalFlowAnalysis

router = APIRouter(prefix="/api/v1/block", tags=["block"])


@router.get("/list")
async def get_block_list(
        block_type: Optional[str] = Query(None, description="板块类型"),
        db: Session = Depends(get_db)
):
    """获取板块列表"""
    try:
        query = """
        SELECT DISTINCT 
            block_code,
            block_name,
            block_type,
            COUNT(DISTINCT stock_code) as stock_count
        FROM stock_block_membership
        """

        params = {}
        if block_type:
            query += " WHERE block_type = :block_type"
            params['block_type'] = block_type

        query += " GROUP BY block_code, block_name, block_type ORDER BY stock_count DESC"

        result = db.execute(query, params).fetchall()

        blocks = []
        for row in result:
            blocks.append({
                'block_code': row.block_code,
                'block_name': row.block_name,
                'block_type': row.block_type,
                'stock_count': row.stock_count
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "blocks": blocks,
                "total_count": len(blocks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{block_code}/stocks")
async def get_block_stocks(
        block_code: str,
        trade_date: Optional[str] = Query(None, description="交易日期"),
        sort_by: str = Query("inflow_ratio", description="排序字段"),
        limit: int = Query(10, description="返回数量"),
        db: Session = Depends(get_db)
):
    """获取板块内的股票"""
    try:
        if not trade_date:
            # 获取最新交易日
            date_query = "SELECT MAX(trade_date) as max_date FROM stock_price_distribution"
            date_result = db.execute(date_query).fetchone()
            trade_date = date_result.max_date.strftime('%Y-%m-%d') if date_result.max_date else datetime.now().strftime(
                '%Y-%m-%d')

        # 构建排序条件
        sort_fields = {
            "inflow_ratio": "p.inflow_ratio DESC",
            "net_inflow": "p.net_inflow DESC",
            "change_pct": "d.change_pct DESC",
            "amount": "d.amount DESC"
        }
        sort_condition = sort_fields.get(sort_by, "p.inflow_ratio DESC")

        query = f"""
        SELECT 
            d.stock_code,
            d.stock_name,
            d.close_price,
            d.change_pct,
            d.amount,
            d.volume,
            d.turnover_rate,
            p.net_inflow,
            p.inflow_ratio,
            p.large_net_inflow
        FROM stock_block_membership b
        INNER JOIN stock_day_data d 
            ON b.stock_code = d.stock_code
        LEFT JOIN stock_price_distribution p 
            ON b.stock_code = p.stock_code 
            AND d.trade_date = p.trade_date
        WHERE b.block_code = :block_code
          AND d.trade_date = :trade_date
        ORDER BY {sort_condition}
        LIMIT :limit
        """

        result = db.execute(query, {
            'block_code': block_code,
            'trade_date': trade_date,
            'limit': limit
        }).fetchall()

        # 获取板块信息
        block_query = """
        SELECT block_name, block_type 
        FROM stock_block_membership 
        WHERE block_code = :block_code 
        LIMIT 1
        """

        block_info = db.execute(block_query, {'block_code': block_code}).fetchone()

        stocks = []
        for row in result:
            stocks.append({
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'close_price': float(row.close_price) if row.close_price else 0,
                'change_pct': float(row.change_pct) if row.change_pct else 0,
                'amount': float(row.amount) if row.amount else 0,
                'volume': int(row.volume) if row.volume else 0,
                'turnover_rate': float(row.turnover_rate) if row.turnover_rate else 0,
                'net_inflow': float(row.net_inflow) if row.net_inflow else 0,
                'inflow_ratio': float(row.inflow_ratio) if row.inflow_ratio else 0,
                'large_net_inflow': float(row.large_net_inflow) if row.large_net_inflow else 0
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "block_code": block_code,
                "block_name": block_info.block_name if block_info else "",
                "block_type": block_info.block_type if block_info else "",
                "trade_date": trade_date,
                "stocks": stocks,
                "count": len(stocks)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{block_code}/history")
async def get_block_history(
        block_code: str,
        days: int = Query(30, description="历史天数"),
        db: Session = Depends(get_db)
):
    """获取板块历史资金流向"""
    try:
        # 获取板块名称
        block_query = """
        SELECT block_name, block_type 
        FROM stock_block_membership 
        WHERE block_code = :block_code 
        LIMIT 1
        """
        block_info = db.execute(block_query, {'block_code': block_code}).fetchone()

        if not block_info:
            raise HTTPException(status_code=404, detail="板块不存在")

        # 获取历史数据
        query = """
        SELECT 
            p.trade_date,
            SUM(p.total_buy_amount) as total_buy,
            SUM(p.total_sell_amount) as total_sell,
            SUM(p.net_inflow) as net_inflow,
            SUM(p.total_amount) as total_amount,
            COUNT(DISTINCT p.stock_code) as stock_count
        FROM stock_block_membership b
        INNER JOIN stock_price_distribution p 
            ON b.stock_code = p.stock_code
        WHERE b.block_code = :block_code
          AND p.trade_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        GROUP BY p.trade_date
        ORDER BY p.trade_date
        """

        result = db.execute(query, {
            'block_code': block_code,
            'days': days
        }).fetchall()

        history = []
        for row in result:
            inflow_ratio = (row.net_inflow / row.total_amount * 100
                            if row.total_amount and row.total_amount > 0 else 0)

            history.append({
                'date': str(row.trade_date),
                'total_buy': float(row.total_buy) if row.total_buy else 0,
                'total_sell': float(row.total_sell) if row.total_sell else 0,
                'net_inflow': float(row.net_inflow) if row.net_inflow else 0,
                'total_amount': float(row.total_amount) if row.total_amount else 0,
                'inflow_ratio': float(inflow_ratio),
                'stock_count': row.stock_count
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "block_code": block_code,
                "block_name": block_info.block_name,
                "block_type": block_info.block_type,
                "history": history,
                "summary": {
                    "total_days": len(history),
                    "avg_inflow_ratio": sum(h['inflow_ratio'] for h in history) / len(history) if history else 0,
                    "total_net_inflow": sum(h['net_inflow'] for h in history)
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))