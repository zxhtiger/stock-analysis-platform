# backend/app/utils/indicators.py
import numpy as np
from typing import List, Tuple, Optional


class TechnicalIndicators:
    """技术指标计算工具"""

    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> List[float]:
        """计算移动平均线"""
        if len(prices) < period:
            return [np.nan] * len(prices)

        ma_values = []
        for i in range(len(prices)):
            if i < period - 1:
                ma_values.append(np.nan)
            else:
                ma = np.mean(prices[i - period + 1:i + 1])
                ma_values.append(ma)

        return ma_values

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """计算指数移动平均线"""
        if len(prices) < period:
            return [np.nan] * len(prices)

        alpha = 2 / (period + 1)
        ema_values = [prices[0]]

        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema_values[-1]
            ema_values.append(ema)

        return ema_values

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return [np.nan] * len(prices)

        deltas = np.diff(prices)
        seed = deltas[:period + 1]

        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            rs = 0
        else:
            rs = up / down

        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)

        for i in range(period, len(prices)):
            delta = deltas[i - 1]

            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period

            if down == 0:
                rs = 0
            else:
                rs = up / down

            rsi[i] = 100. - 100. / (1. + rs)

        return rsi.tolist()

    @staticmethod
    def calculate_macd(prices: List[float],
                       fast_period: int = 12,
                       slow_period: int = 26,
                       signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """计算MACD指标"""
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow_period)

        macd_line = []
        for fast, slow in zip(ema_fast, ema_slow):
            if np.isnan(fast) or np.isnan(slow):
                macd_line.append(np.nan)
            else:
                macd_line.append(fast - slow)

        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal_period)

        histogram = []
        for macd, signal in zip(macd_line, signal_line):
            if np.isnan(macd) or np.isnan(signal):
                histogram.append(np.nan)
            else:
                histogram.append(macd - signal)

        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(prices: List[float],
                                  period: int = 20,
                                  num_std: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """计算布林带"""
        ma = TechnicalIndicators.calculate_ma(prices, period)

        upper_band = []
        lower_band = []

        for i in range(len(prices)):
            if i < period - 1:
                upper_band.append(np.nan)
                lower_band.append(np.nan)
            else:
                window = prices[i - period + 1:i + 1]
                std = np.std(window)
                upper_band.append(ma[i] + num_std * std)
                lower_band.append(ma[i] - num_std * std)

        return ma, upper_band, lower_band

    @staticmethod
    def calculate_atr(highs: List[float],
                      lows: List[float],
                      closes: List[float],
                      period: int = 14) -> List[float]:
        """计算ATR（平均真实波幅）"""
        if len(highs) < period:
            return [np.nan] * len(highs)

        tr_values = []
        for i in range(1, len(highs)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr = max(hl, hc, lc)
            tr_values.append(tr)

        atr_values = [np.nan] * period
        atr = np.mean(tr_values[:period])
        atr_values.append(atr)

        for i in range(period, len(tr_values)):
            atr = (atr * (period - 1) + tr_values[i]) / period
            atr_values.append(atr)

        return atr_values

    @staticmethod
    def calculate_volume_indicators(volumes: List[int],
                                    period: int = 20) -> Dict[str, List[float]]:
        """计算成交量指标"""
        vma = TechnicalIndicators.calculate_ma(volumes, period)

        # 计算量比
        volume_ratios = []
        for i, volume in enumerate(volumes):
            if i < period - 1 or np.isnan(vma[i]):
                volume_ratios.append(np.nan)
            else:
                volume_ratios.append(volume / vma[i])

        # 计算能量潮（简化版）
        obv = [0]
        for i in range(1, len(volumes)):
            # 这里需要价格数据来判断涨跌，简化处理
            obv.append(obv[-1] + volumes[i])

        return {
            "vma": vma,
            "volume_ratio": volume_ratios,
            "obv": obv
        }