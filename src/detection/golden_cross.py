"""
金叉/死叉检测实现 - 均线交叉信号
"""
import pandas as pd
from typing import Dict, List, Optional

from src.detection.base import Signal, SignalCondition


class GoldenCrossCondition(SignalCondition):
    """
    金叉检测条件

    检测短期均线向上穿越长期均线。

    参数:
        short_period: 短期均线周期（如5）
        long_period: 长期均线周期（如20）
        data_type: 数据类型
    """

    def __init__(
        self,
        short_period: int = 5,
        long_period: int = 20,
        data_type: str = "daily_kline"
    ):
        self._short_period = short_period
        self._long_period = long_period
        self._data_type = data_type
        self._short_name = f"MA{short_period}"
        self._long_name = f"MA{long_period}"

    @property
    def name(self) -> str:
        return "golden_cross"

    @property
    def required_indicators(self) -> List[str]:
        return [self._short_name, self._long_name]

    @property
    def data_type(self) -> str:
        return self._data_type

    @property
    def description(self) -> str:
        return f"MA{self._short_period}/MA{self._long_period} 金叉"

    def detect(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series]
    ) -> Optional[Signal]:
        """
        检测金叉信号

        Args:
            code: 股票代码
            name: 股票名称
            data: K线数据
            indicators: 指标字典，需包含 MA_short 和 MA_long

        Returns:
            Signal 或 None
        """
        ma_short = indicators.get(self._short_name)
        ma_long = indicators.get(self._long_name)

        if ma_short is None or ma_long is None:
            return None

        if len(ma_short) < 2 or len(ma_long) < 2:
            return None

        # 当前值和前一个值
        curr_short = ma_short.iloc[-1]
        prev_short = ma_short.iloc[-2]
        curr_long = ma_long.iloc[-1]
        prev_long = ma_long.iloc[-2]

        # 检查是否有效值
        if pd.isna(curr_short) or pd.isna(prev_short) or pd.isna(curr_long) or pd.isna(prev_long):
            return None

        # 金叉条件：前一根短线<=长线，当前短线>长线
        is_golden_cross = prev_short <= prev_long and curr_short > curr_long

        if not is_golden_cross:
            return None

        # 构建信号
        close = data["close"].iloc[-1]
        last_time = data["time"].iloc[-1]
        data_time = str(last_time)[:10] if len(str(last_time)) >= 10 else str(last_time)

        return Signal(
            code=code,
            name=name,
            condition=self.name,
            values={
                self._short_name: round(curr_short, 2),
                self._long_name: round(curr_long, 2),
                "close": round(close, 2)
            },
            data_time=data_time,
            message=f"{name}({code}) {self._short_name}/{self._long_name} 金叉: " +
                    f"{self._short_name}={curr_short:.2f}, {self._long_name}={curr_long:.2f}, " +
                    f"收盘={close:.2f}"
        )


class DeathCrossCondition(SignalCondition):
    """
    死叉检测条件

    检测短期均线向下穿越长期均线。
    """

    def __init__(
        self,
        short_period: int = 5,
        long_period: int = 20,
        data_type: str = "daily_kline"
    ):
        self._short_period = short_period
        self._long_period = long_period
        self._data_type = data_type
        self._short_name = f"MA{short_period}"
        self._long_name = f"MA{long_period}"

    @property
    def name(self) -> str:
        return "death_cross"

    @property
    def required_indicators(self) -> List[str]:
        return [self._short_name, self._long_name]

    @property
    def data_type(self) -> str:
        return self._data_type

    @property
    def description(self) -> str:
        return f"MA{self._short_period}/MA{self._long_period} 死叉"

    def detect(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series]
    ) -> Optional[Signal]:
        """
        检测死叉信号
        """
        ma_short = indicators.get(self._short_name)
        ma_long = indicators.get(self._long_name)

        if ma_short is None or ma_long is None:
            return None

        if len(ma_short) < 2 or len(ma_long) < 2:
            return None

        curr_short = ma_short.iloc[-1]
        prev_short = ma_short.iloc[-2]
        curr_long = ma_long.iloc[-1]
        prev_long = ma_long.iloc[-2]

        if pd.isna(curr_short) or pd.isna(prev_short) or pd.isna(curr_long) or pd.isna(prev_long):
            return None

        # 死叉条件：前一根短线>=长线，当前短线<长线
        is_death_cross = prev_short >= prev_long and curr_short < curr_long

        if not is_death_cross:
            return None

        close = data["close"].iloc[-1]
        last_time = data["time"].iloc[-1]
        data_time = str(last_time)[:10] if len(str(last_time)) >= 10 else str(last_time)

        return Signal(
            code=code,
            name=name,
            condition=self.name,
            values={
                self._short_name: round(curr_short, 2),
                self._long_name: round(curr_long, 2),
                "close": round(close, 2)
            },
            data_time=data_time,
            message=f"{name}({code}) {self._short_name}/{self._long_name} 死叉"
        )


def create_cross_conditions_daily(
    short_period: int = 5,
    long_period: int = 20
) -> list:
    """
    创建日K金叉/死叉检测条件组

    Args:
        short_period: 短期均线周期
        long_period: 长期均线周期

    Returns:
        [GoldenCrossCondition, DeathCrossCondition]
    """
    return [
        GoldenCrossCondition(short_period, long_period, "daily_kline"),
        DeathCrossCondition(short_period, long_period, "daily_kline")
    ]