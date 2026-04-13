"""
定时调度模块
"""
import logging
import schedule
import time
from datetime import datetime
from typing import Callable, Optional

import config
from src.data_source import DataSource

logger = logging.getLogger(__name__)


class Scheduler:
    """定时任务调度器"""

    def __init__(self, scan_func: Callable, backtrack_func: Optional[Callable] = None):
        """
        Args:
            scan_func: 扫描函数（定时任务使用），返回信号列表
            backtrack_func: 回溯扫描函数（启动时使用），返回信号列表
        """
        self.scan_func = scan_func
        self.backtrack_func = backtrack_func or scan_func
        self.data_source = DataSource()
        self._running = False

    def _is_trade_time(self) -> bool:
        """检查当前是否在交易时间"""
        return self.data_source.is_trade_time()

    def _do_scan(self) -> None:
        """执行扫描任务"""
        dt = datetime.now()

        # 检查是否交易日
        if not self.data_source.is_trade_day(dt):
            logger.info(f"今日 {dt.strftime('%Y-%m-%d')} 不是交易日，跳过")
            return

        # 检查是否交易时间
        if not self._is_trade_time():
            logger.info(f"当前时间 {dt.strftime('%H:%M')} 不在交易时间，跳过")
            return

        logger.info(f"定时扫描触发: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            self.scan_func()
        except Exception as e:
            logger.error(f"扫描任务执行异常: {e}")

    def setup_schedule(self) -> None:
        """设置定时任务"""
        # 每小时执行
        # 使用schedule库
        schedule.every(config.SCAN_INTERVAL_HOURS).hours.do(self._do_scan)

        # 或者更精确地在交易时间的整点执行
        # 上午：10:30, 11:30
        schedule.every().day.at("10:30").do(self._do_scan)
        schedule.every().day.at("11:30").do(self._do_scan)
        # 下午：14:00, 15:00（收盘前）
        schedule.every().day.at("14:00").do(self._do_scan)

        logger.info(f"定时任务已设置: 10:30, 11:30, 14:00 执行扫描")

    def run(self) -> None:
        """运行调度器"""
        self._running = True

        logger.info("调度器启动")

        while self._running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        logger.info("调度器停止")

    def run_once(self) -> None:
        """启动时立即执行一次扫描（重置状态，允许重新通知）"""
        logger.info("启动时立即执行扫描...")

        # 启动扫描统一使用回溯函数（重置状态，允许重新通知）
        try:
            self.backtrack_func()
        except Exception as e:
            logger.error(f"启动扫描执行异常: {e}")