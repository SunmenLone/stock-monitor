"""
技术指标计算模块（向后兼容）
"""
import pandas as pd
from typing import Optional, Tuple

import config


def calculate_ma(close_prices: pd.Series, period: int) -> pd.Series:
    """
    计算移动平均线

    Args:
        close_prices: 收盘价序列
        period: 均线周期（K线数量）

    Returns:
        均线序列
    """
    return close_prices.rolling(window=period).mean()


def detect_cross(ma_short: pd.Series, ma_long: pd.Series) -> Tuple[bool, bool]:
    """
    检测均线交叉

    Args:
        ma_short: 短期均线
        ma_long: 长期均线

    Returns:
        (golden_cross, death_cross)
        - golden_cross: 金叉（短线上穿长线）
        - death_cross: 死叉（短线下穿长线）
    """
    if len(ma_short) < 2 or len(ma_long) < 2:
        return False, False

    curr_short = ma_short.iloc[-1]
    prev_short = ma_short.iloc[-2]
    curr_long = ma_long.iloc[-1]
    prev_long = ma_long.iloc[-2]

    if pd.isna(curr_short) or pd.isna(prev_short) or pd.isna(curr_long) or pd.isna(prev_long):
        return False, False

    golden_cross = prev_short <= prev_long and curr_short > curr_long
    death_cross = prev_short >= prev_long and curr_short < curr_long

    return golden_cross, death_cross


def get_current_values(ma_short: pd.Series, ma_long: pd.Series) -> Tuple[float, float]:
    """
    获取当前均线值

    Returns:
        (ma_short_current, ma_long_current)
    """
    return ma_short.iloc[-1], ma_long.iloc[-1]


def get_cross_status(ma_short: pd.Series, ma_long: pd.Series) -> str:
    """
    获取当前均线状态

    Returns:
        "golden_cross" - 金叉区域（短线>长线）
        "death_cross" - 死叉区域（短线<长线）
        "neutral" - 中性（相等）
        "unknown" - 数据不足
    """
    if len(ma_short) < 1 or len(ma_long) < 1:
        return "unknown"

    curr_short = ma_short.iloc[-1]
    curr_long = ma_long.iloc[-1]

    if pd.isna(curr_short) or pd.isna(curr_long):
        return "unknown"

    if curr_short > curr_long:
        return "golden_cross"
    elif curr_short < curr_long:
        return "death_cross"
    else:
        return "neutral"


def calculate_indicators_daily(klines: pd.DataFrame) -> Optional[Tuple[pd.Series, pd.Series]]:
    """
    计算日K线的均线指标

    Args:
        klines: 日K线数据（包含close列）

    Returns:
        (ma_short, ma_long) 或 None（数据不足）
    """
    if klines is None or len(klines) < config.MA_LONG_KLINES_DAILY:
        return None

    close_prices = klines["close"]

    ma_short = calculate_ma(close_prices, config.MA_SHORT_KLINES_DAILY)
    ma_long = calculate_ma(close_prices, config.MA_LONG_KLINES_DAILY)

    return ma_short, ma_long