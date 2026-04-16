"""
股票数据获取模块 - BaoStock数据源（日K线）
"""
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set

import pandas as pd

import config

logger = logging.getLogger(__name__)

# 日K检测数据源状态
DATASOURCE_AVAILABLE_DAILY = {"tushare": False, "baostock": True, "akshare": False}


class DataSource:
    """BaoStock数据源封装（日K线）"""

    def __init__(self):
        self._trade_dates: Optional[Set[str]] = None
        self._bs_logged_in = False

    def _get_bs_code(self, code: str) -> str:
        """转换为BaoStock代码格式（sh/sz前缀）"""
        if code.startswith("6"):
            return f"sh.{code}"
        else:
            return f"sz.{code}"

    def get_hs300_stocks(self) -> List[Dict[str, str]]:
        """
        获取沪深300成分股列表

        Returns:
            [{"code": "000001", "name": "平安银行"}, ...]
        """
        cache_path = Path(config.HS300_CACHE_FILE)

        # 检查缓存是否今日有效
        if cache_path.exists():
            cache_data = json.loads(cache_path.read_text())
            cache_date = cache_data.get("date", "")
            if cache_date == datetime.now().strftime("%Y-%m-%d"):
                logger.info("使用沪深300缓存数据")
                return cache_data.get("stocks", [])

        # 尝试BaoStock
        if DATASOURCE_AVAILABLE_DAILY.get("baostock", False):
            try:
                import baostock as bs
                logger.info("从BaoStock获取沪深300成分股...")

                lg = bs.login()
                if lg.error_code == '0':
                    rs = bs.query_hs300_stocks()
                    stocks = []
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        bs_code = str(row[1]).strip()
                        code = bs_code.split('.')[-1] if '.' in bs_code else bs_code
                        name = str(row[2]).strip()
                        stocks.append({"code": code, "name": name})

                    cache_data = {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "stocks": stocks
                    }
                    cache_path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2))
                    logger.info(f"BaoStock获取沪深300成分股 {len(stocks)} 只")
                    return stocks
                else:
                    logger.warning(f"BaoStock登录失败: {lg.error_msg}")
            except Exception as e:
                logger.warning(f"BaoStock获取沪深300失败: {e}")

        # 备用：使用过期缓存
        if cache_path.exists():
            logger.warning("使用过期缓存数据")
            cache_data = json.loads(cache_path.read_text())
            return cache_data.get("stocks", [])

        # 最后备用：内置沪深300主要股票列表
        logger.warning("使用内置沪深300股票列表")
        return _get_builtin_hs300()

    def get_trade_dates(self) -> Set[str]:
        """
        获取交易日历

        Returns:
            {"2024-01-02", "2024-01-03", ...}
        """
        cache_path = Path(config.TRADE_DATE_CACHE_FILE)
        today_str = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year

        # 检查缓存有效性
        if cache_path.exists():
            cache_data = json.loads(cache_path.read_text())
            cache_year = cache_data.get("year", 0)
            dates_list = cache_data.get("dates", [])

            if cache_year == current_year and dates_list:
                # 今日在交易日列表中
                if today_str in dates_list:
                    logger.info(f"使用交易日历缓存（包含今日 {today_str}）")
                    return set(dates_list)

                # 今日不在列表中，检查是否今天已同步过
                last_sync_date = cache_data.get("last_sync_date")

                # 兼容旧格式：如果没有last_sync_date但有initialized，视为已同步
                if last_sync_date is None and cache_data.get("initialized"):
                    last_sync_date = today_str  # 旧格式迁移，首次读取时设为今天

                if last_sync_date == today_str:
                    # 今天已同步过，今日确实非交易日
                    logger.info(f"今日 {today_str} 非交易日（交易日历今日已同步）")
                    return set(dates_list)
                else:
                    # 上次同步不是今天，可能有新交易日需要刷新
                    latest_date_str = max(dates_list)
                    logger.info(
                        f"交易日历上次同步: {last_sync_date or '未知'}, "
                        f"最新交易日: {latest_date_str}，需要刷新"
                    )

        # 尝试BaoStock
        if DATASOURCE_AVAILABLE_DAILY.get("baostock", False):
            try:
                import baostock as bs
                logger.info("从BaoStock获取交易日历...")
                lg = bs.login()
                if lg.error_code == '0':
                    rs = bs.query_trade_dates()
                    dates = []
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        date = row[0]  # calendar_date
                        is_trading = row[1]  # is_trading_day ("1"=交易日, "0"=非交易日)
                        if is_trading == '1':  # 只保留交易日
                            dates.append(date)

                    current_year_dates = [d for d in dates if d.startswith(str(current_year))]
                    cache_data = {
                        "year": current_year,
                        "dates": current_year_dates,
                        "last_sync_date": today_str  # 记录同步时间，替代initialized
                    }
                    cache_path.write_text(json.dumps(cache_data, indent=2))
                    logger.info(f"BaoStock获取 {len(current_year_dates)} 个交易日，同步时间: {today_str}")
                    return set(current_year_dates)
                else:
                    logger.warning(f"BaoStock登录失败: {lg.error_msg}")
            except Exception as e:
                logger.warning(f"BaoStock获取交易日历失败: {e}")

        raise RuntimeError("无法获取交易日历，请检查网络连接")

    def is_trade_day(self, date: Optional[datetime] = None) -> bool:
        """检查是否为交易日"""
        if date is None:
            date = datetime.now()

        if self._trade_dates is None:
            self._trade_dates = self.get_trade_dates()

        date_str = date.strftime("%Y-%m-%d")
        return date_str in self._trade_dates

    def get_latest_trade_date(self, date: Optional[datetime] = None) -> str:
        """获取最近的交易日"""
        if date is None:
            date = datetime.now()

        if self._trade_dates is None:
            self._trade_dates = self.get_trade_dates()

        date_str = date.strftime("%Y-%m-%d")

        if date_str in self._trade_dates:
            return date_str

        sorted_dates = sorted(self._trade_dates, reverse=True)
        for d in sorted_dates:
            if d <= date_str:
                logger.info(f"非交易日 {date_str}，回溯到最近交易日 {d}")
                return d

        if sorted_dates:
            return sorted_dates[0]

        raise ValueError("无法获取交易日历数据")

    def is_trade_time(self, dt: Optional[datetime] = None) -> bool:
        """检查是否在交易时间段内"""
        if dt is None:
            dt = datetime.now()

        if not self.is_trade_day(dt):
            return False

        time_str = dt.strftime("%H:%M")

        if TRADING_MORNING_START <= time_str <= TRADING_MORNING_END:
            return True
        if TRADING_AFTERNOON_START <= time_str <= TRADING_AFTERNOON_END:
            return True

        return False

    def get_stock_daily_klines(self, code: str, days: int = None, start_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取单只股票的日K线数据（仅BaoStock）

        Args:
            code: 股票代码（如"000001"）
            days: 获取天数（最大）
            start_date: 增量拉取起始日期（可选，如"2026-04-10"）

        Returns:
            DataFrame with columns: time, open, close, high, low, volume
        """
        if days is None:
            days = config.DAILY_KLINE_DAYS

        logger.debug(f"获取股票 {code} 日K线..." + (f" 从{start_date}" if start_date else ""))

        if not DATASOURCE_AVAILABLE_DAILY.get("baostock", False):
            logger.warning("日K数据源BaoStock未启用")
            return None

        return self._get_daily_klines_baostock(code, days, start_date)

    def _get_daily_klines_baostock(self, code: str, days: int, start_date: str = None) -> Optional[pd.DataFrame]:
        """从BaoStock获取日K线"""
        try:
            import baostock as bs

            if not self._bs_logged_in:
                lg = bs.login()
                if lg.error_code != '0':
                    logger.warning(f"BaoStock登录失败: {lg.error_msg}")
                    return None
                self._bs_logged_in = True

            bs_code = self._get_bs_code(code)
            end_date = datetime.now().strftime("%Y-%m-%d")

            if start_date:
                actual_start = start_date
            else:
                actual_start = (datetime.now() - timedelta(days=days + 15)).strftime("%Y-%m-%d")

            for attempt in range(config.REQUEST_RETRY_TIMES):
                try:
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "date,code,open,high,low,close,volume,amount,adjustflag",
                        start_date=actual_start,
                        end_date=end_date,
                        frequency="d",
                        adjustflag="3"
                    )

                    if rs.error_code != '0':
                        logger.warning(f"BaoStock查询日K失败: {rs.error_msg}")
                        return None

                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())

                    if not data_list:
                        logger.warning(f"BaoStock: 股票 {code} 日K数据为空")
                        return None

                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df = df.rename(columns={"date": "time"})

                    for col in ["open", "close", "high", "low", "volume"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                    df = df.tail(days)
                    df = df.drop(columns=["code", "amount", "adjustflag"], errors='ignore')
                    df["time"] = df["time"].astype(str)

                    logger.debug(f"BaoStock获取 {code} 日K线 {len(df)} 条")
                    return df

                except Exception as e:
                    logger.warning(f"BaoStock获取 {code} 日K失败 (尝试 {attempt+1}): {e}")
                    if attempt < config.REQUEST_RETRY_TIMES - 1:
                        time.sleep(1)

            return None

        except ImportError:
            logger.warning("BaoStock未安装")
            return None
        except Exception as e:
            logger.warning(f"BaoStock日K数据源不可用: {e}")
            return None


def _get_builtin_hs300() -> List[Dict[str, str]]:
    """内置沪深300主要股票列表（备用）"""
    major_stocks = [
        {"code": "600519", "name": "贵州茅台"},
        {"code": "601318", "name": "中国平安"},
        {"code": "600036", "name": "招商银行"},
        {"code": "000001", "name": "平安银行"},
        {"code": "000858", "name": "五粮液"},
        {"code": "601166", "name": "兴业银行"},
        {"code": "600000", "name": "浦发银行"},
        {"code": "601398", "name": "工商银行"},
        {"code": "601288", "name": "农业银行"},
        {"code": "601939", "name": "建设银行"},
        {"code": "601988", "name": "中国银行"},
        {"code": "600276", "name": "恒瑞医药"},
        {"code": "000333", "name": "美的集团"},
        {"code": "002415", "name": "海康威视"},
        {"code": "600887", "name": "伊利股份"},
        {"code": "601012", "name": "隆基绿能"},
        {"code": "600309", "name": "万华化学"},
        {"code": "002352", "name": "顺丰控股"},
        {"code": "600900", "name": "长江电力"},
        {"code": "601888", "name": "中国中免"},
    ]
    logger.warning(f"使用内置 {len(major_stocks)} 只主要股票作为备用")
    return major_stocks


# 从config导入交易时间常量
TRADING_MORNING_START = config.TRADING_MORNING_START
TRADING_MORNING_END = config.TRADING_MORNING_END
TRADING_AFTERNOON_START = config.TRADING_AFTERNOON_START
TRADING_AFTERNOON_END = config.TRADING_AFTERNOON_END