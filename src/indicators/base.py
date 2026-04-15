"""
指标抽象基类 - 定义指标计算的标准接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

import pandas as pd


class Indicator(ABC):
    """
    指标抽象基类

    所有指标实现都需要继承此基类，实现标准接口。
    支持的指标类型包括：
    - 单值指标：返回一个序列（如 MA、EMA）
    - 多值指标：返回多个序列（如 MACD 返回 DIF、DEA、MACD）
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        指标名称

        如 'MA5', 'MA20', 'MACD', 'KDJ' 等
        用于在 Registry 中唯一标识指标
        """
        pass

    @property
    @abstractmethod
    def required_data(self) -> str:
        """
        所需数据类型

        如 'daily_kline'（日K）、'min15_kline'（15分钟K）等
        用于确定指标适用的数据源
        """
        pass

    @property
    def min_data_length(self) -> int:
        """
        最小数据长度要求

        返回计算指标所需的最小K线数量。
        默认返回 0，子类可根据需要覆盖。
        """
        return 0

    @property
    def output_fields(self) -> List[str]:
        """
        输出字段列表

        返回指标计算结果的字段名列表。
        单值指标默认返回 [name]，多值指标需覆盖此属性。

        如：
        - MA5 返回 ['MA5']
        - MACD 返回 ['DIF', 'DEA', 'MACD']
        """
        return [self.name]

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> Union[pd.Series, Dict[str, pd.Series]]:
        """
        计算指标

        Args:
            data: K线数据 DataFrame，包含 time, open, close, high, low, volume 等列

        Returns:
            单值指标：返回 pd.Series（索引与 data 一致）
            多值指标：返回 Dict[str, pd.Series]（键为 output_fields 中的名称）
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证数据是否满足计算条件

        Args:
            data: K线数据 DataFrame

        Returns:
            True 如果数据满足最小长度要求，False 否则
        """
        if data is None or data.empty:
            return False
        if len(data) < self.min_data_length:
            return False
        return True

    def safe_calculate(self, data: pd.DataFrame) -> Optional[Union[pd.Series, Dict[str, pd.Series]]]:
        """
        安全计算指标（带数据验证）

        Args:
            data: K线数据 DataFrame

        Returns:
            计算结果或 None（数据不满足条件时）
        """
        if not self.validate_data(data):
            return None
        return self.calculate(data)