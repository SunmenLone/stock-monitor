"""
日K线扫描器模块
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import config
from src.data_sync_service import DataSyncService
from src.daily_state import DailyScanState
from src.indicators import calculate_indicators_daily, detect_cross, get_current_values
from src.notifier import create_notifier

logger = logging.getLogger(__name__)


class DailyScanner:
    """日K线扫描器"""

    def __init__(self):
        self.data_sync = DataSyncService()  # 使用数据同步服务
        self.state = DailyScanState()
        self.notifier = create_notifier()

    def _get_current_date(self) -> str:
        """获取当前日期"""
        return datetime.now().strftime("%Y-%m-%d")

    def scan_daily(self) -> Dict:
        """
        执行日K金叉检测

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

        # 1. 检查当天是否已完成 -> 跳过，返回上次结果
        if self.state.is_completed(date):
            logger.info(f"当天 {date} 已完成检测，跳过")
            result = self.state.get_result()
            result["elapsed"] = 0
            return result

        # 2. 新的一天？重置状态
        state_date = self.state.get_date()
        if state_date != date:
            stocks = self.data_sync.get_hs300_stocks()
            self.state.reset_for_new_day(stocks)
            # 清理过期缓存
            self.data_sync.clear_expired_cache()

        # 3. 获取待检测股票列表（使用副本，避免遍历中修改原列表）
        pending_codes = list(self.state.get_pending_stocks())
        total = self.state.get_result()["total"]

        # 4. 获取股票名称映射（用于播报）
        stock_map = self.data_sync.get_stock_names()

        # 5. 播报"开始检测"
        result_before = self.state.get_result()
        self.notifier.notify_daily_scan_start(
            total=total,
            pending=len(pending_codes),
            fetched=result_before.get("fetched_count", 0)
        )

        logger.info(f"开始日K检测: {date}, 待检测 {len(pending_codes)} 只股票")

        # 6. 逐个检测（使用数据同步服务）
        for code in pending_codes:
            name = stock_map.get(code, "未知")

            try:
                # 使用数据同步服务获取数据
                sync_result = self.data_sync.sync_stock_data(code, name)

                if not sync_result.has_data():
                    logger.warning(f"{code}({name}) 获取日K失败，跳过")
                    continue

                klines = sync_result.data

                # 计算MA5/MA20（使用日K均线周期）
                indicators = calculate_indicators_daily(klines)
                if indicators is None:
                    logger.debug(f"{code}({name}) 日K数据不足，跳过")
                    continue

                ma_short, ma_long = indicators

                # 检测金叉
                golden_cross, _ = detect_cross(ma_short, ma_long)

                signal = None
                if golden_cross:
                    curr_ma_short, curr_ma_long = get_current_values(ma_short, ma_long)
                    close = klines["close"].iloc[-1]
                    last_date = klines["time"].iloc[-1]

                    signal = {
                        "code": code,
                        "name": name,
                        "ma5": round(curr_ma_short, 2),
                        "ma20": round(curr_ma_long, 2),
                        "close": round(close, 2),
                        "date": str(last_date)[:10] if len(str(last_date)) >= 10 else str(last_date)
                    }

                # 更新进度
                self.state.update_progress(code, signal)

            except Exception as e:
                logger.warning(f"检测 {code}({name}) 异常: {e}")
                continue

        elapsed = time.time() - start_time

        # 7. 获取最终结果
        result = self.state.get_result()
        result["elapsed"] = elapsed

        # 8. 如果全部完成，标记当天已完成
        if result["pending_count"] == 0:
            self.state.mark_completed(date)
            result["completed"] = True  # 更新结果状态
            logger.info(f"当天 {date} 检测完成，耗时 {elapsed:.1f}秒")

        # 9. 播报完成统计
        self.notifier.notify_daily_scan_complete(result)

        return result

    def run_once(self) -> Dict:
        """
        执行一次日K检测（启动时调用）

        Returns:
            检测结果
        """
        logger.info("执行日K检测...")
        return self.scan_daily()