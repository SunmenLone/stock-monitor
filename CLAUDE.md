# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

沪深300均线交叉检测系统 - 自动监控沪深300股票，检测MA5/MA20金叉信号，通过钉钉群机器人发送通知。

## Commands

```bash
# 运行系统
python main.py

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env  # 编辑填写 DINGDING_WEBHOOK
```

## Architecture

### Core Flow

```
main.py → DailyScheduler → DailyScanner → DataSource(BaoStock)
                                    ↓
                              DailyCache(增量更新)
                                    ↓
                              DailyState(进度管理)
                                    ↓
                              Notifier(钉钉通知)
```

### Key Modules

| Module | Responsibility |
|--------|---------------|
| `daily_scanner.py` | 扫描沪深300，检测日K金叉信号 |
| `daily_scheduler.py` | 16-19点定时调度（间隔30分钟） |
| `daily_cache.py` | 日K缓存，增量拉取，保留最近30条 |
| `daily_state.py` | 每日检测进度，pending_stocks列表 |
| `data_source.py` | BaoStock数据源，支持增量拉取(start_date参数) |
| `notifier.py` | 钉钉通知：开始、完成统计、金叉信号 |

### Data Flow

1. 启动时执行检测，遍历pending_stocks（使用`list()`副本避免遍历中修改）
2. 检查缓存：`get_with_check()` → 返回 `data`, `last_kline_time`, `needs_update`
3. 增量拉取：`get_stock_daily_klines(code, start_date=last_kline_time)`
4. 合并数据：`merge_and_set()` 合并新旧K线，去重，截取最近30条
5. 更新进度：`update_progress()` 从pending移除，检测完成时`mark_completed()`

## Key Patterns

### 增量拉取
- 缓存存储`last_kline_time`（最后K线日期）
- 拉取时传递`start_date`参数，只获取缺失的新数据
- 合并新旧数据后截取最近30条

### 进度管理
- `pending_stocks`列表存储待检测股票代码
- 遍历时使用`list()`创建副本（避免遍历中修改原列表）
- 检测完成条件：`pending_count == 0` → `mark_completed()`

### 缓存保留
- 日期变更后不清空缓存，保留历史数据
- `clear_expired()`仅更新日期字段，不删除文件

### 通知时机
- 开始检测：`notify_daily_scan_start()`
- 完成检测：先`mark_completed()`再`notify_daily_scan_complete()`（确保completed状态正确）

## Configuration

关键配置项（`config.py`）：

```python
DAILY_KLINE_DAYS = 30       # 日K数据保留天数
MA_SHORT_KLINES_DAILY = 5   # MA5均线周期
MA_LONG_KLINES_DAILY = 20   # MA20均线周期
DAILY_SCAN_TIMES = ["16:00", "16:30", ...]  # 定时检测时间
```

## Data Files

```
data/
├── daily_klines_cache/{code}.json  # 日K缓存，结构见daily_cache.py
├── daily_scan_state.json           # 每日状态：pending_stocks, signals, completed
├── hs300_stocks.json                # 沪深300股票列表缓存
├── trade_dates.json                 # 交易日历缓存
```