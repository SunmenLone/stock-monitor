"""
指标计算引擎 - 批量计算注册的指标
"""
import logging
from typing import Dict, List, Optional, Union

import pandas as pd

from src.indicators.base import Indicator
from src.indicators.registry import IndicatorRegistry

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """
    指标计算引擎

    负责根据注册中心批量计算指标，为信号检测提供数据。

    使用示例:
    >>> registry = IndicatorRegistry()
    >>> registry.register(MAIndicator(5))
    >>> registry.register(MAIndicator(20))
    >>> engine = IndicatorEngine(registry)
    >>> results = engine.calculate_for_data_type("daily_kline", klines_df)
    >>> results["MA5"]  # MA5 序列
    >>> results["MA20"]  # MA20 序列
    """

    def __init__(self, registry: IndicatorRegistry):
        self.registry = registry

    def calculate(self, indicator_names: List[str], data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        批量计算指定指标

        支持按指标名称或输出字段名查找：
        - 如果传入指标名称（如'MA5'、'MACD'），计算该指标
        - 如果传入输出字段名（如'DIF'），查找包含该字段的指标并计算

        Args:
            indicator_names: 指标名称或输出字段名列表
            data: K线数据 DataFrame

        Returns:
            {指标输出字段: pd.Series} 字典
            多值指标的所有输出字段都会包含在结果中
        """
        results = {}

        # 构建查找映射：输出字段名 -> 指标名称
        output_field_to_indicator = {}
        for indicator in self.registry._indicators.values():
            for field in indicator.output_fields:
                output_field_to_indicator[field] = indicator.name

        for name in indicator_names:
            # 先尝试直接查找指标
            indicator = self.registry.get(name)

            # 如果找不到，尝试通过输出字段查找
            if indicator is None:
                indicator_name = output_field_to_indicator.get(name)
                if indicator_name:
                    indicator = self.registry.get(indicator_name)

            if indicator is None:
                logger.warning(f"指标 {name} 未注册，跳过")
                continue

            # 如果该指标已计算过（多值指标的情况），跳过重复计算
            if indicator.name in [self.registry.get(n).name if self.registry.get(n) else None for n in results.keys()]:
                continue

            # 安全计算（带数据验证）
            calc_result = indicator.safe_calculate(data)

            if calc_result is None:
                logger.debug(f"指标 {name} 数据不足，跳过")
                continue

            # 处理单值和多值指标
            if isinstance(calc_result, pd.Series):
                results[indicator.name] = calc_result
            elif isinstance(calc_result, dict):
                for field, series in calc_result.items():
                    results[field] = series

        return results

    def calculate_for_data_type(
        self,
        data_type: str,
        data: pd.DataFrame
    ) -> Dict[str, pd.Series]:
        """
        计算指定数据类型的所有已注册指标

        Args:
            data_type: 数据类型，如 'daily_kline'
            data: K线数据 DataFrame

        Returns:
            {指标输出字段: pd.Series} 字典
        """
        indicators = self.registry.get_all_for_data_type(data_type)
        indicator_names = [ind.name for ind in indicators]
        return self.calculate(indicator_names, data)

    def calculate_single(
        self,
        indicator_name: str,
        data: pd.DataFrame
    ) -> Optional[Union[pd.Series, Dict[str, pd.Series]]]:
        """
        计算单个指标

        Args:
            indicator_name: 指标名称
            data: K线数据 DataFrame

        Returns:
            指标计算结果或 None
        """
        indicator = self.registry.get(indicator_name)
        if indicator is None:
            logger.warning(f"指标 {indicator_name} 未注册")
            return None
        return indicator.safe_calculate(data)

    def get_indicator_info(self, indicator_name: str) -> Optional[Dict]:
        """
        获取指标信息

        Args:
            indicator_name: 指标名称

        Returns:
            指标信息字典或 None
        """
        indicator = self.registry.get(indicator_name)
        if indicator is None:
            return None
        return {
            "name": indicator.name,
            "required_data": indicator.required_data,
            "min_data_length": indicator.min_data_length,
            "output_fields": indicator.output_fields
        }

    def get_all_indicators_info(self) -> List[Dict]:
        """
        获取所有已注册指标的信息

        Returns:
            指标信息列表
        """
        return [
            self.get_indicator_info(name)
            for name in self.registry.list_all()
            if self.get_indicator_info(name) is not None
        ]


def create_default_engine_daily(
    short_period: int = 5,
    long_period: int = 20
) -> IndicatorEngine:
    """
    创建默认的日K指标计算引擎

    注册 MA5 和 MA20 指标。

    Args:
        short_period: 短期均线周期
        long_period: 长期均线周期

    Returns:
        IndicatorEngine 实例
    """
    from src.indicators.ma import MAIndicator

    registry = IndicatorRegistry()
    registry.register(MAIndicator(short_period, "daily_kline"))
    registry.register(MAIndicator(long_period, "daily_kline"))

    return IndicatorEngine(registry)


def create_default_engine_min15(
    short_days: int = 5,
    long_days: int = 20
) -> IndicatorEngine:
    """
    创建默认的15分钟K指标计算引擎

    Args:
        short_days: 短期均线天数（转换为K线数：天数*16）
        long_days: 长期均线天数

    Returns:
        IndicatorEngine 实例
    """
    from src.indicators.ma import MAIndicator

    registry = IndicatorRegistry()
    registry.register(MAIndicator(short_days * 16, "min15_kline"))
    registry.register(MAIndicator(long_days * 16, "min15_kline"))

    return IndicatorEngine(registry)


def create_engine_with_macd(
    short_period: int = 5,
    mid_period: int = 10,
    long_period: int = 20,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> IndicatorEngine:
    """
    创建包含MA和MACD的日K指标计算引擎

    注册 MA5、MA10、MA20 和 MACD(DIF, DEA, MACD) 指标。

    Args:
        short_period: 短期均线周期（默认5）
        mid_period: 中期均线周期（默认10）
        long_period: 长期均线周期（默认20）
        fast_period: MACD快线周期（默认12）
        slow_period: MACD慢线周期（默认26）
        signal_period: MACD信号线周期（默认9）

    Returns:
        IndicatorEngine 实例
    """
    from src.indicators.ma import MAIndicator
    from src.indicators.macd import MACDIndicator

    registry = IndicatorRegistry()
    registry.register(MAIndicator(short_period, "daily_kline"))
    registry.register(MAIndicator(mid_period, "daily_kline"))
    registry.register(MAIndicator(long_period, "daily_kline"))
    registry.register(MACDIndicator(fast_period, slow_period, signal_period, "daily_kline"))

    return IndicatorEngine(registry)