"""
日K线扫描器模块
"""
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

import config
from src.data_source import DataSource
from src.daily_cache import DailyKlineCache
from src.daily_state import DailyScanState
from src.indicators import calculate_indicators_daily, detect_cross, get_current_values
from src.notifier import create_notifier

logger = logging.getLogger(__name__)


def _random_delay() -> float:
    """生成随机延迟时间"""
    return random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX)


class DailyScanner:
    """日K线扫描器"""

    def __init__(self):
        self.data_source = DataSource()
        self.cache = DailyKlineCache()
        self.state = DailyScanState()
        self.notifier = create_notifier()

logger = logging.getLogger(__name__)


def _random_delay() -> float:
    """生成随机延迟时间"""
    return random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX)


class DailyScanner:
    """日K线扫描器"""

    def __init__(self):
        self.data_source = DataSource()
        self.cache = DailyKlineCache()
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
            stocks = self.data_source.get_hs300_stocks()
            self.state.reset_for_new_day(stocks)
            # 清理过期缓存
            self.cache.clear_expired()

        # 3. 获取待检测股票列表
        pending_codes = self.state.get_pending_stocks()
        total = self.state.get_result()["total"]

        # 4. 获取股票名称映射（用于播报）
        stocks = self.data_source.get_hs300_stocks()
        stock_map = {s["code"]: s["name"] for s in stocks}

        # 5. 播报"开始检测"
        result_before = self.state.get_result()
        self.notifier.notify_daily_scan_start(
            total=total,
            pending=len(pending_codes),
            fetched=result_before.get("fetched_count", 0)
        )

        logger.info(f"开始日K检测: {date}, 待检测 {len(pending_codes)} 只股票")

        # 6. 逐个检测（使用缓存）
        for code in pending_codes:
            name = stock_map.get(code, "未知")

            try:
                # 检查缓存
                cached = self.cache.get_with_check(code)
                klines = cached["data"]

                # 缓存需要更新或不存在 -> 从数据源拉取
                if cached["needs_update"] or klines is None:
                    logger.debug(f"拉取 {code}({name}) 日K数据...")
                    klines = self.data_source.get_stock_daily_klines(code)
                    if klines is not None:
                        self.cache.set(code, klines)

                if klines is None or klines.empty:
                    logger.warning(f"{code}({name}) 获取日K失败，跳过")
                    continue

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

                # 随机延迟
                time.sleep(_random_delay())

            except Exception as e:
                logger.warning(f"检测 {code}({name}) 异常: {e}")
                time.sleep(config.REQUEST_DELAY_ON_ERROR)
                continue

        elapsed = time.time() - start_time

        # 7. 获取最终结果
        result = self.state.get_result()
        result["elapsed"] = elapsed

        # 8. 播报完成统计
        self.notifier.notify_daily_scan_complete(result)

        # 9. 如果全部完成，标记当天已完成
        if result["pending_count"] == 0:
            self.state.mark_completed(date)
            logger.info(f"当天 {date} 检测完成，耗时 {elapsed:.1f}秒")

        return result

    def run_once(self) -> Dict:
        """
        执行一次日K检测（启动时调用）

        Returns:
            检测结果
        """
        logger.info("执行日K检测...")
        return self.scan_daily()