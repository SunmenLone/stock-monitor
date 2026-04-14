"""
日K线数据缓存模块
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

import config

logger = logging.getLogger(__name__)


class DailyKlineCache:
    """日K线数据本地缓存管理"""

    def __init__(self):
        self.cache_dir = Path(config.DAILY_KLINES_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, code: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{code}.json"

    def _get_current_date(self) -> str:
        """获取当前日期"""
        return datetime.now().strftime("%Y-%m-%d")

    def _extract_last_kline_time(self, df: pd.DataFrame) -> Optional[str]:
        """
        从K线数据提取最后一条K线时间（日期）

        Args:
            df: K线DataFrame

        Returns:
            最后K线日期字符串，如 "2026-04-14"，或 None
        """
        if df is None or df.empty or "time" not in df.columns:
            return None

        try:
            last_time = df["time"].max()
            # 日K时间格式为日期 "YYYY-MM-DD"
            time_str = str(last_time)
            if len(time_str) >= 10:
                return time_str[:10]
            return time_str
        except Exception:
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        解析日期字符串为datetime

        Args:
            date_str: 日期字符串，如 "2026-04-14"

        Returns:
            datetime 或 None
        """
        if not date_str:
            return None

        try:
            # 截取日期部分
            date_part = date_str[:10] if len(date_str) >= 10 else date_str
            return datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            return None

    def _needs_update(self, last_kline_time_str: str) -> bool:
        """
        判断缓存是否需要更新

        规则：最后K线日期距今天 >= 1天，则需要更新

        Args:
            last_kline_time_str: 最后K线日期字符串

        Returns:
            是否需要更新
        """
        if not last_kline_time_str:
            return True

        last_dt = self._parse_date(last_kline_time_str)
        if last_dt is None:
            return True

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")

        diff_days = (today_dt - last_dt).days

        # 最后K线日期距今天 >= 1天，需要更新
        needs_update = diff_days >= 1

        if needs_update:
            logger.debug(f"缓存需要更新：最后K线日期 {last_kline_time_str}，距今天 {diff_days} 天")

        return needs_update

    def get(self, code: str) -> Optional[pd.DataFrame]:
        """
        获取缓存的日K线数据（简化版本，保持兼容）

        Args:
            code: 股票代码

        Returns:
            DataFrame 或 None（无缓存）
        """
        result = self.get_with_check(code)
        return result.get("data")

    def get_with_check(self, code: str) -> Dict[str, Any]:
        """
        获取缓存并检查是否需要更新

        Args:
            code: 股票代码

        Returns:
            {
                "data": DataFrame 或 None,
                "last_fetch_time": str 或 None,
                "last_kline_time": str 或 None,
                "needs_update": bool
            }
        """
        cache_path = self._get_cache_path(code)
        result = {
            "data": None,
            "last_fetch_time": None,
            "last_kline_time": None,
            "needs_update": True
        }

        if not cache_path.exists():
            return result

        try:
            raw_data = json.loads(cache_path.read_text())

            df = pd.DataFrame(raw_data.get("klines", []))
            if df.empty:
                return result

            result["data"] = df
            result["last_fetch_time"] = raw_data.get("last_fetch_time")
            result["last_kline_time"] = raw_data.get("last_kline_time")

            # 如果缓存中没有记录时间，从数据中提取
            if not result["last_kline_time"]:
                result["last_kline_time"] = self._extract_last_kline_time(df)

            # 判断是否需要更新（基于最后K线日期差）
            result["needs_update"] = self._needs_update(result["last_kline_time"])

            return result

        except Exception as e:
            logger.warning(f"读取日K缓存 {code} 失败: {e}")
            return result

    def set(self, code: str, df: pd.DataFrame, last_fetch_time: datetime = None) -> None:
        """
        设置日K线缓存，保留最近DAILY_KLINE_DAYS条数据

        Args:
            code: 股票代码
            df: K线DataFrame
            last_fetch_time: 上次API请求时间，默认为当前时间
        """
        cache_path = self._get_cache_path(code)

        if last_fetch_time is None:
            last_fetch_time = datetime.now()

        try:
            # 截取最近DAILY_KLINE_DAYS条数据
            df = df.tail(config.DAILY_KLINE_DAYS)

            last_kline_time = self._extract_last_kline_time(df)
            last_fetch_time_str = last_fetch_time.strftime("%Y-%m-%d %H:%M:%S")

            data = {
                "date": self._get_current_date(),
                "last_fetch_time": last_fetch_time_str,
                "last_kline_time": last_kline_time,
                "klines": df.to_dict(orient="records")
            }
            cache_path.write_text(json.dumps(data, ensure_ascii=False))
            logger.debug(f"缓存 {code} 日K线 {len(df)} 条，最后日期 {last_kline_time}")

        except Exception as e:
            logger.warning(f"写入日K缓存 {code} 失败: {e}")

    def merge_and_set(self, code: str, old_df: pd.DataFrame, new_df: pd.DataFrame, last_fetch_time: datetime = None) -> pd.DataFrame:
        """
        合并新旧日K数据并缓存

        Args:
            code: 股票代码
            old_df: 旧K线DataFrame（缓存数据）
            new_df: 新K线DataFrame（增量数据）
            last_fetch_time: 上次API请求时间，默认为当前时间

        Returns:
            合并后的DataFrame
        """
        if last_fetch_time is None:
            last_fetch_time = datetime.now()

        try:
            # 合并数据
            if old_df is None or old_df.empty:
                merged_df = new_df
            elif new_df is None or new_df.empty:
                merged_df = old_df
            else:
                merged_df = pd.concat([old_df, new_df], ignore_index=True)

            # 按时间排序，去重（保留最新的）
            merged_df = merged_df.drop_duplicates(subset=["time"], keep="last")
            merged_df = merged_df.sort_values("time").reset_index(drop=True)

            # 截取最近DAILY_KLINE_DAYS条
            merged_df = merged_df.tail(config.DAILY_KLINE_DAYS)

            # 写入缓存
            self.set(code, merged_df, last_fetch_time)

            logger.debug(f"合并 {code} 日K数据：旧{len(old_df) if old_df else 0}条 + 新{len(new_df) if new_df else 0}条 = {len(merged_df)}条")

            return merged_df

        except Exception as e:
            logger.warning(f"合并日K缓存 {code} 失败: {e}")
            # 失败时返回新数据
            return new_df

    def clear_all(self) -> None:
        """清空所有缓存"""
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
        logger.info("清空所有日K线缓存")

    def clear_expired(self) -> int:
        """
        处理过期缓存（日期变更后保留数据，仅更新日期字段）

        不删除缓存文件，保留最近DAILY_KLINE_DAYS条数据
        """
        count = 0
        current_date = self._get_current_date()

        for file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                cache_date = data.get("date", "")

                # 日期变更，保留数据但更新日期字段
                if cache_date != current_date:
                    # 截取最近DAILY_KLINE_DAYS条数据
                    klines = data.get("klines", [])
                    if klines:
                        klines = klines[-config.DAILY_KLINE_DAYS:]
                        data["klines"] = klines
                        data["date"] = current_date
                        file.write_text(json.dumps(data, ensure_ascii=False))
                        count += 1
                        logger.debug(f"更新缓存 {file.stem} 日期为 {current_date}，保留 {len(klines)} 条")

            except Exception as e:
                logger.warning(f"处理缓存 {file.stem} 异常: {e}")
                # 异常文件保留，不删除
                continue

        if count > 0:
            logger.info(f"更新 {count} 个缓存日期字段，保留历史数据")
        return count