"""
股票数据获取模块 - 多数据源支持（TuShare主源 + BaoStock备用 + AkShare备用）
"""
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set

import pandas as pd

import config
from src.cache import KlineCache

logger = logging.getLogger(__name__)

# 数据源状态
# TuShare（主源）和BaoStock（备用）默认启用
# AkShare（备用）默认不启用，易触发风控，需手动开启
DATASOURCE_AVAILABLE = {"tushare": True, "baostock": True, "akshare": False}


class DataSource:
    """多数据源封装"""

    def __init__(self):
        self.kline_cache = KlineCache()
        self._trade_dates: Optional[Set[str]] = None
        self._bs_logged_in = False
        self._ts_pro = None  # TuShare pro接口

    def _get_bs_code(self, code: str) -> str:
        """转换为BaoStock代码格式（sh/sz前缀）"""
        if code.startswith("6"):
            return f"sh.{code}"
        else:
            return f"sz.{code}"

    def _get_ts_code(self, code: str) -> str:
        """转换为TuShare代码格式（SZ/SH后缀）"""
        if code.startswith("6"):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    def _init_tushare(self):
        """初始化TuShare pro接口"""
        if self._ts_pro is not None:
            return True

        if not config.TUSHARE_TOKEN:
            logger.warning("TuShare Token未配置")
            DATASOURCE_AVAILABLE["tushare"] = False
            return False

        try:
            import tushare as ts
            ts.set_token(config.TUSHARE_TOKEN)
            self._ts_pro = ts.pro_api()
            logger.info("TuShare初始化成功")
            return True
        except ImportError:
            logger.warning("TuShare未安装，请执行: pip install tushare")
            DATASOURCE_AVAILABLE["tushare"] = False
            return False
        except Exception as e:
            logger.warning(f"TuShare初始化失败: {e}")
            DATASOURCE_AVAILABLE["tushare"] = False
            return False

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

        # 尝试BaoStock（主源）
        if DATASOURCE_AVAILABLE["baostock"]:
            try:
                import baostock as bs
                logger.info("从BaoStock获取沪深300成分股...")

                # 登录BaoStock
                lg = bs.login()
                if lg.error_code == '0':
                    rs = bs.query_hs300_stocks()
                    stocks = []
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        # BaoStock返回格式: date, code, name (code带sh/sz前缀)
                        bs_code = str(row[1]).strip()
                        # 去掉sh/sz前缀
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
                DATASOURCE_AVAILABLE["baostock"] = False

        # 备用：尝试AkShare
        if DATASOURCE_AVAILABLE["akshare"]:
            try:
                import akshare as ak
                logger.info("从AkShare获取沪深300成分股...")
                df = ak.index_stock_cons_weight_csindex(symbol="000300")
                stocks = []
                for _, row in df.iterrows():
                    code = str(row["成分券代码"])
                    name = str(row["成分券名称"])
                    stocks.append({"code": code, "name": name})

                cache_data = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "stocks": stocks
                }
                cache_path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2))
                logger.info(f"AkShare获取沪深300成分股 {len(stocks)} 只")
                return stocks
            except Exception as e:
                logger.warning(f"AkShare获取沪深300失败: {e}")
                DATASOURCE_AVAILABLE["akshare"] = False

        # 备用：使用硬编码的沪深300列表（或从本地缓存读取）
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

        # 检查缓存有效性：年份匹配 + 缓存包含今天或更新的日期
        if cache_path.exists():
            cache_data = json.loads(cache_path.read_text())
            cache_year = cache_data.get("year", 0)
            current_year = datetime.now().year
            today_str = datetime.now().strftime("%Y-%m-%d")

            if cache_year == current_year:
                dates_list = cache_data.get("dates", [])
                if dates_list:
                    # 检查缓存是否包含今天
                    if today_str in dates_list:
                        logger.info(f"使用交易日历缓存（包含今日 {today_str}）")
                        return set(dates_list)
                    else:
                        # 缓存不包含今天，需要刷新获取最新交易日历
                        latest_date_str = max(dates_list)
                        logger.info(f"交易日历缓存缺少今日 {today_str}（最新: {latest_date_str}），需要刷新")
                else:
                    logger.warning("交易日历缓存数据为空")

        # 尝试BaoStock（主源）
        if DATASOURCE_AVAILABLE["baostock"]:
            try:
                import baostock as bs
                logger.info("从BaoStock获取交易日历...")
                lg = bs.login()
                if lg.error_code == '0':
                    rs = bs.query_trade_dates()
                    dates = []
                    while (rs.error_code == '0') & rs.next():
                        dates.append(rs.get_row_data()[0])

                    current_year_dates = [d for d in dates if d.startswith(str(datetime.now().year))]
                    cache_data = {"year": datetime.now().year, "dates": current_year_dates}
                    cache_path.write_text(json.dumps(cache_data, indent=2))
                    logger.info(f"BaoStock获取 {len(current_year_dates)} 个交易日")
                    return set(current_year_dates)
                else:
                    logger.warning(f"BaoStock登录失败: {lg.error_msg}")
            except Exception as e:
                logger.warning(f"BaoStock获取交易日历失败: {e}")
                DATASOURCE_AVAILABLE["baostock"] = False

        # 备用：尝试AkShare
        if DATASOURCE_AVAILABLE["akshare"]:
            try:
                import akshare as ak
                logger.info("从AkShare获取交易日历...")
                df = ak.tool_trade_date_hist_sina()
                dates = df["trade_date"].astype(str).tolist()
                current_year_dates = [d for d in dates if d.startswith(str(datetime.now().year))]

                cache_data = {"year": datetime.now().year, "dates": current_year_dates}
                cache_path.write_text(json.dumps(cache_data, indent=2))
                logger.info(f"AkShare获取 {len(current_year_dates)} 个交易日")
                return set(current_year_dates)
            except Exception as e:
                logger.warning(f"AkShare获取交易日历失败: {e}")
                DATASOURCE_AVAILABLE["akshare"] = False

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

    def get_stock_klines(self, code: str, days: int = None) -> Optional[pd.DataFrame]:
        """
        获取单只股票的15分钟K线数据（多数据源 + 增量更新）

        Args:
            code: 股票代码（如"000001"）
            days: 获取天数

        Returns:
            DataFrame with columns: time, open, close, high, low, volume
        """
        if days is None:
            days = config.KLINE_DAYS

        logger.debug(f"获取股票 {code} 15分钟K线...")

        # 检查缓存并判断是否需要更新
        cached = self.kline_cache.get_with_check(code)

        if cached["data"] is not None and not cached["needs_update"]:
            logger.debug(f"使用缓存K线数据 {code}，无需更新")
            return cached["data"]

        # 需要更新或无缓存
        if cached["data"] is not None:
            logger.debug(f"缓存 {code} 需要增量更新")
            # 计算增量查询的起始时间
            # 优先级：last_fetch_time > last_kline_time > 从数据提取
            last_time_str = cached.get("last_fetch_time") \
                            or cached.get("last_kline_time")

            if last_time_str:
                try:
                    # 解析时间并往前回溯30分钟
                    if len(last_time_str) >= 16:
                        last_time_str = last_time_str[:16]
                    last_dt = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")
                    start_dt = last_dt - timedelta(minutes=30)
                    logger.debug(f"增量查询起始时间: {start_dt.strftime('%Y-%m-%d %H:%M')}")
                except ValueError:
                    start_dt = None
            else:
                start_dt = None
        else:
            start_dt = None
            logger.debug(f"无缓存 {code}，全量查询")

        # 获取新数据
        new_df = None

        # 尝试TuShare（主源，官方API稳定）
        if DATASOURCE_AVAILABLE["tushare"]:
            new_df = self._get_klines_tushare(code, days)

        # 备用：使用BaoStock（TuShare失败时）
        if new_df is None and DATASOURCE_AVAILABLE["baostock"]:
            new_df = self._get_klines_baostock(code, days)

        # 备用：使用AkShare（最后备用，易风控）
        if new_df is None and DATASOURCE_AVAILABLE["akshare"]:
            new_df = self._get_klines_akshare(code, days)

        if new_df is None:
            # API获取失败，返回缓存数据（即使可能过期）
            if cached["data"] is not None:
                logger.warning(f"获取 {code} 新数据失败，使用缓存数据")
                return cached["data"]
            logger.error(f"获取 {code} K线失败，所有数据源不可用")
            return None

        # 合并数据（如果有缓存）
        if cached["data"] is not None:
            merged_df = self._merge_klines(cached["data"], new_df)
            self.kline_cache.set(code, merged_df, last_fetch_time=datetime.now())
            logger.debug(f"合并 {code} K线数据，共 {len(merged_df)} 条")
            return merged_df
        else:
            self.kline_cache.set(code, new_df, last_fetch_time=datetime.now())
            return new_df

    def _merge_klines(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        合并新旧K线数据，去重

        Args:
            old_df: 旧数据
            new_df: 新数据

        Returns:
            合合并后的DataFrame
        """
        if old_df is None or old_df.empty:
            return new_df
        if new_df is None or new_df.empty:
            return old_df

        # 合并并按时间去重（保留最新的）
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["time"], keep="last")
        combined = combined.sort_values("time").reset_index(drop=True)

        return combined

    def _get_klines_tushare(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """从TuShare获取K线"""
        # 初始化TuShare
        if not self._init_tushare():
            return None

        try:
            ts_code = self._get_ts_code(code)

            # 计算日期范围
            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            start_date = (datetime.now() - timedelta(days=days + 5)).strftime("%Y-%m-%d %H:%M:%S")

            for attempt in range(config.REQUEST_RETRY_TIMES):
                try:
                    # TuShare分钟K线接口
                    df = self._ts_pro.query(
                        'stk_mins',
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        freq='15min'
                    )

                    if df is None or df.empty:
                        logger.warning(f"TuShare: 股票 {code} K线数据为空")
                        return None

                    # TuShare返回字段: ts_code, trade_time, open, high, low, close, vol, amount
                    df = df.rename(columns={
                        "trade_time": "time",
                        "open": "open",
                        "close": "close",
                        "high": "high",
                        "low": "low",
                        "vol": "volume"
                    })

                    # 格式化时间: TuShare返回格式为 "2026-04-14 09:45:00"
                    df["time"] = df["time"].astype(str)

                    # 只保留需要的天数
                    df["date_only"] = df["time"].str[:10]
                    recent_dates = df["date_only"].unique()[-days:]
                    df = df[df["date_only"].isin(recent_dates)]
                    df = df.drop(columns=["date_only", "ts_code", "amount"], errors='ignore')

                    # 数值转换
                    for col in ["open", "close", "high", "low", "volume"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                    logger.debug(f"TuShare获取 {code} K线 {len(df)} 条")
                    return df

                except Exception as e:
                    logger.warning(f"TuShare获取 {code} 失败 (尝试 {attempt+1}): {e}")
                    if attempt < config.REQUEST_RETRY_TIMES - 1:
                        # 指数退避
                        wait_time = config.REQUEST_DELAY_ON_ERROR * (2 ** attempt)
                        logger.debug(f"等待 {wait_time}秒后重试")
                        time.sleep(wait_time)

            return None

        except Exception as e:
            logger.warning(f"TuShare数据源不可用: {e}")
            DATASOURCE_AVAILABLE["tushare"] = False
            return None

    def _get_klines_akshare(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """从AkShare获取K线"""
        try:
            import akshare as ak
            for attempt in range(config.REQUEST_RETRY_TIMES):
                try:
                    df = ak.stock_zh_a_hist_min_em(
                        symbol=code,
                        period=config.KLINE_PERIOD,
                        adjust="qfq"
                    )

                    if df.empty:
                        logger.warning(f"AkShare: 股票 {code} K线数据为空")
                        return None

                    df = df.rename(columns={
                        "时间": "time",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "volume"
                    })

                    df["date"] = df["time"].str[:10]
                    recent_dates = df["date"].unique()[-days:]
                    df = df[df["date"].isin(recent_dates)]
                    df = df.drop(columns=["date"])

                    self.kline_cache.set(code, df)
                    logger.debug(f"AkShare获取 {code} K线 {len(df)} 条")
                    return df

                except Exception as e:
                    logger.warning(f"AkShare获取 {code} 失败 (尝试 {attempt+1}): {e}")
                    if attempt < config.REQUEST_RETRY_TIMES - 1:
                        # 指数退避：1秒, 2秒, 4秒...
                        wait_time = config.REQUEST_DELAY_ON_ERROR * (2 ** attempt)
                        logger.debug(f"等待 {wait_time}秒后重试")
                        time.sleep(wait_time)

            return None

        except ImportError:
            logger.warning("AkShare未安装")
            DATASOURCE_AVAILABLE["akshare"] = False
            return None
        except Exception as e:
            logger.warning(f"AkShare数据源不可用: {e}")
            DATASOURCE_AVAILABLE["akshare"] = False
            return None

    def _get_klines_baostock(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """从BaoStock获取分钟K线"""
        try:
            import baostock as bs

            # 登录
            if not self._bs_logged_in:
                lg = bs.login()
                if lg.error_code != '0':
                    logger.warning(f"BaoStock登录失败: {lg.error_msg}")
                    DATASOURCE_AVAILABLE["baostock"] = False
                    return None
                self._bs_logged_in = True

            bs_code = self._get_bs_code(code)

            # 计算日期范围
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")

            for attempt in range(config.REQUEST_RETRY_TIMES):
                try:
                    # BaoStock分钟K线频率：5, 15, 30, 60
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "date,time,code,open,high,low,close,volume,amount,adjustflag",
                        start_date=start_date,
                        end_date=end_date,
                        frequency="15",
                        adjustflag="3"  # 前复权
                    )

                    if rs.error_code != '0':
                        logger.warning(f"BaoStock查询失败: {rs.error_msg}")
                        return None

                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())

                    if not data_list:
                        logger.warning(f"BaoStock: 股票 {code} K线数据为空")
                        return None

                    df = pd.DataFrame(data_list, columns=rs.fields)

                    # 标准化列名和格式
                    df = df.rename(columns={
                        "time": "time",
                        "open": "open",
                        "close": "close",
                        "high": "high",
                        "low": "low",
                        "volume": "volume"
                    })

                    # 时间格式：BaoStock返回的是 "20260302094500000"，需要解析
                    # 格式：日期(8位) + 时间(6位) + 毫秒(4位)
                    def parse_bs_time(time_str: str) -> str:
                        if len(time_str) >= 14:
                            date_part = time_str[:8]  # 20260302
                            time_part = time_str[8:14]  # 094500
                            return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}"
                        return time_str

                    df["time"] = df["time"].apply(parse_bs_time)

                    # 数值转换
                    for col in ["open", "close", "high", "low", "volume"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                    # 只保留需要的天数
                    df["date_only"] = df["time"].str[:10]
                    recent_dates = df["date_only"].unique()[-days:]
                    df = df[df["date_only"].isin(recent_dates)]
                    df = df.drop(columns=["date_only", "date", "code", "amount", "adjustflag"])

                    self.kline_cache.set(code, df)
                    logger.debug(f"BaoStock获取 {code} 分钟K线 {len(df)} 条")
                    return df

                except Exception as e:
                    logger.warning(f"BaoStock获取 {code} 失败 (尝试 {attempt+1}): {e}")
                    if attempt < config.REQUEST_RETRY_TIMES - 1:
                        time.sleep(1)

            return None

        except ImportError:
            logger.warning("BaoStock未安装")
            DATASOURCE_AVAILABLE["baostock"] = False
            return None
        except Exception as e:
            logger.warning(f"BaoStock数据源不可用: {e}")
            DATASOURCE_AVAILABLE["baostock"] = False
            return None

    def get_stock_daily_klines(self, code: str, days: int = None) -> Optional[pd.DataFrame]:
        """
        获取单只股票的日K线数据（仅BaoStock）

        Args:
            code: 股票代码（如"000001"）
            days: 获取天数

        Returns:
            DataFrame with columns: time, open, close, high, low, volume
        """
        if days is None:
            days = config.DAILY_KLINE_DAYS

        logger.debug(f"获取股票 {code} 日K线...")

        # 仅使用BaoStock（根据配置）
        if not config.DATASOURCE_AVAILABLE_DAILY.get("baostock", False):
            logger.warning("日K数据源BaoStock未启用")
            return None

        return self._get_daily_klines_baostock(code, days)

    def _get_daily_klines_baostock(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """从BaoStock获取日K线"""
        try:
            import baostock as bs

            # 登录
            if not self._bs_logged_in:
                lg = bs.login()
                if lg.error_code != '0':
                    logger.warning(f"BaoStock登录失败: {lg.error_msg}")
                    return None
                self._bs_logged_in = True

            bs_code = self._get_bs_code(code)

            # 计算日期范围（多获取几天确保数据充足）
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days + 15)).strftime("%Y-%m-%d")

            for attempt in range(config.REQUEST_RETRY_TIMES):
                try:
                    # BaoStock日K线：frequency="d"
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "date,code,open,high,low,close,volume,amount,adjustflag",
                        start_date=start_date,
                        end_date=end_date,
                        frequency="d",  # 日K
                        adjustflag="3"  # 前复权
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

                    # 标准化列名和格式
                    # BaoStock日K返回字段: date, code, open, high, low, close, volume, amount, adjustflag
                    df = df.rename(columns={
                        "date": "time"
                    })

                    # 数值转换
                    for col in ["open", "close", "high", "low", "volume"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                    # 只保留需要的天数（最近days条）
                    df = df.tail(days)

                    # 删除不需要的列
                    df = df.drop(columns=["code", "amount", "adjustflag"], errors='ignore')

                    # 确保时间格式为 "YYYY-MM-DD"
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
    # 沪深300部分主要股票
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