# backend/app/services/alert_service.py
class AlertService:
    """股票预警服务"""

    def __init__(self, db: Session):
        self.db = db

    def check_alerts(self, stock_code: str, trade_date: str) -> List[Dict]:
        """检查股票预警信号"""
        alerts = []

        # 1. 资金异常预警
        capital_alerts = self._check_capital_alerts(stock_code, trade_date)
        alerts.extend(capital_alerts)

        # 2. 技术面预警
        technical_alerts = self._check_technical_alerts(stock_code, trade_date)
        alerts.extend(technical_alerts)

        # 3. 风险预警
        risk_alerts = self._check_risk_alerts(stock_code, trade_date)
        alerts.extend(risk_alerts)

        return alerts

    def _check_capital_alerts(self, stock_code: str, trade_date: str) -> List[Dict]:
        """检查资金面预警"""
        alerts = []

        # 查询最近资金流向
        query = """
        SELECT 
            net_inflow,
            large_net_inflow,
            inflow_ratio,
            (SELECT net_inflow FROM stock_price_distribution 
             WHERE stock_code = :stock_code 
               AND trade_date = DATE_SUB(:date, INTERVAL 1 DAY)) as prev_inflow
        FROM stock_price_distribution
        WHERE stock_code = :stock_code 
          AND trade_date = :date
        """

        result = self.db.execute(query, {
            'stock_code': stock_code,
            'date': trade_date
        }).fetchone()

        if not result:
            return alerts

        # 资金大幅流出预警
        if result.net_inflow < -10000000:  # 净流出超过1000万
            alerts.append({
                'type': 'capital_outflow',
                'level': 'warning',
                'message': f'资金大幅流出，净流出{abs(result.net_inflow / 10000):.0f}万元',
                'suggestion': '注意风险，考虑减仓'
            })

        # 主力资金背离预警
        if result.net_inflow > 0 and result.large_net_inflow < 0:
            alerts.append({
                'type': 'capital_divergence',
                'level': 'warning',
                'message': '主力资金流出但散户资金流入，存在背离',
                'suggestion': '谨慎对待，观察后续'
            })

        # 资金流入加速预警
        if result.prev_inflow and result.net_inflow > result.prev_inflow * 2:
            alerts.append({
                'type': 'capital_acceleration',
                'level': 'info',
                'message': '资金流入加速，关注度提升',
                'suggestion': '可适当关注'
            })

        return alerts