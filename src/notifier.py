"""
钉钉通知模块
"""
import hashlib
import hmac
import base64
import logging
import time
import urllib.parse
import requests
from datetime import datetime
from typing import List, Dict

import config

logger = logging.getLogger(__name__)


class DingDingNotifier:
    """钉钉群机器人通知"""

    def __init__(self):
        self.webhook = config.DINGDING_WEBHOOK
        self.secret = config.DINGDING_SECRET

    def _get_sign(self) -> tuple:
        """
        计算签名（如果配置了密钥）

        Returns:
            (timestamp, sign) 或 (None, None)
        """
        if not self.secret:
            return None, None

        timestamp = str(int(time.time() * 1000))
        string_to_sign = timestamp + "\n" + self.secret

        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def _build_url(self) -> str:
        """构建带签名的Webhook URL"""
        if not self.webhook:
            logger.error("未配置钉钉Webhook URL")
            return ""

        url = self.webhook

        if self.secret:
            timestamp, sign = self._get_sign()
            if timestamp and sign:
                url = f"{url}&timestamp={timestamp}&sign={sign}"

        return url

    def send_text(self, content: str) -> bool:
        """发送文本消息"""
        url = self._build_url()
        if not url:
            return False

        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }

        try:
            resp = requests.post(url, json=data, timeout=config.REQUEST_TIMEOUT)
            result = resp.json()

            if result.get("errcode") == 0:
                logger.info("钉钉文本消息发送成功")
                return True
            else:
                logger.error(f"钉钉消息发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"发送钉钉消息异常: {e}")
            return False

    def send_markdown(self, title: str, content: str) -> bool:
        """发送Markdown消息"""
        url = self._build_url()
        if not url:
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }

        try:
            resp = requests.post(url, json=data, timeout=config.REQUEST_TIMEOUT)
            result = resp.json()

            if result.get("errcode") == 0:
                logger.info("钉钉Markdown消息发送成功")
                return True
            else:
                logger.error(f"钉钉消息发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"发送钉钉消息异常: {e}")
            return False

    def notify_daily_scan_start(self, total: int, pending: int, fetched: int) -> bool:
        """发送日K检测开始通知"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        title = "🔍 日K金叉检测启动"

        content = f"""## 🔍 日K金叉检测启动

**时间**: {now}

**总股票**: {total}只

**已拉取**: {fetched}只

**待检测**: {pending}只

---

系统正在检测沪深300日K金叉信号，请稍候..."""

        return self.send_markdown(title, content)

    def notify_daily_scan_complete(self, result: Dict) -> bool:
        """发送日K检测完成通知"""
        url = self._build_url()
        if not url:
            logger.error("未配置钉钉Webhook URL")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        completed = result.get("completed", False)
        status_text = "已完成（当天不再检测）" if completed else "未完成（下次继续）"

        signals_count = result.get("signals_count", 0)
        if signals_count > 0:
            title = f"✅ 日K金叉检测完成 ({signals_count}只金叉)"
            status_line = f"**金叉信号**: 📊 {signals_count} 只"
        else:
            title = "✅ 日K金叉检测完成"
            status_line = "**金叉信号**: 未发现符合条件的股票"

        content = f"""## {title}

**完成时间**: {now}

**总股票**: {result.get('total', 0)}只

**完成检测**: {result.get('detected_count', 0)}只

**待检测**: {result.get('pending_count', 0)}只

**耗时**: {result.get('elapsed', 0):.1f}秒

---

**当日状态**: {status_text}

{status_line}"""

        return self.send_markdown(title, content)

    def notify_golden_cross_daily(self, signals: List[Dict]) -> bool:
        """发送日K金叉信号通知"""
        if not signals:
            logger.info("无日K金叉信号，不发送通知")
            return True

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        title = f"📊 日K金叉信号 ({len(signals)}只)"

        lines = [
            f"## 📊 日K金叉信号检测",
            f"",
            f"**检测时间**: {now}",
            f"**信号数量**: {len(signals)}只",
            f"",
            "---",
            f""
        ]

        for sig in signals:
            code = sig.get("code", "")
            name = sig.get("name", "")
            close = sig.get("close", 0)
            ma5 = sig.get("ma5", 0)
            ma20 = sig.get("ma20", 0)
            sig_date = sig.get("date", "")

            diff_pct = ((ma5 - ma20) / ma20) * 100 if ma20 > 0 else 0

            lines.append(f"### {name} ({code})")
            lines.append(f"- 当前价: **{close:.2f}**")
            lines.append(f"- MA5: {ma5:.2f}")
            lines.append(f"- MA20: {ma20:.2f}")
            lines.append(f"- 均线差: +{diff_pct:.2f}%")
            lines.append(f"- K线日期: {sig_date}")
            lines.append(f"")

        content = "\n".join(lines)

        return self.send_markdown(title, content)


def create_notifier() -> DingDingNotifier:
    """创建通知器实例"""
    return DingDingNotifier()