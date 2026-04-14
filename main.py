"""
股票均线交叉检测系统 - 主程序入口
"""
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

import config
from src.scanner import Scanner
from src.notifier import create_notifier
from src.scheduler import Scheduler


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
    logger.info(f"K线周期: {config.KLINE_PERIOD}分钟")
    logger.info(f"均线参数: MA{config.MA_SHORT} / MA{config.MA_LONG}")
    logger.info(f"扫描间隔: 每{config.SCAN_INTERVAL_HOURS}小时")
    logger.info("=" * 50)

    # 检查钉钉配置
    if not config.DINGDING_WEBHOOK:
        logger.warning("未配置钉钉Webhook，通知功能将不可用")
        logger.warning("请编辑 .env 文件设置 DINGDING_WEBHOOK")

    # 创建组件
    scanner = Scanner()
    notifier = create_notifier()

    def scan_and_notify() -> None:
        """扫描并发送通知（定时任务使用，不重置状态）"""
        result = scanner.run_single_scan(force_backtrack=False, reset_state=False)
        # 发送扫描完成通知（无论是否有信号）
        notifier.notify_scan_complete(
            total_scanned=result["total"],
            success_scanned=result["success"],
            signal_count=len(result["signals"]),
            elapsed_seconds=result["elapsed"],
            reference_date=result["reference_date"]
        )
        # 如果有金叉信号，发送详细通知
        if result["signals"]:
            notifier.notify_golden_cross(result["signals"])

    def backtrack_and_notify() -> None:
        """回溯扫描并发送通知（启动时使用，重置状态允许重新通知）"""
        result = scanner.run_single_scan(force_backtrack=True, reset_state=True)
        # 发送扫描完成通知（无论是否有信号）
        notifier.notify_scan_complete(
            total_scanned=result["total"],
            success_scanned=result["success"],
            signal_count=len(result["signals"]),
            elapsed_seconds=result["elapsed"],
            reference_date=result["reference_date"]
        )
        # 如果有金叉信号，发送详细通知
        if result["signals"]:
            notifier.notify_golden_cross(result["signals"])

    # 创建调度器（启动时回溯，定时任务正常）
    scheduler = Scheduler(scan_and_notify, backtrack_and_notify)

    # 设置信号处理（优雅退出）
    def signal_handler(sig, frame):
        logger.info("收到退出信号，正在停止...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动时立即执行一次扫描
    scheduler.run_once()

    # 设置定时任务
    scheduler.setup_schedule()

    # 运行调度器
    try:
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("用户中断，退出程序")
        scheduler.stop()


if __name__ == "__main__":
    main()