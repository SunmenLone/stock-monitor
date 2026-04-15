"""
信号检测条件注册中心 - 管理可用的检测条件
"""
import logging
from typing import Dict, List, Optional, Set

from src.detection.base import SignalCondition

logger = logging.getLogger(__name__)


class SignalRegistry:
    """
    信号检测条件注册中心

    管理可用的检测条件：
    1. 条件注册：register()
    2. 条件获取：get()
    3. 按数据类型筛选：get_all_for_data_type()
    4. 列出所有条件：list_all()
    5. 获取所需指标：get_required_indicators()

    使用示例:
    >>> registry = SignalRegistry()
    >>> registry.register(GoldenCrossCondition())
    >>> registry.list_all()
    ['golden_cross']
    """

    def __init__(self):
        self._conditions: Dict[str, SignalCondition] = {}

    def register(self, condition: SignalCondition) -> None:
        """
        注册检测条件

        Args:
            condition: SignalCondition 实例
        """
        name = condition.name
        if name in self._conditions:
            logger.warning(f"检测条件 {name} 已存在，将被覆盖")
        self._conditions[name] = condition
        logger.debug(f"注册检测条件: {name}")

    def unregister(self, name: str) -> bool:
        """
        取消注册检测条件

        Args:
            name: 条件名称

        Returns:
            True 如果成功移除，False 如果不存在
        """
        if name in self._conditions:
            del self._conditions[name]
            logger.debug(f"取消注册检测条件: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[SignalCondition]:
        """
        获取检测条件

        Args:
            name: 条件名称

        Returns:
            SignalCondition 实例或 None
        """
        return self._conditions.get(name)

    def get_all_for_data_type(self, data_type: str) -> List[SignalCondition]:
        """
        获取指定数据类型的所有检测条件

        Args:
            data_type: 数据类型，如 'daily_kline'

        Returns:
            SignalCondition 实例列表
        """
        return [
            cond for cond in self._conditions.values()
            if cond.data_type == data_type
        ]

    def list_all(self) -> List[str]:
        """
        列出所有已注册检测条件名称

        Returns:
            条件名称列表
        """
        return list(self._conditions.keys())

    def list_all_for_data_type(self, data_type: str) -> List[str]:
        """
        列出指定数据类型的所有条件名称

        Args:
            data_type: 数据类型

        Returns:
            条件名称列表
        """
        return [
            name for name, cond in self._conditions.items()
            if cond.data_type == data_type
        ]

    def get_required_indicators(self, condition_names: List[str] = None) -> Set[str]:
        """
        获取指定条件所需的指标集合

        Args:
            condition_names: 条件名称列表，None 表示所有条件

        Returns:
            所需指标名称集合
        """
        if condition_names is None:
            conditions = self._conditions.values()
        else:
            conditions = [self.get(name) for name in condition_names]
            conditions = [c for c in conditions if c is not None]

        required = set()
        for cond in conditions:
            required.update(cond.required_indicators)

        return required

    def count(self) -> int:
        """返回已注册条件数量"""
        return len(self._conditions)

    def clear(self) -> None:
        """清空所有注册的条件"""
        self._conditions.clear()
        logger.debug("清空信号检测条件注册中心")


# 全局注册中心实例
_global_registry: Optional[SignalRegistry] = None


def get_signal_registry() -> SignalRegistry:
    """
    获取全局信号注册中心

    Returns:
        SignalRegistry 实例
    """
    if _global_registry is None:
        _global_registry = SignalRegistry()
    return _global_registry


def reset_signal_registry() -> None:
    """重置全局信号注册中心"""
    _global_registry = None