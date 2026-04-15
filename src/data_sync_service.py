"""
数据同步服务模块 - 分离数据同步与检测逻辑
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.data_source import DataSource
from src.daily_cache import DailyKlineCache

logger = logging.getLogger(__name__)


class DataSyncResult:
    """数据同步结果"""

    def __init__(
        self,
        code: str,
        name: str,
        data: Optional[pd.DataFrame],
        last_kline_time: Optional[str],
        is_updated: bool,
        error: Optional[str] = None
    ):
        self.code = code
        self.name = name
        self.data = data
        self.last_kline_time = last_kline_time
        self.is_updated = is_updated  # 是否进行了数据更新
        self.error = error

    def has_data(self) -> bool:
        """是否有有效数据"""
        return self.data is not None and not self.data.empty

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "code": self.code,
            "name": self.name,
            "data": self.data,
            "last_kline_time": self.last_kline_time,
            "is_updated": self.is_updated,
            "error": self.error
        }


class DataSyncService:
    """
    数据同步服务 - 负责股票数据的获取与缓存管理

    职责：
    1. 检查缓存有效性
    2. 增量拉取新数据
    3. 合并新旧数据并缓存
    """

    def __init__(self):
        self.data_source = DataSource()
        self.cache = DailyKlineCache()

    def sync_stock_data(
        self,
        code: str,
        name: str = "未知",
        force_update: bool = False
    ) -> DataSyncResult:
        """
        同步单只股票的日K数据

        Args:
            code: 股票代码
            name: 股票名称（可选）
            force_update: 强制更新（忽略缓存有效性检查）

        Returns:
            DataSyncResult: 同步结果，包含数据和状态信息
        """
        try:
            # 1. 检查缓存
            cached = self.cache.get_with_check(code)
            old_data = cached.get("data")
            last_kline_time = cached.get("last_kline_time")
            needs_update = cached.get("needs_update", True)

            # 2. 判断是否需要拉取新数据
            should_fetch = force_update or needs_update or old_data is None

            if not should_fetch:
                # 缓存有效，直接返回
                logger.debug(f"{code}({name}) 缓存有效，无需更新")
                return DataSyncResult(
                    code=code,
                    name=name,
                    data=old_data,
                    last_kline_time=last_kline_time,
                    is_updated=False
                )

            # 3. 增量拉取
            logger.debug(
                f"拉取 {code}({name}) 日K数据..." +
                (f" 从 {last_kline_time}" if last_kline_time else "")
            )
            new_data = self.data_source.get_stock_daily_klines(
                code,
                start_date=last_kline_time  # 增量拉取起始日期
            )

            # 4. 合并数据
            if new_data is not None and not new_data.empty:
                if old_data is not None and not old_data.empty:
                    merged_data = self.cache.merge_and_set(code, old_data, new_data)
                else:
                    self.cache.set(code, new_data)
                    merged_data = new_data

                # 提取最新K线时间
                new_last_time = self._extract_last_time(merged_data)

                logger.debug(
                    f"{code}({name}) 数据更新完成: " +
                    f"旧{len(old_data) if old_data else 0}条 + 新{len(new_data)}条 = {len(merged_data)}条"
                )

                return DataSyncResult(
                    code=code,
                    name=name,
                    data=merged_data,
                    last_kline_time=new_last_time,
                    is_updated=True
                )
            else:
                # 拉取失败，使用旧缓存
                if old_data is not None and not old_data.empty:
                    logger.warning(f"{code}({name}) 拉取新数据失败，使用旧缓存")
                    return DataSyncResult(
                        code=code,
                        name=name,
                        data=old_data,
                        last_kline_time=last_kline_time,
                        is_updated=False
                    )
                else:
                    logger.warning(f"{code}({name}) 获取数据失败，无缓存")
                    return DataSyncResult(
                        code=code,
                        name=name,
                        data=None,
                        last_kline_time=None,
                        is_updated=False,
                        error="数据获取失败"
                    )

        except Exception as e:
            logger.warning(f"同步 {code}({name}) 数据异常: {e}")
            return DataSyncResult(
                code=code,
                name=name,
                data=None,
                last_kline_time=None,
                is_updated=False,
                error=str(e)
            )

    def sync_batch(
        self,
        stock_list: List[Dict[str, str]],
        force_update: bool = False
    ) -> Tuple[List[DataSyncResult], int, int]:
        """
        批量同步股票数据

        Args:
            stock_list: 股票列表 [{"code": "000001", "name": "平安银行"}, ...]
            force_update: 强制更新

        Returns:
            (results, success_count, update_count)
            - results: 所有同步结果列表
            - success_count: 成功获取数据的数量
            - update_count: 进行了数据更新的数量
        """
        results = []
        success_count = 0
        update_count = 0

        for stock in stock_list:
            code = stock.get("code")
            name = stock.get("name", "未知")

            result = self.sync_stock_data(code, name, force_update)
            results.append(result)

            if result.has_data():
                success_count += 1
            if result.is_updated:
                update_count += 1

        logger.info(
            f"批量同步完成: 总数 {len(stock_list)}, " +
            f"成功 {success_count}, 更新 {update_count}"
        )

        return results, success_count, update_count

    def get_stock_names(self) -> Dict[str, str]:
        """
        获取股票名称映射

        Returns:
            {code: name} 字典
        """
        stocks = self.data_source.get_hs300_stocks()
        return {s["code"]: s["name"] for s in stocks}

    def get_hs300_stocks(self) -> List[Dict[str, str]]:
        """
        获取沪深300股票列表

        Returns:
            [{"code": "000001", "name": "平安银行"}, ...]
        """
        return self.data_source.get_hs300_stocks()

    def clear_expired_cache(self) -> int:
        """
        清理过期缓存（保留数据，仅更新日期字段）

        Returns:
            更新的缓存数量
        """
        return self.cache.clear_expired()

    def _extract_last_time(self, df: pd.DataFrame) -> Optional[str]:
        """
        从K线数据提取最后时间

        Args:
            df: K线DataFrame

        Returns:
            最后时间字符串，如 "2026-04-14"
        """
        if df is None or df.empty or "time" not in df.columns:
            return None

        try:
            last_time = df["time"].max()
            time_str = str(last_time)
            # 日K时间格式为日期 "YYYY-MM-DD"
            if len(time_str) >= 10:
                return time_str[:10]
            return time_str
        except Exception:
            return None

    def get_current_date(self) -> str:
        """获取当前日期"""
        return datetime.now().strftime("%Y-%m-%d")