"""
信号检测器 - 整合指标计算和条件检测
"""
import logging
from typing import Dict, List, Optional

import pandas as pd

from src.indicators.engine import IndicatorEngine
from src.detection.base import Signal, SignalCondition
from src.detection.registry import SignalRegistry

logger = logging.getLogger(__name__)


class SignalDetector:
    """
    信号检测器

    职责:
    1. 根据检测条件所需指标，批量计算指标
    2. 执行所有注册的检测条件
    3. 收集并返回检测到的信号

    使用示例:
    >>> detector = SignalDetector(signal_registry, indicator_engine)
    >>> signals = detector.detect("000001", "平安银行", "daily_kline", klines_df)
    >>> for signal in signals:
    ...     print(signal.message)
    """

    def __init__(self, signal_registry: SignalRegistry, indicator_engine: IndicatorEngine):
        self.signal_registry = signal_registry
        self.indicator_engine = indicator_engine

    def detect(
        self,
        code: str,
        name: str,
        data_type: str,
        data: pd.DataFrame
    ) -> List[Signal]:
        """
        对单只股票执行所有适用的检测条件

        Args:
            code: 股票代码
            name: 股票名称
            data_type: 数据类型（如 'daily_kline'）
            data: K线数据 DataFrame

        Returns:
            检测到的信号列表
        """
        signals = []

        if data is None or data.empty:
            logger.debug(f"{code}({name}) 数据为空，跳过检测")
            return signals

        # 获取该数据类型的所有检测条件
        conditions = self.signal_registry.get_all_for_data_type(data_type)

        if not conditions:
            logger.debug(f"数据类型 {data_type} 无注册的检测条件")
            return signals

        # 收集所有需要的指标
        required_indicators = set()
        for condition in conditions:
            required_indicators.update(condition.required_indicators)

        # 批量计算所需指标
        indicators = self.indicator_engine.calculate(list(required_indicators), data)

        if not indicators:
            logger.debug(f"{code}({name}) 无法计算指标")
            return signals

        # 执行每个检测条件
        for condition in conditions:
            try:
                if not condition.validate_indicators(indicators):
                    logger.debug(f"{code}({name}) 条件 {condition.name} 指标数据不足")
                    continue

                signal = condition.detect(code, name, data, indicators)
                if signal:
                    signals.append(signal)
                    logger.info(f"检测到信号: {signal.message}")

            except Exception as e:
                logger.warning(f"{code}({name}) 条件 {condition.name} 检测异常: {e}")
                continue

        return signals

    def detect_batch(
        self,
        stock_list: List[Dict[str, str]],
        data_type: str,
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, List[Signal]]:
        """
        批量检测多只股票

        Args:
            stock_list: 股票列表 [{"code": "...", "name": "..."}]
            data_type: 数据类型
            data_dict: 数据字典 {code: DataFrame}

        Returns:
            {code: [Signal]} 字典
        """
        results = {}

        for stock in stock_list:
            code = stock.get("code")
            name = stock.get("name", "未知")
            data = data_dict.get(code)

            if data is None:
                continue

            signals = self.detect(code, name, data_type, data)
            if signals:
                results[code] = signals

        return results

    def get_registered_conditions(self, data_type: str = None) -> List[SignalCondition]:
        """
        获取已注册的检测条件

        Args:
            data_type: 数据类型，None 表示所有

        Returns:
            SignalCondition 列表
        """
        if data_type:
            return self.signal_registry.get_all_for_data_type(data_type)
        return list(self.signal_registry._conditions.values())


def create_default_detector_daily(
    short_period: int = 5,
    long_period: int = 20
) -> SignalDetector:
    """
    创建默认的日K信号检测器

    注册 MA金叉/死叉 检测条件。

    Args:
        short_period: 短期均线周期
        long_period: 长期均线周期

    Returns:
        SignalDetector 实例
    """
    from src.indicators.engine import create_default_engine_daily
    from src.detection.golden_cross import GoldenCrossCondition, DeathCrossCondition

    # 创建指标引擎
    indicator_engine = create_default_engine_daily(short_period, long_period)

    # 创建信号注册中心
    signal_registry = SignalRegistry()
    signal_registry.register(GoldenCrossCondition(short_period, long_period, "daily_kline"))
    # 死叉可选注册
    # signal_registry.register(DeathCrossCondition(short_period, long_period, "daily_kline"))

    return SignalDetector(signal_registry, indicator_engine)


def create_default_detector_min15(
    short_days: int = 5,
    long_days: int = 20
) -> SignalDetector:
    """
    创建默认的15分钟K信号检测器

    Args:
        short_days: 短期均线天数
        long_days: 长期均线天数

    Returns:
        SignalDetector 实例
    """
    from src.indicators.engine import create_default_engine_min15
    from src.detection.golden_cross import GoldenCrossCondition

    indicator_engine = create_default_engine_min15(short_days, long_days)

    signal_registry = SignalRegistry()
    signal_registry.register(GoldenCrossCondition(
        short_days * 16, long_days * 16, "min15_kline"
    ))

    return SignalDetector(signal_registry, indicator_engine)


def create_detector_with_macd(
    short_period: int = 5,
    mid_period: int = 10,
    long_period: int = 20,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> SignalDetector:
    """
    创建包含MA和MACD复合检测的日K信号检测器

    检测条件：
    - 条件A：金叉且DIF>0
    - 条件B：DIF上穿0轴且均线多头排列

    Args:
        short_period: 短期均线周期（默认5）
        mid_period: 中期均线周期（默认10）
        long_period: 长期均线周期（默认20）
        fast_period: MACD快线周期（默认12）
        slow_period: MACD慢线周期（默认26）
        signal_period: MACD信号线周期（默认9）

    Returns:
        SignalDetector 实例
    """
    from src.indicators.engine import create_engine_with_macd
    from src.detection.golden_cross_macd import GoldenCrossWithMACDCondition

    # 创建包含MA和MACD的指标引擎
    indicator_engine = create_engine_with_macd(
        short_period, mid_period, long_period, fast_period, slow_period, signal_period
    )

    # 创建信号注册中心
    signal_registry = SignalRegistry()
    signal_registry.register(GoldenCrossWithMACDCondition(
        short_period, mid_period, long_period, "daily_kline"
    ))

    return SignalDetector(signal_registry, indicator_engine)