"""
扫描编排器 - 整合数据同步和信号检测
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

import config
from src.data_sync_service import DataSyncService, DataSyncResult
from src.indicators.engine import IndicatorEngine, create_default_engine_daily
from src.detection.detector import SignalDetector, create_default_detector_daily
from src.detection.base import Signal
from src.daily_state import DailyScanState
from src.notifier import create_notifier

logger = logging.getLogger(__name__)


class ScanOrchestrator:
    """
    扫描编排器

    整合数据同步层和信号检测层，编排完整的检测流程：
    1. 数据同步：DataSyncService
    2. 指标计算：IndicatorEngine
    3. 信号检测：SignalDetector
    4. 状态管理：DailyScanState
    5. 通知：Notifier

    使用示例:
    >>> orchestrator = ScanOrchestrator()
    >>> result = orchestrator.orchestrate_daily_scan()
    >>> print(result["signals"])
    """

    def __init__(
        self,
        data_sync: DataSyncService = None,
        signal_detector: SignalDetector = None,
        state: DailyScanState = None,
        notifier = None
    ):
        # 使用默认实现或自定义实现
        self.data_sync = data_sync or DataSyncService()
        self.signal_detector = signal_detector or create_default_detector_daily()
        self.state = state or DailyScanState()
        self.notifier = notifier or create_notifier()

    def _get_current_date(self) -> str:
        """获取当前日期"""
        return datetime.now().strftime("%Y-%m-%d")

    def orchestrate_daily_scan(self) -> Dict:
        """
        编排日K检测流程

        流程:
        1. 检查是否已完成
        2. 新的一天初始化
        3. 数据同步
        4. 指标计算
        5. 信号检测
        6. 状态更新
        7. 完成通知

        Returns:
            {
                "date": str,
                "completed": bool,
                "total": int,
                "fetched_count": int,
                "detected_count": int,
                "pending_count": int,
                "signals_count": int,
                "signals": List,
                "elapsed": float
            }
        """
        date = self._get_current_date()
        start_time = time.time()

        # 1. 检查是否已完成
        if self.state.is_completed(date):
            logger.info(f"当天 {date} 已完成检测，跳过")
            result = self.state.get_result()
            result["elapsed"] = 0
            return result

        # 2. 新的一天初始化
        state_date = self.state.get_date()
        if state_date != date:
            stocks = self.data_sync.get_hs300_stocks()
            self.state.reset_for_new_day(stocks)
            self.data_sync.clear_expired_cache()

        # 3. 获取待检测股票
        pending_codes = list(self.state.get_pending_stocks())
        total = self.state.get_result()["total"]
        stock_map = self.data_sync.get_stock_names()

        # 4. 播报开始
        result_before = self.state.get_result()
        self.notifier.notify_daily_scan_start(
            total=total,
            pending=len(pending_codes),
            fetched=result_before.get("fetched_count", 0)
        )

        logger.info(f"开始日K检测: {date}, 待检测 {len(pending_codes)} 只股票")

        # 5. 逐个检测
        for code in pending_codes:
            name = stock_map.get(code, "未知")

            try:
                # 5.1 数据同步
                sync_result = self.data_sync.sync_stock_data(code, name)

                if not sync_result.has_data():
                    logger.warning(f"{code}({name}) 获取日K失败，跳过")
                    continue

                data = sync_result.data

                # 5.2 信号检测
                signals = self.signal_detector.detect(
                    code=code,
                    name=name,
                    data_type="daily_kline",
                    data=data
                )

                # 5.3 转换为旧格式（向后兼容）
                signal_dict = None
                if signals:
                    # 取第一个信号（当前只有金叉）
                    sig = signals[0]
                    signal_dict = {
                        "code": sig.code,
                        "name": sig.name,
                        "ma5": sig.values.get("MA5", 0),
                        "ma20": sig.values.get("MA20", 0),
                        "close": sig.values.get("close", 0),
                        "date": sig.data_time
                    }

                # 5.4 更新进度
                self.state.update_progress(code, signal_dict)

            except Exception as e:
                logger.warning(f"检测 {code}({name}) 异常: {e}")
                continue

        elapsed = time.time() - start_time

        # 6. 获取最终结果
        result = self.state.get_result()
        result["elapsed"] = elapsed

        # 7. 标记完成
        if result["pending_count"] == 0:
            self.state.mark_completed(date)
            result["completed"] = True
            logger.info(f"当天 {date} 检测完成，耗时 {elapsed:.1f}秒")

        # 8. 播报完成
        self.notifier.notify_daily_scan_complete(result)

        return result

    def run_once(self) -> Dict:
        """执行一次检测"""
        logger.info("执行日K检测...")
        return self.orchestrate_daily_scan()

    def sync_only(self, stock_list: List[Dict[str, str]] = None) -> Dict:
        """
        仅执行数据同步（不检测信号）

        Args:
            stock_list: 股票列表，None 表示全部

        Returns:
            {
                "synced_count": int,
                "update_count": int,
                "failed_count": int,
                "elapsed": float
            }
        """
        if stock_list is None:
            stock_list = self.data_sync.get_hs300_stocks()

        start_time = time.time()
        results, success_count, update_count = self.data_sync.sync_batch(stock_list)
        elapsed = time.time() - start_time

        failed_count = len(stock_list) - success_count

        logger.info(f"数据同步完成: 成功 {success_count}, 更新 {update_count}, 失败 {failed_count}")

        return {
            "synced_count": success_count,
            "update_count": update_count,
            "failed_count": failed_count,
            "elapsed": elapsed
        }

    def detect_only(self, code: str, name: str, data: pd.DataFrame) -> List[Signal]:
        """
        仅执行信号检测（数据已就绪）

        Args:
            code: 股票代码
            name: 股票名称
            data: K线数据

        Returns:
            Signal 列表
        """
        return self.signal_detector.detect(code, name, "daily_kline", data)


def create_default_orchestrator() -> ScanOrchestrator:
    """
    创建默认的扫描编排器

    Returns:
        ScanOrchestrator 实例（使用默认配置）
    """
    return ScanOrchestrator()