"""
每日检测状态管理模块
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import config

logger = logging.getLogger(__name__)


class DailyScanState:
    """每日检测状态管理"""

    def __init__(self):
        self.state_file = Path(config.DAILY_SCAN_STATE_FILE)
        self._state: Dict = {}
        self._load()

    def _load(self) -> None:
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                self._state = json.loads(self.state_file.read_text())
                logger.info(f"加载每日检测状态: {self._state.get('date', '未知')}")
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}")
                self._state = {}

    def _save(self) -> None:
        """保存状态到文件"""
        try:
            self.state_file.write_text(json.dumps(self._state, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    def get_date(self) -> str:
        """获取状态记录的日期"""
        return self._state.get("date", "")

    def is_completed(self, date: str) -> bool:
        """
        检查指定日期是否已完成检测

        Args:
            date: 目标日期字符串（必须是最新交易日）

        Returns:
            是否已完成
        """
        # 日期不匹配，未完成
        if self._state.get("date") != date:
            return False

        return self._state.get("completed", False)

    def mark_completed(self, date: str) -> None:
        """
        标记指定日期已完成检测

        Args:
            date: 目标日期字符串（必须是最新交易日）
        """
        self._state["date"] = date
        self._state["completed"] = True
        self._state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        logger.info(f"标记 {date} 检测完成")

    def reset_for_new_day(self, stocks: List[Dict], date: str) -> None:
        """
        新的一天重置状态

        Args:
            stocks: 沪深300股票列表 [{"code": "000001", "name": "平安银行"}, ...]
            date: 目标日期字符串（必须是最新交易日）
        """
        stock_codes = [s["code"] for s in stocks]

        self._state = {
            "date": date,
            "completed": False,
            "total_stocks": len(stocks),
            "fetched_count": 0,
            "detected_count": 0,
            "pending_stocks": stock_codes,  # 待检测股票代码列表
            "signals": [],
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save()
        logger.info(f"重置 {date} 检测状态，待检测 {len(stock_codes)} 只股票")

    def get_pending_stocks(self) -> List[str]:
        """
        获取待检测股票代码列表

        Returns:
            待检测股票代码列表
        """
        return self._state.get("pending_stocks", [])

    def update_progress(self, code: str, signal: Optional[Dict] = None) -> None:
        """
        更新检测进度

        Args:
            code: 股票代码
            signal: 金叉信号（如果有），包含 code, name, ma5, ma20, close
        """
        # 从待检测列表移除
        pending = self._state.get("pending_stocks", [])
        if code in pending:
            pending.remove(code)
            self._state["pending_stocks"] = pending

        # 更新计数
        self._state["fetched_count"] = self._state.get("fetched_count", 0) + 1
        self._state["detected_count"] = self._state.get("detected_count", 0) + 1

        # 如果有金叉信号，添加到信号列表
        if signal:
            signals = self._state.get("signals", [])
            signals.append(signal)
            self._state["signals"] = signals
            logger.info(f"发现金叉信号: {code} ({signal.get('name', '未知')})")

        # 更新时间
        self._state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()

    def get_result(self) -> Dict:
        """
        获取当前检测结果

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
                "pending_stocks": List[str]
            }
        """
        return {
            "date": self._state.get("date", ""),
            "completed": self._state.get("completed", False),
            "total": self._state.get("total_stocks", 0),
            "fetched_count": self._state.get("fetched_count", 0),
            "detected_count": self._state.get("detected_count", 0),
            "pending_count": len(self._state.get("pending_stocks", [])),
            "signals_count": len(self._state.get("signals", [])),
            "signals": self._state.get("signals", []),
            "pending_stocks": self._state.get("pending_stocks", [])
        }

    def clear_all(self) -> None:
        """清空所有状态"""
        self._state = {}
        self._save()
        logger.info("清空每日检测状态")