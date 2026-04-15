"""
均线指标实现 - MA (Moving Average)
"""
from typing import Union

import pandas as pd

from src.indicators.base import Indicator


class MAIndicator(Indicator):
    """
    移动平均线指标 (Simple Moving Average)

    计算收盘价的简单移动平均线。

    参数:
        period: 均线周期（K线数量）
        data_type: 数据类型（'daily_kline' 或 'min15_kline'）

    使用示例:
    >>> ma5 = MAIndicator(5, "daily_kline")
    >>> ma5_series = ma5.calculate(klines_df)
    """

    def __init__(self, period: int, data_type: str = "daily_kline"):
        self._period = period
        self._data_type = data_type
        self._name = f"MA{period}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def required_data(self) -> str:
        return self._data_type

    @property
    def min_data_length(self) -> int:
        # MA 计算需要至少 period 条数据
        return self._period

    @property
    def period(self) -> int:
        """均线周期"""
        return self._period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算移动平均线

        Args:
            data: K线数据 DataFrame，需包含 'close' 列

        Returns:
            均线序列（索引与 data 一致，前 period-1 个值为 NaN）
        """
        close_prices = data["close"]
        return close_prices.rolling(window=self._period).mean()


class EMAIndicator(Indicator):
    """
    指数移动平均线指标 (Exponential Moving Average)

    计算收盘价的指数移动平均线，对近期数据给予更大权重。

    参数:
        period: 均线周期
        data_type: 数据类型
    """

    def __init__(self, period: int, data_type: str = "daily_kline"):
        self._period = period
        self._data_type = data_type
        self._name = f"EMA{period}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def required_data(self) -> str:
        return self._data_type

    @property
    def min_data_length(self) -> int:
        return self._period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算指数移动平均线

        Args:
            data: K线数据 DataFrame

        Returns:
            EMA 序列
        """
        close_prices = data["close"]
        return close_prices.ewm(span=self._period, adjust=False).mean()


def create_ma_indicators_daily(short_period: int = 5, long_period: int = 20) -> list:
    """
    创建日K均线指标组

    Args:
        short_period: 短期均线周期
        long_period: 长期均线周期

    Returns:
        [MAIndicator(short_period), MAIndicator(long_period)]
    """
    return [
        MAIndicator(short_period, "daily_kline"),
        MAIndicator(long_period, "daily_kline")
    ]


def create_ma_indicators_min15(short_period: int = 5, long_period: int = 20) -> list:
    """
    创建15分钟K均线指标组

    Args:
        short_period: 短期均线周期（天数）
        long_period: 长期均线周期（天数）

    Returns:
        [MAIndicator(short*16), MAIndicator(long*16)]
        注：15分钟K线，每天约16根
    """
    return [
        MAIndicator(short_period * 16, "min15_kline"),
        MAIndicator(long_period * 16, "min15_kline")
    ]