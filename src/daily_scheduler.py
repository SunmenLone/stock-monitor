"""
日K线检测调度模块
"""
import logging
import schedule
import time
from datetime import datetime
from typing import Callable

import config
from src.data_source import DataSource

logger = logging.getLogger(__name__)


class DailyScheduler:
    """日K检测调度器"""

    def __init__(self, scan_func: Callable):
        """
        Args:
            scan_func: 日K扫描函数，返回检测结果
        """
        self.scan_func = scan_func
        self.data_source = DataSource()
        self._running = False

    def _is_trade_day(self) -> bool:
        """检查当前是否为交易日"""
        return self.data_source.is_trade_day()

    def _do_scan(self) -> None:
        """执行日K扫描任务"""
        dt = datetime.now()

        # 检查是否交易日
        if not self._is_trade_day():
            logger.info(f"今日 {dt.strftime('%Y-%m-%d')} 不是交易日，跳过日K检测")
            return

        logger.info(f"日K检测触发: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            self.scan_func()
        except Exception as e:
            logger.error(f"日K检测执行异常: {e}")

    def _refresh_trade_dates(self) -> None:
        """每日10:00刷新交易日历缓存"""
        logger.info("定时刷新交易日历...")
        try:
            self.data_source.get_trade_dates(force_refresh=True)
            # 判断并打印今日是否交易日
            today_str = datetime.now().strftime('%Y-%m-%d')
            is_today_trade_day = self.data_source.is_trade_day()
            if is_today_trade_day:
                logger.info(f"今日 {today_str} 是交易日")
            else:
                logger.info(f"今日 {today_str} 不是交易日")
        except Exception as e:
            logger.error(f"交易日历刷新失败: {e}")

    def setup_schedule(self) -> None:
        """设置定时任务（16-19点检测 + 10:00刷新交易日历）"""
        schedule.every().day.at("10:00").do(self._refresh_trade_dates)
        logger.info("交易日历刷新任务已设置: 10:00")

        for scan_time in config.DAILY_SCAN_TIMES:
            schedule.every().day.at(scan_time).do(self._do_scan)
            logger.info(f"日K检测任务已设置: {scan_time}")

        logger.info(f"日K检测定时任务已设置: {config.DAILY_SCAN_TIMES}")

    def run_once(self) -> None:
        """启动时立即执行一次日K检测（静默模式）"""
        logger.info("启动时执行日K检测...")

        try:
            # 启动时使用静默模式：只播报信号通知，跳过启动/完成通知
            self.scan_func(silent_mode=True)
        except Exception as e:
            logger.error(f"启动时日K检测执行异常: {e}")

    def run(self) -> None:
        """运行调度器"""
        self._running = True

        logger.info("日K调度器启动")

        while self._running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        logger.info("日K调度器停止")