"""
股票均线交叉检测系统 - 主程序入口
"""
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

import config
from src.notifier import create_notifier
from src.scan_orchestrator import ScanOrchestrator
from src.daily_scheduler import DailyScheduler


def setup_logging() -> None:
    """配置日志"""
    log_dir = Path(config.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"stock_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main() -> None:
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("股票均线交叉检测系统启动")
    logger.info(f"监控范围: 沪深300")
    logger.info(f"日K检测时间: {config.DAILY_SCAN_TIMES}")
    logger.info("=" * 50)

    # 检查钉钉配置
    if not config.DINGDING_WEBHOOK:
        logger.warning("未配置钉钉Webhook，通知功能将不可用")
        logger.warning("请编辑 .env 文件设置 DINGDING_WEBHOOK")

    # 创建通知器
    notifier = create_notifier()

    # 日K检测模块（使用新架构的编排器）
    orchestrator = ScanOrchestrator()

    def daily_scan_and_notify() -> None:
        """日K检测并发送通知"""
        result = orchestrator.orchestrate_daily_scan()
        if result.get("signals"):
            notifier.notify_golden_cross_daily(result["signals"])

    # 创建日K调度器
    daily_scheduler = DailyScheduler(daily_scan_and_notify)

    # 启动时立即执行日K检测
    daily_scheduler.run_once()

    # 设置日K定时任务（16-19点）
    daily_scheduler.setup_schedule()

    # 设置信号处理（优雅退出）
    def signal_handler(sig, frame):
        logger.info("收到退出信号，正在停止...")
        daily_scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 运行日K调度器
    try:
        daily_scheduler.run()
    except KeyboardInterrupt:
        logger.info("用户中断，退出程序")
        daily_scheduler.stop()


if __name__ == "__main__":
    main()