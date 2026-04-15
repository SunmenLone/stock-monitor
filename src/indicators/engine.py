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

        Args:
            indicator_names: 指标名称列表
            data: K线数据 DataFrame

        Returns:
            {指标输出字段: pd.Series} 字典
            多值指标的所有输出字段都会包含在结果中
        """
        results = {}

        for name in indicator_names:
            indicator = self.registry.get(name)
            if indicator is None:
                logger.warning(f"指标 {name} 未注册，跳过")
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