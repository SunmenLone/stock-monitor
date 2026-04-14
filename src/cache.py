"""
K线数据缓存模块
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

import config

logger = logging.getLogger(__name__)


class KlineCache:
    """K线数据本地缓存管理"""

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

    def get(self, code: str) -> Optional[pd.DataFrame]:
        """
        获取缓存的K线数据

        Args:
            code: 股票代码

        Returns:
            DataFrame 或 None（无缓存或已过期）
        """
        cache_path = self._get_cache_path(code)

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text())
            cache_date = data.get("date", "")

            if self._is_expired(cache_date):
                logger.debug(f"缓存 {code} 已过期，删除")
                cache_path.unlink()
                return None

            df = pd.DataFrame(data["klines"])
            return df

        except Exception as e:
            logger.warning(f"读取缓存 {code} 失败: {e}")
            return None

    def set(self, code: str, df: pd.DataFrame) -> None:
        """
        设置K线缓存

        Args:
            code: 股票代码
            df: K线DataFrame
        """
        cache_path = self._get_cache_path(code)

        try:
            data = {
                "date": self._get_current_date(),
                "klines": df.to_dict(orient="records")
            }
            cache_path.write_text(json.dumps(data, ensure_ascii=False))
            logger.debug(f"缓存 {code} K线 {len(df)} 条")

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