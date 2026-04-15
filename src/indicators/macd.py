"""
MACD指标实现 - Moving Average Convergence Divergence
"""
from typing import Dict, Union

import pandas as pd

from src.indicators.base import Indicator


class MACDIndicator(Indicator):
    """
    MACD指标 (Moving Average Convergence Divergence)

    计算公式：
    - DIF = EMA(close, fast_period) - EMA(close, slow_period)
    - DEA = EMA(DIF, signal_period)
    - MACD = (DIF - DEA) * 2

    参数:
        fast_period: 快线EMA周期（默认12）
        slow_period: 慢线EMA周期（默认26）
        signal_period: DEA信号线周期（默认9）
        data_type: 数据类型（'daily_kline' 或其他）

    输出字段：
    - DIF: 快慢线差值
    - DEA: DIF的信号线
    - MACD: 柱状图值

    使用示例:
    >>> macd = MACDIndicator()
    >>> result = macd.calculate(klines_df)
    >>> # result 是字典：{'DIF': Series, 'DEA': Series, 'MACD': Series}
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        data_type: str = "daily_kline"
    ):
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period
        self._data_type = data_type
        self._name = "MACD"

    @property
    def name(self) -> str:
        return self._name

    @property
    def required_data(self) -> str:
        return self._data_type

    @property
    def min_data_length(self) -> int:
        # MACD计算至少需要slow_period条数据
        return self._slow_period

    @property
    def output_fields(self) -> list:
        # MACD是多值指标，返回三个字段
        return ["DIF", "DEA", "MACD"]

    @property
    def fast_period(self) -> int:
        """快线周期"""
        return self._fast_period

    @property
    def slow_period(self) -> int:
        """慢线周期"""
        return self._slow_period

    @property
    def signal_period(self) -> int:
        """信号线周期"""
        return self._signal_period

    def calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        计算MACD指标

        Args:
            data: K线数据 DataFrame，需包含 'close' 列

        Returns:
            字典 {'DIF': Series, 'DEA': Series, 'MACD': Series}
            索引与 data 一致
        """
        close_prices = data["close"]

        # 计算快线EMA和慢线EMA
        ema_fast = close_prices.ewm(span=self._fast_period, adjust=False).mean()
        ema_slow = close_prices.ewm(span=self._slow_period, adjust=False).mean()

        # DIF = 快线 - 慢线
        dif = ema_fast - ema_slow

        # DEA = DIF的signal周期EMA
        dea = dif.ewm(span=self._signal_period, adjust=False).mean()

        # MACD柱状图 = (DIF - DEA) * 2
        macd = (dif - dea) * 2

        return {
            "DIF": dif,
            "DEA": dea,
            "MACD": macd
        }


def create_macd_indicator_daily(
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> MACDIndicator:
    """
    创建日K MACD指标

    Args:
        fast_period: 快线周期（默认12）
        slow_period: 慢线周期（默认26）
        signal_period: 信号线周期（默认9）

    Returns:
        MACDIndicator 实例
    """
    return MACDIndicator(fast_period, slow_period, signal_period, "daily_kline")