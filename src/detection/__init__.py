"""
信号检测模块 - 可扩展的信号检测框架

新架构:
- base.py: Signal 数据类 + SignalCondition 抽象基类
- registry.py: 检测条件注册中心
- golden_cross.py: 金叉/死叉检测实现
- detector.py: 信号检测器

向后兼容:
- 原有 detect_cross 函数仍可用（通过 indicators_legacy）
"""

# 导出新框架组件
from src.detection.base import Signal, SignalCondition
from src.detection.registry import SignalRegistry, get_signal_registry, reset_signal_registry
from src.detection.detector import SignalDetector, create_default_detector_daily, create_default_detector_min15, create_detector_with_macd
from src.detection.golden_cross import (
    GoldenCrossCondition,
    DeathCrossCondition,
    create_cross_conditions_daily
)
from src.detection.golden_cross_macd import (
    GoldenCrossWithMACDCondition,
    create_golden_cross_macd_condition_daily
)


# 便捷方法
def get_daily_detector() -> SignalDetector:
    """
    获取默认的日K检测器（复合条件：金叉+DIF>0 或 DIF上穿+多头排列）

    Returns:
        SignalDetector 实例
    """
    import config
    return create_detector_with_macd(
        short_period=config.MA_SHORT_DAYS,
        long_period=config.MA_LONG_DAYS
    )


__all__ = [
    # 新框架
    "Signal",
    "SignalCondition",
    "SignalRegistry",
    "SignalDetector",
    "GoldenCrossCondition",
    "DeathCrossCondition",
    "GoldenCrossWithMACDCondition",
    "get_signal_registry",
    "reset_signal_registry",
    "create_default_detector_daily",
    "create_default_detector_min15",
    "create_cross_conditions_daily",
    "create_golden_cross_macd_condition_daily",
    "create_detector_with_macd",
    "get_daily_detector",
]