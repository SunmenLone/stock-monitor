"""
K线数据缓存模块
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

import config

logger = logging.getLogger(__name__)


class KlineCache:
    """K线数据本地缓存管理"""

    # 缓存更新阈值：最多容忍缺失1条15分钟K线（15分钟）
    UPDATE_THRESHOLD_MINUTES = 15

    def __init__(self):
        self.cache_dir = Path(config.KLINES_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, code: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{code}.json"

    def _is_expired(self, cache_date: str) -> bool:
        """检查缓存是否过期（隔日清空）- 每次检查都获取当前日期"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return cache_date != current_date

    def _get_current_date(self) -> str:
        """获取当前日期"""
        return datetime.now().strftime("%Y-%m-%d")

    def _extract_last_kline_time(self, df: pd.DataFrame) -> Optional[str]:
        """
        从K线数据提取最后一条K线时间

        Args:
            df: K线DataFrame

        Returns:
            最后K线时间字符串，如 "2026-04-14 14:45"，或 None
        """
        if df is None or df.empty or "time" not in df.columns:
            return None

        try:
            last_time = df["time"].max()
            # 确保格式为 "YYYY-MM-DD HH:MM"
            if len(str(last_time)) >= 16:
                return str(last_time)[:16]
            return str(last_time)
        except Exception:
            return None

    def _parse_time_to_datetime(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串为datetime

        Args:
            time_str: 时间字符串，如 "2026-04-14 14:45" 或 "2026-04-14 14:45:00"

        Returns:
            datetime 或 None
        """
        if not time_str:
            return None

        try:
            # 尝试多种格式
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(time_str[:len(fmt.replace('%', ''))], fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _needs_update(self, last_kline_time_str: str) -> bool:
        """
        判断缓存是否需要更新

        规则：缺失超过1条15分钟K线（差距 > 15分钟）则需要更新

        Args:
            last_kline_time_str: 最后K线时间字符串

        Returns:
            是否需要更新
        """
        if not last_kline_time_str:
            return True

        last_dt = self._parse_time_to_datetime(last_kline_time_str)
        if last_dt is None:
            return True

        now = datetime.now()
        diff_minutes = (now - last_dt).total_seconds() / 60

        # 缺失超过阈值分钟数则需要更新
        needs_update = diff_minutes > self.UPDATE_THRESHOLD_MINUTES

        if needs_update:
            logger.debug(f"缓存需要更新：最后K线时间 {last_kline_time_str}，距现在 {diff_minutes:.1f} 分钟")

        return needs_update

    def get(self, code: str) -> Optional[pd.DataFrame]:
        """
        获取缓存的K线数据（简化版本，保持兼容）

        Args:
            code: 股票代码

        Returns:
            DataFrame 或 None（无缓存或已过期）
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
                "last_fetch_time": str 或 None,  # 上次API请求时间
                "last_kline_time": str 或 None,  # 最后K线时间
                "needs_update": bool  # 是否需要更新
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
            cache_date = raw_data.get("date", "")

            if self._is_expired(cache_date):
                logger.debug(f"缓存 {code} 已过期（隔日），删除")
                cache_path.unlink()
                return result

            df = pd.DataFrame(raw_data.get("klines", []))
            if df.empty:
                return result

            result["data"] = df
            result["last_fetch_time"] = raw_data.get("last_fetch_time")
            result["last_kline_time"] = raw_data.get("last_kline_time")

            # 如果缓存中没有记录时间，从数据中提取
            if not result["last_kline_time"]:
                result["last_kline_time"] = self._extract_last_kline_time(df)

            # 判断是否需要更新
            result["needs_update"] = self._needs_update(result["last_kline_time"])

            return result

        except Exception as e:
            logger.warning(f"读取缓存 {code} 失败: {e}")
            return result

    def set(self, code: str, df: pd.DataFrame, last_fetch_time: datetime = None) -> None:
        """
        设置K线缓存

        Args:
            code: 股票代码
            df: K线DataFrame
            last_fetch_time: 上次API请求时间，默认为当前时间
        """
        cache_path = self._get_cache_path(code)

        if last_fetch_time is None:
            last_fetch_time = datetime.now()

        try:
            last_kline_time = self._extract_last_kline_time(df)
            last_fetch_time_str = last_fetch_time.strftime("%Y-%m-%d %H:%M:%S")

            data = {
                "date": self._get_current_date(),
                "last_fetch_time": last_fetch_time_str,
                "last_kline_time": last_kline_time,
                "klines": df.to_dict(orient="records")
            }
            cache_path.write_text(json.dumps(data, ensure_ascii=False))
            logger.debug(f"缓存 {code} K线 {len(df)} 条，最后时间 {last_kline_time}")

        except Exception as e:
            logger.warning(f"写入缓存 {code} 失败: {e}")

    def clear_all(self) -> None:
        """清空所有缓存"""
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
        logger.info("清空所有K线缓存")

    def clear_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        for file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                if self._is_expired(data.get("date", "")):
                    file.unlink()
                    count += 1
            except Exception:
                file.unlink()
                count += 1

        if count > 0:
            logger.info(f"清理 {count} 个过期缓存")
        return count