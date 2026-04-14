"""
股票扫描器模块
"""
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional

from src.data_source import DataSource
from src.indicators import calculate_indicators, detect_cross, get_current_values
from src.state_manager import StateManager
from src.notifier import create_notifier

import config

logger = logging.getLogger(__name__)


class Scanner:
    """股票扫描器"""

    def __init__(self):
        self.data_source = DataSource()
        self.state_manager = StateManager()
        self.notifier = create_notifier()

    def scan(self, reference_date: Optional[str] = None) -> List[Dict]:
        """
        扫描沪深300股票，检测金叉信号

        Args:
            reference_date: 参考日期，用于筛选截止该日期的K线数据
                           格式如 "2024-01-15"，None表示使用全部数据

        Returns:
            [{"code": "000001", "name": "平安银行", "ma_short": 10.5, "ma_long": 10.3,
              "close": 10.8, "klines": DataFrame, "ma_short_series": Series, "ma_long_series": Series}, ...]
        """
        logger.info(f"开始扫描沪深300股票... (参考日期: {reference_date or '全部数据'})")
        start_time = time.time()

        results = []

        # 获取沪深300股票列表
        stocks = self.data_source.get_hs300_stocks()
        total = len(stocks)

        # 发送扫描开始通知
        self.notifier.notify_scan_start(total)

        for i, stock in enumerate(stocks, 1):
            code = stock["code"]
            name = stock["name"]

            logger.debug(f"扫描 [{i}/{total}] {code}({name})")

            try:
                # 获取K线数据
                klines = self.data_source.get_stock_klines(code)
                if klines is None:
                    continue

                # 如果有参考日期，筛选截止该日期的数据
                if reference_date:
                    klines = klines[klines["time"].str[:10] <= reference_date]
                    if len(klines) < config.MA_LONG_KLINES:
                        logger.debug(f"{code} 参考日期 {reference_date} 数据不足，跳过")
                        continue

                # 计算均线
                indicators = calculate_indicators(klines)
                if indicators is None:
                    logger.debug(f"{code} K线数据不足，跳过")
                    continue

                ma_short, ma_long = indicators

                # 检测交叉
                golden_cross, death_cross = detect_cross(ma_short, ma_long)

                # 如果检测到金叉，检查是否需要通知
                if golden_cross:
                    should_notify = self.state_manager.check_and_update(
                        code, name, ma_short, ma_long
                    )

                    if should_notify:
                        curr_ma_short, curr_ma_long = get_current_values(ma_short, ma_long)
                        close_price = klines["close"].iloc[-1]

                        results.append({
                            "code": code,
                            "name": name,
                            "ma_short": curr_ma_short,
                            "ma_long": curr_ma_long,
                            "close": close_price,
                            "time": klines["time"].iloc[-1],
                            "klines": klines,
                            "ma_short_series": ma_short,
                            "ma_long_series": ma_long
                        })

                        # 标记已通知
                        self.state_manager.mark_notified(code, name, curr_ma_short, curr_ma_long)

                # 检测到死叉，更新状态（已在上面的check_and_update中处理）
                if death_cross:
                    logger.info(f"{code}({name}) 检测到死叉")

                # 避免请求过快
                time.sleep(0.1)

            except Exception as e:
                logger.warning(f"扫描 {code}({name}) 异常: {e}")
                continue

        elapsed = time.time() - start_time
        logger.info(f"扫描完成，耗时 {elapsed:.1f}秒，发现 {len(results)} 个金叉信号")

        return results

    def run_single_scan(self, force_backtrack: bool = False, reset_state: bool = False) -> List[Dict]:
        """
        执行单次扫描

        Args:
            force_backtrack: 是否强制回溯到最近交易日
                           True: 始终回溯（非交易日启动）
                           False: 自动判断（交易日用当天，非交易日回溯）
            reset_state: 是否重置状态（启动扫描时使用，允许重新通知）

        Returns:
            金叉信号列表
        """
        # 启动扫描时重置状态，允许重新通知
        if reset_state:
            logger.info("重置通知状态，允许重新通知")
            self.state_manager.clear_all()

        dt = datetime.now()

        # 判断是否需要回溯
        if force_backtrack:
            # 强制回溯模式
            latest_trade_date = self.data_source.get_latest_trade_date(dt)
            logger.info(f"强制回溯模式：使用最近交易日 {latest_trade_date} 的数据进行扫描")
            return self.scan(reference_date=latest_trade_date)
        else:
            # 自动判断模式
            if self.data_source.is_trade_day(dt):
                # 交易日，使用当天数据
                logger.info(f"交易日模式：使用当天数据进行扫描")
                return self.scan()
            else:
                # 非交易日，回溯到最近交易日
                latest_trade_date = self.data_source.get_latest_trade_date(dt)
                logger.info(f"非交易日模式：回溯到最近交易日 {latest_trade_date}")
                return self.scan(reference_date=latest_trade_date)