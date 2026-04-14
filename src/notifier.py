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
from pathlib import Path
from typing import List, Dict, Optional

import config
from src.chart_generator import generate_ma_chart
from src.oss_uploader import create_uploader

logger = logging.getLogger(__name__)


class DingDingNotifier:
    """钉钉群机器人通知"""

    def __init__(self):
        self.webhook = config.DINGDING_WEBHOOK
        self.secret = config.DINGDING_SECRET
        self.oss_uploader = create_uploader()

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
        """
        发送文本消息

        Args:
            content: 文本内容

        Returns:
            是否成功
        """
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
        """
        发送Markdown消息

        Args:
            title: 消息标题
            content: Markdown内容

        Returns:
            是否成功
        """
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

    def notify_scan_start(self, stock_count: int = 300) -> bool:
        """
        发送扫描开始通知

        Args:
            stock_count: 待扫描股票数量

        Returns:
            是否成功
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        title = "🔍 沪深300扫描启动"

        content = f"""## 🔍 沪深300均线交叉检测

**启动时间**: {now}

**扫描范围**: 沪深300 ({stock_count}只股票)

---

系统正在扫描检测金叉信号，请稍候..."""

        return self.send_markdown(title, content)

    def notify_golden_cross(self, signals: List[Dict]) -> bool:
        """
        发送金叉信号通知（含均线图表）

        Args:
            signals: 金叉信号列表，需包含 klines, ma_short_series, ma_long_series

        Returns:
            是否成功
        """
        if not signals:
            logger.info("无金叉信号，不发送通知")
            return True

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 构建Markdown内容
        title = f"📊 沪深300金叉信号 ({len(signals)}只)"

        lines = [
            f"## 📊 沪深300金叉信号检测",
            f"",
            f"**检测时间**: {now}",
            f"**信号数量**: {len(signals)}只",
            f"",
            "---",
            f""
        ]

        for sig in signals:
            code = sig["code"]
            name = sig["name"]
            close = sig["close"]
            ma_short = sig["ma_short"]
            ma_long = sig["ma_long"]

            diff_pct = ((ma_short - ma_long) / ma_long) * 100

            lines.append(f"### {name} ({code})")
            lines.append(f"- 当前价: **{close:.2f}**")
            lines.append(f"- MA5: {ma_short:.2f}")
            lines.append(f"- MA20: {ma_long:.2f}")
            lines.append(f"- 均线差: +{diff_pct:.2f}%")

            # 生成并嵌入图表
            if "klines" in sig and "ma_short_series" in sig:
                try:
                    chart_data = generate_ma_chart(
                        code, name,
                        sig["klines"],
                        sig["ma_short_series"],
                        sig["ma_long_series"]
                    )
                    # 上传PNG到OSS
                    oss_url = None
                    if self.oss_uploader.is_available():
                        png_path = chart_data["png_path"]
                        # 使用股票代码+时间戳作为文件名
                        oss_filename = f"{code}_{int(time.time())}.png"
                        oss_url = self.oss_uploader.upload_chart(png_path, oss_filename)

                    # 使用OSS链接或本地路径
                    lines.append(f"")
                    if oss_url:
                        lines.append(f"📈 [查看均线图表]({oss_url})")
                    else:
                        lines.append(f"本地图表: {chart_data['png_path']}")

                except Exception as e:
                    logger.warning(f"生成 {code} 图表失败: {e}")

            lines.append(f"")

        content = "\n".join(lines)

        return self.send_markdown(title, content)


def create_notifier() -> DingDingNotifier:
    """创建通知器实例"""
    return DingDingNotifier()