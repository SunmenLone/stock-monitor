# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

沪深 300 信号检测系统 - 自动监控沪深 300 股票，检测复合信号条件，通过钉钉群机器人发送通知。

### 检测条件

满足以下条件即触发信号：
- **金叉+DIF>0**：MA5上穿MA20（金叉） 且 DIF > 0

## Commands

<!-- AUTO-GENERATED -->
```bash
# 运行系统（激活venv后）
python main.py

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env  # 编辑填写 DINGDING_WEBHOOK

# 测试模块导入
venv/Scripts/python.exe -c "from src.detection import create_detector_with_macd; print('OK')"
```
<!-- END AUTO-GENERATED -->

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

| 层次       | 模块                        | 职责                             |
| ---------- | --------------------------- | -------------------------------- |
| **数据层** | `data_sync_service.py`      | 数据同步服务，增量拉取，合并缓存 |
|            | `daily_cache.py`            | 日 K 缓存读写，数据合并          |
|            | `data_source.py`            | BaoStock 数据源接口              |
| **指标层** | `indicators/base.py`        | 指标抽象基类                     |
|            | `indicators/registry.py`    | 指标注册中心                     |
|            | `indicators/ma.py`          | 均线指标实现                     |
|            | `indicators/macd.py`        | MACD指标实现                     |
|            | `indicators/engine.py`      | 批量计算引擎                     |
| **检测层** | `detection/base.py`         | Signal 数据类 + 检测条件基类     |
|            | `detection/registry.py`     | 检测条件注册中心                 |
|            | `detection/golden_cross.py` | 金叉/死叉检测                    |
|            | `detection/golden_cross_macd.py` | 复合检测条件（MA+MACD）     |
|            | `detection/detector.py`     | 信号检测器                       |
| **编排层** | `scan_orchestrator.py`      | 编排完整检测流程                 |
|            | `daily_state.py`            | 检测进度状态管理                 |
|            | `daily_scheduler.py`        | 定时任务调度                     |
|            | `notifier.py`               | 钉钉通知                         |

### Core Flow

```
ScanOrchestrator.orchestrate_daily_scan(silent_mode=False):
1. 获取目标日期（最新交易日） → get_latest_trade_date()
2. 检查是否已完成 → 跳过已完成的目标日期
3. 新的目标日期 → 初始化状态，清理过期缓存
4. 播报开始（silent_mode时跳过）
5. 遍历pending_stocks（使用副本）
   a. DataSyncService.sync_stock_data() → 数据同步
   b. 检查数据是否同步到目标日期 → is_data_current()
   c. SignalDetector.detect() → 指标计算 + 条件检测
   d. DailyState.update_progress() → 更新进度（数据完整才移除）
6. 播报完成（silent_mode时只发送信号通知）
```

**关键变更**：
- 使用 **最新交易日** 作为目标日期，而非当前日期
- 启动时 (`silent_mode=True`)：
  - 即使数据未同步到最新交易日，也用现有缓存数据检测
  - 只播报信号通知，跳过启动/完成通知
  - 不更新进度，不标记完成
- 定时触发 (`silent_mode=False`)：
  - 数据需同步到目标日期才算完整
  - 正常播报所有通知
  - 更新进度，标记完成

## Key Patterns

### 数据同步分离

- `DataSyncService` 独立负责数据同步
- `sync_stock_data()` 返回 `DataSyncResult`，包含数据和状态信息
- 增量拉取逻辑封装在服务内部
- **数据完整性判断**：使用 `get_target_date()`（最新交易日），而非当前日期

### 目标日期逻辑

- `DataSource.get_latest_trade_date()` 返回最近交易日
- 启动时：即使在周末或节假日，也能检测最新交易日数据
- 定时触发：仅在交易日运行，且数据需同步到目标日期

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

- 缓存存储 `last_kline_time`（最后 K 线日期）
- 拉取时传递 `start_date` 参数，只获取缺失的新数据
- 合并新旧数据后截取最近 30 条

### 进度管理

- `pending_stocks` 列表存储待检测股票代码
- 遍历时使用 `list()` 创建副本（避免遍历中修改原列表）
- 检测完成条件：`pending_count == 0` → `mark_completed()`
- **数据完整性要求**：只有数据同步到目标日期才从pending移除

### 缓存保留

- 日期变更后不清空缓存，保留历史数据
- `clear_expired()` 仅更新日期字段，不删除文件

## 扩展指南

### 已实现的指标

| 指标 | 输出字段 | 文件 |
|------|----------|------|
| MA | MA5, MA10, MA20 | `src/indicators/ma.py` |
| MACD | DIF, DEA, MACD | `src/indicators/macd.py` |

### 已实现的检测条件

| 条件 | 所需指标 | 文件 |
|------|----------|------|
| 金叉/死叉 | MA5, MA20 | `src/detection/golden_cross.py` |
| 复合条件 | MA5, MA10, MA20, DIF | `src/detection/golden_cross_macd.py` |

### 新增指标示例

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

<!-- AUTO-GENERATED -->
关键配置项（`config.py`）：

```python
# 均线配置
MA_SHORT_DAYS = 5           # 短期均线周期
MA_LONG_DAYS = 20           # 长期均线周期
DAILY_KLINE_DAYS = 30       # 日K数据保留天数

# 检测时间窗口
DAILY_SCAN_TIMES = ["16:00", "16:30", ...]  # 定时检测时间

# 指标配置（已实现）
DEFAULT_INDICATORS = ["MA5", "MA10", "MA20", "DIF", "DEA", "MACD"]
DEFAULT_CONDITIONS = ["golden_cross_with_macd"]

INDICATOR_CONFIGS = {
    "daily_kline": {
        "ma": {"short": 5, "long": 20},
        "macd": {"fast": 12, "slow": 26, "signal": 9},
    }
}
```

## Environment Variables

<!-- AUTO-GENERATED -->
| Variable | Required | Description |
|----------|----------|-------------|
| `DINGDING_WEBHOOK` | Yes | 钉钉群机器人Webhook URL |
| `DINGDING_SECRET` | No | 钉钉签名密钥（加签验证） |
| `OSS_ACCESS_KEY_ID` | No | 阿里云OSS访问密钥ID |
| `OSS_ACCESS_KEY_SECRET` | No | 阿里云OSS访问密钥 |
| `OSS_BUCKET_NAME` | No | OSS Bucket名称 |
| `OSS_ENDPOINT` | No | OSS Endpoint（如：oss-cn-shanghai.aliyuncs.com） |
<!-- END AUTO-GENERATED -->

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

## 通知格式

检测到信号时，钉钉通知包含以下信息：

```
### 平安银行 (000001)
- **触发条件**: 金叉+DIF>0
- 当前价: **10.00**
- MA5: 9.80
- MA10: 9.50
- MA20: 9.20
- 均线差: +6.52%
- DIF: 0.1234
- K线日期: 2024-01-15
```

触发条件类型：
- "金叉+DIF>0"

## 程序测试

激活 venv 环境后再使用 python 命令
