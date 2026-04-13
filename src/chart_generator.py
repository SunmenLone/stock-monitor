"""
均线图表生成模块 - ASCII文本图 + 本地PNG保存
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use('Agg')  # 无GUI后端
import matplotlib.pyplot as plt
import pandas as pd

import config

logger = logging.getLogger(__name__)

# 图表保存目录
CHART_DIR = Path("charts")
CHART_DIR.mkdir(exist_ok=True)

# 尝试设置中文字体
try:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    logger.warning("无法设置中文字体，图表将使用英文标签")


def generate_ma_chart(
    code: str,
    name: str,
    klines: pd.DataFrame,
    ma_short: pd.Series,
    ma_long: pd.Series,
    close_prices: Optional[pd.Series] = None
) -> dict:
    """
    生成均线图表（ASCII文本图 + PNG图片）

    Args:
        code: 股票代码
        name: 肧票名称
        klines: K线数据
        ma_short: 短期均线序列
        ma_long: 长期均线序列
        close_prices: 收盘价序列（可选）

    Returns:
        {"ascii_chart": str, "png_path": str}
    """
    # 生成PNG图表
    png_path = generate_png_chart(code, name, klines, ma_short, ma_long, close_prices)

    # 生成ASCII文本图
    ascii_chart = generate_ascii_chart(ma_short, ma_long, close_prices)

    return {
        "ascii_chart": ascii_chart,
        "png_path": str(png_path)
    }


def generate_png_chart(
    code: str,
    name: str,
    klines: pd.DataFrame,
    ma_short: pd.Series,
    ma_long: pd.Series,
    close_prices: Optional[pd.Series] = None
) -> Path:
    """
    生成PNG格式的均线图表

    Returns:
        PNG文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    png_path = CHART_DIR / f"{code}_{timestamp}.png"

    # 只取最近的数据点用于绘图（避免图表过大）
    plot_points = min(200, len(klines))

    fig, ax = plt.subplots(figsize=(12, 6))

    # 绘制收盘价
    if close_prices is None:
        close_prices = klines["close"]
    ax.plot(range(plot_points), close_prices.iloc[-plot_points:].values,
            label='Close', color='black', linewidth=1, alpha=0.7)

    # 绘制均线
    ax.plot(range(plot_points), ma_short.iloc[-plot_points:].values,
            label=f'MA{config.MA_SHORT}', color='red', linewidth=1.5)
    ax.plot(range(plot_points), ma_long.iloc[-plot_points:].values,
            label=f'MA{config.MA_LONG}', color='blue', linewidth=1.5)

    # 标记金叉位置（最后位置）
    last_idx = plot_points - 1
    ax.scatter([last_idx], [ma_short.iloc[-1]], color='gold', s=100, zorder=5,
               marker='*', label='Golden Cross')

    ax.set_title(f'{name} ({code}) - MA Cross', fontsize=14)
    ax.set_xlabel('Time (last 200 points)', fontsize=10)
    ax.set_ylabel('Price', fontsize=10)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(png_path, dpi=100, format='png')
    plt.close()

    logger.info(f"生成图表: {png_path}")
    return png_path


def generate_ascii_chart(
    ma_short: pd.Series,
    ma_long: pd.Series,
    close_prices: Optional[pd.Series] = None,
    width: int = 40,
    height: int = 10
) -> str:
    """
    生成ASCII文本格式的均线图表

    Args:
        ma_short: 短期均线序列
        ma_long: 长期均线序列
        close_prices: 收盘价序列（可选）
        width: 图表宽度（字符数）
        height: 图表高度（行数）

    Returns:
        ASCII图表字符串
    """
    # 只取最近的数据点
    points = min(width, len(ma_short))

    # 获取数据范围
    if close_prices is not None:
        all_vals = pd.concat([ma_short.iloc[-points:], ma_long.iloc[-points:], close_prices.iloc[-points:]])
    else:
        all_vals = pd.concat([ma_short.iloc[-points:], ma_long.iloc[-points:]])

    min_val = all_vals.min()
    max_val = all_vals.max()
    val_range = max_val - min_val if max_val != min_val else 1

    # 构建图表网格
    chart_grid = [[' ' for _ in range(points)] for _ in range(height)]

    # 绘制均线（MA5用*，MA20用+）
    for i, val in enumerate(ma_short.iloc[-points:].values):
        if pd.isna(val):
            continue
        row = int((max_val - val) / val_range * (height - 1))
        row = max(0, min(height - 1, row))
        chart_grid[row][i] = '*'

    for i, val in enumerate(ma_long.iloc[-points:].values):
        if pd.isna(val):
            continue
        row = int((max_val - val) / val_range * (height - 1))
        row = max(0, min(height - 1, row))
        # 如果位置已有*，改为#表示交叉
        if chart_grid[row][i] == '*':
            chart_grid[row][i] = '#'
        else:
            chart_grid[row][i] = '+'

    # 构建ASCII图表字符串
    lines = []
    lines.append(f"```")
    lines.append(f"MA Chart (last {points} points, *: MA5, +: MA20, #: cross)")
    lines.append(f"High: {max_val:.2f}")

    for row in chart_grid:
        lines.append(''.join(row))

    lines.append(f"Low:  {min_val:.2f}")
    lines.append(f"```")

    return '\n'.join(lines)


def cleanup_old_charts(days: int = 7) -> int:
    """
    清理旧的图表文件

    Args:
        days: 保留天数

    Returns:
        删除的文件数
    """
    import time
    count = 0
    cutoff = time.time() - days * 86400

    for file in CHART_DIR.glob("*.png"):
        if file.stat().st_mtime < cutoff:
            file.unlink()
            count += 1

    if count > 0:
        logger.info(f"清理 {count} 个旧图表文件")
    return count