"""
复合检测条件 - 金叉+DIF>0
"""
import pandas as pd
from typing import Dict, List, Optional

from src.detection.base import Signal, SignalCondition


class GoldenCrossWithMACDCondition(SignalCondition):
    """
    复合检测条件：金叉且DIF>0

    检测条件：
    - MA5上穿MA20（金叉）
    - 且 DIF > 0

    参数:
        short_period: 短期均线周期（如5）
        mid_period: 中期均线周期（如10）
        long_period: 长期均线周期（如20）
        data_type: 数据类型

    所需指标：
    - MA5 (短期均线)
    - MA10 (中期均线)
    - MA20 (长期均线)
    - DIF (MACD快慢线差值)
    """

    def __init__(
        self,
        short_period: int = 5,
        mid_period: int = 10,
        long_period: int = 20,
        data_type: str = "daily_kline"
    ):
        self._short_period = short_period
        self._mid_period = mid_period
        self._long_period = long_period
        self._data_type = data_type
        self._short_name = f"MA{short_period}"
        self._mid_name = f"MA{mid_period}"
        self._long_name = f"MA{long_period}"

    @property
    def name(self) -> str:
        return "golden_cross_with_macd"

    @property
    def required_indicators(self) -> List[str]:
        # 需要 MA5、MA10、MA20 和 DIF
        return [self._short_name, self._mid_name, self._long_name, "DIF"]

    @property
    def data_type(self) -> str:
        return self._data_type

    @property
    def description(self) -> str:
        return "金叉+DIF>0"

    def detect(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series]
    ) -> Optional[Signal]:
        """
        检测复合信号

        Args:
            code: 股票代码
            name: 股票名称
            data: K线数据
            indicators: 指标字典，需包含 MA5、MA10、MA20 和 DIF

        Returns:
            Signal 或 None
        """
        ma5 = indicators.get(self._short_name)
        ma10 = indicators.get(self._mid_name)
        ma20 = indicators.get(self._long_name)
        dif = indicators.get("DIF")

        # 验证指标数据
        if ma5 is None or ma10 is None or ma20 is None or dif is None:
            return None

        if len(ma5) < 2 or len(ma10) < 2 or len(ma20) < 2 or len(dif) < 2:
            return None

        # 获取当前值和前一个值
        curr_ma5 = ma5.iloc[-1]
        prev_ma5 = ma5.iloc[-2]
        curr_ma10 = ma10.iloc[-1]
        prev_ma10 = ma10.iloc[-2]
        curr_ma20 = ma20.iloc[-1]
        prev_ma20 = ma20.iloc[-2]
        curr_dif = dif.iloc[-1]
        prev_dif = dif.iloc[-2]

        # 检查是否有效值
        if pd.isna(curr_ma5) or pd.isna(prev_ma5) or \
           pd.isna(curr_ma10) or pd.isna(prev_ma10) or \
           pd.isna(curr_ma20) or pd.isna(prev_ma20) or \
           pd.isna(curr_dif) or pd.isna(prev_dif):
            return None

        # 条件A：金叉且DIF>0
        golden_cross = prev_ma5 <= prev_ma20 and curr_ma5 > curr_ma20
        dif_above_zero = curr_dif > 0
        condition = golden_cross and dif_above_zero

        if not condition:
            return None

        # 构建信号
        close = data["close"].iloc[-1]
        last_time = data["time"].iloc[-1]
        data_time = str(last_time)[:10] if len(str(last_time)) >= 10 else str(last_time)

        trigger_type = "金叉+DIF>0"

        return Signal(
            code=code,
            name=name,
            condition=self.name,
            values={
                self._short_name: round(curr_ma5, 2),
                self._mid_name: round(curr_ma10, 2),
                self._long_name: round(curr_ma20, 2),
                "DIF": round(curr_dif, 4),
                "close": round(close, 2),
                "trigger_type": trigger_type
            },
            data_time=data_time,
            message=f"{name}({code}) {trigger_type}: " +
                    f"MA5={curr_ma5:.2f}, MA10={curr_ma10:.2f}, MA20={curr_ma20:.2f}, " +
                    f"DIF={curr_dif:.4f}, 收盘={close:.2f}"
        )


def create_golden_cross_macd_condition_daily(
    short_period: int = 5,
    mid_period: int = 10,
    long_period: int = 20
) -> GoldenCrossWithMACDCondition:
    """
    创建日K复合检测条件

    Args:
        short_period: 短期均线周期
        mid_period: 中期均线周期
        long_period: 长期均线周期

    Returns:
        GoldenCrossWithMACDCondition 实例
    """
    return GoldenCrossWithMACDCondition(short_period, mid_period, long_period, "daily_kline")