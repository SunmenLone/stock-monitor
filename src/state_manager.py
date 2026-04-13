"""
信号状态管理模块 - 用于去重
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import config
from src.indicators import get_cross_status

logger = logging.getLogger(__name__)


class StateManager:
    """信号状态管理（去重）"""

    def __init__(self):
        self.state_file = Path(config.NOTIFIED_STATE_FILE)
        self._states: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                self._states = json.loads(self.state_file.read_text())
                logger.info(f"加载 {len(self._states)} 条状态记录")
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}")
                self._states = {}

    def _save(self) -> None:
        """保存状态到文件"""
        try:
            self.state_file.write_text(json.dumps(self._states, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    def has_notified(self, code: str) -> bool:
        """
        检查股票是否已通知金叉

        Args:
            code: 肧票代码

        Returns:
            是否已通知
        """
        return code in self._states and self._states[code].get("status") == "golden_cross"

    def mark_notified(self, code: str, name: str, ma_short: float, ma_long: float) -> None:
        """
        标记股票已通知金叉

        Args:
            code: 肧票代码
            name: 肧票名称
            ma_short: 短期均线值
            ma_long: 长期均线值
        """
        self._states[code] = {
            "name": name,
            "notified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ma_short": round(ma_short, 2),
            "ma_long": round(ma_long, 2),
            "status": "golden_cross"
        }
        self._save()
        logger.info(f"标记 {code}({name}) 金叉已通知")

    def check_and_update(self, code: str, name: str, ma_short: pd.Series, ma_long: pd.Series) -> bool:
        """
        检查状态并更新

        Args:
            code: 肧票代码
            name: 肧票名称
            ma_short: 短期均线序列
            ma_long: 长期均线序列

        Returns:
            是否应该通知（金叉且未已通知）
        """
        # 获取当前均线状态
        current_status = get_cross_status(ma_short, ma_long)

        # 如果当前是死叉或中性，清除该股票的通知状态
        if current_status in ("death_cross", "neutral"):
            if code in self._states:
                logger.info(f"{code}({name}) 已离开金叉区域，清除状态")
                del self._states[code]
                self._save()
            return False

        # 如果当前是金叉状态
        if current_status == "golden_cross":
            # 检查是否已通知
            if self.has_notified(code):
                logger.debug(f"{code}({name}) 已在金叉区域且已通知，跳过")
                return False

            # 未通知，应该通知
            return True

        return False

    def get_state(self, code: str) -> Optional[dict]:
        """获取股票状态"""
        return self._states.get(code)

    def clear_all(self) -> None:
        """清空所有状态"""
        self._states = {}
        self._save()
        logger.info("清空所有状态记录")


# 需要导入pandas
import pandas as pd