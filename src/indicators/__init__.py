"""
指标模块 - 可扩展的技术指标计算框架

新架构:
- base.py: 指标抽象基类
- registry.py: 指标注册中心
- ma.py: 均线指标实现
- engine.py: 指标计算引擎

向后兼容:
- 保持原有函数 calculate_indicators_daily 等可用
"""

# 导出新框架组件
from src.indicators.base import Indicator
from src.indicators.registry import IndicatorRegistry, get_registry, reset_registry
from src.indicators.engine import IndicatorEngine, create_default_engine_daily
from src.indicators.ma import MAIndicator, EMAIndicator, create_ma_indicators_daily

# 导入原有函数（向后兼容）
from src.indicators_legacy import (
    calculate_ma,
    detect_cross,
    get_current_values,
    get_cross_status,
    calculate_indicators_daily,
)


# 便捷方法：创建默认日K引擎
def get_daily_indicator_engine() -> IndicatorEngine:
    """
    获取默认的日K指标引擎（MA5 + MA20）

    Returns:
        IndicatorEngine 实例
    """
    import config
    return create_default_engine_daily(
        short_period=config.MA_SHORT_DAYS,
        long_period=config.MA_LONG_DAYS
    )


__all__ = [
    # 新框架
    "Indicator",
    "IndicatorRegistry",
    "IndicatorEngine",
    "MAIndicator",
    "EMAIndicator",
    "get_registry",
    "reset_registry",
    "create_default_engine_daily",
    "create_ma_indicators_daily",
    "get_daily_indicator_engine",
    # 原有函数（向后兼容）
    "calculate_ma",
    "detect_cross",
    "get_current_values",
    "get_cross_status",
    "calculate_indicators_daily",
]