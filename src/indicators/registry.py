"""
指标注册中心 - 管理可用指标列表
"""
import logging
from typing import Dict, List, Optional

from src.indicators.base import Indicator

logger = logging.getLogger(__name__)


class IndicatorRegistry:
    """
    指标注册中心

    管理:
    1. 指标注册：register()
    2. 指标获取：get()
    3. 按数据类型筛选：get_all_for_data_type()
    4. 列出所有指标：list_all()

    使用示例:
    >>> registry = IndicatorRegistry()
    >>> registry.register(MAIndicator(5))
    >>> registry.register(MAIndicator(20))
    >>> registry.list_all()
    ['MA5', 'MA20']
    """

    def __init__(self):
        self._indicators: Dict[str, Indicator] = {}

    def register(self, indicator: Indicator) -> None:
        """
        注册指标

        Args:
            indicator: Indicator 实例

        Raises:
            ValueError: 如果指标名称已存在
        """
        name = indicator.name
        if name in self._indicators:
            logger.warning(f"指标 {name} 已存在，将被覆盖")
        self._indicators[name] = indicator
        logger.debug(f"注册指标: {name}")

    def unregister(self, name: str) -> bool:
        """
        取消注册指标

        Args:
            name: 指标名称

        Returns:
            True 如果成功移除，False 如果指标不存在
        """
        if name in self._indicators:
            del self._indicators[name]
            logger.debug(f"取消注册指标: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[Indicator]:
        """
        获取指标

        Args:
            name: 指标名称

        Returns:
            Indicator 实例或 None（不存在时）
        """
        return self._indicators.get(name)

    def get_all_for_data_type(self, data_type: str) -> List[Indicator]:
        """
        获取指定数据类型的所有指标

        Args:
            data_type: 数据类型，如 'daily_kline', 'min15_kline'

        Returns:
            Indicator 实例列表
        """
        return [
            ind for ind in self._indicators.values()
            if ind.required_data == data_type
        ]

    def list_all(self) -> List[str]:
        """
        列出所有已注册指标名称

        Returns:
            指标名称列表
        """
        return list(self._indicators.keys())

    def list_all_for_data_type(self, data_type: str) -> List[str]:
        """
        列出指定数据类型的所有指标名称

        Args:
            data_type: 数据类型

        Returns:
            指标名称列表
        """
        return [
            name for name, ind in self._indicators.items()
            if ind.required_data == data_type
        ]

    def get_required_fields(self, indicator_names: List[str]) -> List[str]:
        """
        获取指定指标的输出字段列表

        Args:
            indicator_names: 指标名称列表

        Returns:
            所有输出字段的合并列表
        """
        fields = []
        for name in indicator_names:
            indicator = self.get(name)
            if indicator:
                fields.extend(indicator.output_fields)
        return fields

    def count(self) -> int:
        """返回已注册指标数量"""
        return len(self._indicators)

    def clear(self) -> None:
        """清空所有注册的指标"""
        self._indicators.clear()
        logger.debug("清空指标注册中心")


# 全局注册中心实例
_global_registry: Optional[IndicatorRegistry] = None


def get_registry() -> IndicatorRegistry:
    """
    获取全局指标注册中心

    Returns:
        IndicatorRegistry 实例
    """
    if _global_registry is None:
        _global_registry = IndicatorRegistry()
    return _global_registry


def reset_registry() -> None:
    """重置全局注册中心"""
    _global_registry = None