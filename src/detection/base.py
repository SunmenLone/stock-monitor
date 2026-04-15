"""
信号检测条件抽象基类 - 定义信号检测的标准接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class Signal:
    """
    信号数据类

    表示检测到的交易信号（如金叉、死叉等）
    """

    # 基本信息
    code: str  # 股票代码
    name: str  # 股票名称
    condition: str  # 检测条件名称（如 'golden_cross'）

    # 信号数据
    values: Dict[str, float] = field(default_factory=dict)  # 相关指标值
    data_time: str = ""  # K线时间（最新一根K线的时间）

    # 元数据
    detected_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    message: str = ""  # 信号描述消息

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "code": self.code,
            "name": self.name,
            "condition": self.condition,
            "values": self.values,
            "data_time": self.data_time,
            "detected_at": self.detected_at,
            "message": self.message
        }

    def format_message(self) -> str:
        """格式化信号消息"""
        if self.message:
            return self.message

        # 自动生成消息
        value_str = ", ".join(f"{k}={v:.2f}" for k, v in self.values.items())
        return f"{self.code}({self.name}) {self.condition}: {value_str} @ {self.data_time}"


class SignalCondition(ABC):
    """
    信号检测条件抽象基类

    所有检测条件实现都需要继承此基类，实现标准接口。

    检测条件与指标的关系：
    - 检测条件依赖指标计算结果
    - required_indicators 指定需要哪些指标
    - SignalDetector 会自动计算所需指标后调用 detect()
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        检测条件名称

        如 'golden_cross', 'death_cross', 'macd_cross' 等
        用于在 Registry 中唯一标识检测条件
        """
        pass

    @property
    @abstractmethod
    def required_indicators(self) -> List[str]:
        """
        所需指标列表

        返回此检测条件需要的指标名称列表。
        SignalDetector 会根据此列表批量计算指标。

        如：
        - 金叉检测需要 ['MA5', 'MA20']
        - MACD金叉检测需要 ['DIF', 'DEA']
        """
        pass

    @property
    def data_type(self) -> str:
        """
        适用数据类型

        默认返回 'daily_kline'，子类可覆盖。
        用于筛选适用的检测条件。
        """
        return "daily_kline"

    @property
    def description(self) -> str:
        """
        检测条件描述

        用于生成信号消息。
        """
        return f"{self.name} signal"

    @abstractmethod
    def detect(
        self,
        code: str,
        name: str,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series]
    ) -> Optional[Signal]:
        """
        执行信号检测

        Args:
            code: 股票代码
            name: 股票名称
            data: K线数据 DataFrame
            indicators: 已计算的指标字典 {指标名: 值序列}

        Returns:
            Signal 对象或 None（未检测到信号）
        """
        pass

    def validate_indicators(self, indicators: Dict[str, pd.Series]) -> bool:
        """
        验证指标数据是否满足检测条件

        Args:
            indicators: 指标字典

        Returns:
            True 如果所有必需指标都存在且有足够数据
        """
        for ind_name in self.required_indicators:
            if ind_name not in indicators:
                return False
            series = indicators[ind_name]
            if series is None or len(series) < 2:  # 交叉检测至少需要2个点
                return False
        return True