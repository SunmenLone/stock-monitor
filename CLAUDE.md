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

### 新架构设计（2026-04-15 重构）

采用分层架构，数据同步与信号检测分离：

```
main.py → DailyScheduler → ScanOrchestrator (编排层)
                                │
        ┌───────────────────────┼───────────────────────┐
        ↓                       ↓                       ↓
  DataSyncService         IndicatorEngine          SignalDetector
    (数据同步层)             (指标计算层)             (信号检测层)
        │                       │                       │
        ↓                       ↓                       ↓
  DailyKlineCache         IndicatorRegistry        SignalRegistry
    (缓存管理)               (指标注册)               (条件注册)
        │
        ↓
    DataSource
    (BaoStock)
```

### 模块职责

| 层次 | 模块 | 职责 |
|------|------|------|
| **数据层** | `data_sync_service.py` | 数据同步服务，增量拉取，合并缓存 |
| | `daily_cache.py` | 日K缓存读写，数据合并 |
| | `data_source.py` | BaoStock数据源接口 |
| **指标层** | `indicators/base.py` | 指标抽象基类 |
| | `indicators/registry.py` | 指标注册中心 |
| | `indicators/ma.py` | 均线指标实现 |
| | `indicators/engine.py` | 批量计算引擎 |
| **检测层** | `detection/base.py` | Signal数据类 + 检测条件基类 |
| | `detection/registry.py` | 检测条件注册中心 |
| | `detection/golden_cross.py` | 金叉/死叉检测 |
| | `detection/detector.py` | 信号检测器 |
| **编排层** | `scan_orchestrator.py` | 编排完整检测流程 |
| | `daily_state.py` | 检测进度状态管理 |
| | `daily_scheduler.py` | 定时任务调度 |
| | `notifier.py` | 钉钉通知 |

### Core Flow

```
ScanOrchestrator.orchestrate_daily_scan():
1. 检查是否已完成 → 跳过已完成的日期
2. 新的一天 → 初始化状态，清理过期缓存
3. 遍历pending_stocks（使用副本）
   a. DataSyncService.sync_stock_data() → 数据同步
   b. SignalDetector.detect() → 指标计算 + 条件检测
   c. DailyState.update_progress() → 更新进度
4. 全部完成 → mark_completed() + notify_daily_scan_complete()
```

## Key Patterns

### 数据同步分离
- `DataSyncService` 独立负责数据同步
- `sync_stock_data()` 返回 `DataSyncResult`，包含数据和状态信息
- 增量拉取逻辑封装在服务内部

### 指标计算框架
- `Indicator` 抽象基类定义标准接口
- `IndicatorRegistry` 管理已注册指标
- `IndicatorEngine` 批量计算所需指标
- 新增指标只需继承 `Indicator` 并注册

### 信号检测框架
- `SignalCondition` 抽象基类定义检测接口
- `SignalRegistry` 管理已注册检测条件
- `SignalDetector` 整合指标计算和条件检测
- 新增检测条件只需继承 `SignalCondition` 并注册

### 增量拉取
- 缓存存储 `last_kline_time`（最后K线日期）
- 拉取时传递 `start_date` 参数，只获取缺失的新数据
- 合并新旧数据后截取最近30条

### 进度管理
- `pending_stocks` 列表存储待检测股票代码
- 遍历时使用 `list()` 创建副本（避免遍历中修改原列表）
- 检测完成条件：`pending_count == 0` → `mark_completed()`

### 缓存保留
- 日期变更后不清空缓存，保留历史数据
- `clear_expired()` 仅更新日期字段，不删除文件

## 扩展指南

### 新增指标

```python
# src/indicators/macd.py
from src.indicators.base import Indicator

class MACDIndicator(Indicator):
    def __init__(self, fast=12, slow=26, signal=9):
        self._fast = fast
        self._name = "MACD"
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def required_data(self) -> str:
        return "daily_kline"
    
    def calculate(self, data):
        # MACD 计算逻辑
        ...
```

### 新增检测条件

```python
# src/detection/macd_cross.py
from src.detection.base import SignalCondition

class MACDCrossCondition(SignalCondition):
    @property
    def name(self) -> str:
        return "macd_golden_cross"
    
    @property
    def required_indicators(self) -> list:
        return ["DIF", "DEA"]
    
    def detect(self, code, name, data, indicators):
        # MACD 金叉检测逻辑
        ...
```

详细扩展指南见 `INDICATORS.md`。

## Configuration

关键配置项（`config.py`）：

```python
DAILY_KLINE_DAYS = 30       # 日K数据保留天数
MA_SHORT_DAYS = 5           # MA5均线周期
MA_LONG_DAYS = 20           # MA20均线周期
DAILY_SCAN_TIMES = ["16:00", "16:30", ...]  # 定时检测时间

# 新架构配置
DEFAULT_INDICATORS = ["MA5", "MA20"]
DEFAULT_CONDITIONS = ["golden_cross"]
INDICATOR_CONFIGS = {"daily_kline": {"ma": {...}}}
CONDITION_CONFIGS = {"daily_kline": {"cross": {...}}}
```

## Data Files

```
data/
├── daily_klines_cache/{code}.json  # 日K缓存
├── daily_scan_state.json           # 每日状态
├── hs300_stocks.json               # 沪深300股票列表
├── trade_dates.json                # 交易日历
```

## 向后兼容

重构保持了向后兼容：
- `indicators_legacy.py` 保留原有函数
- `daily_scanner.py` 使用新服务但保持接口不变
- 原有代码可继续使用 `calculate_indicators_daily()` 等函数