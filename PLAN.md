# 股票均线交叉搜索与钉钉通知系统

## Context

用户需要一个自动化系统来监控沪深300股票，检测15分钟K线上的均线交叉信号，并通过钉钉发送通知。

### 需求详情
- **搜索范围**：沪深300成分股
- **K线周期**：15分钟K线
- **搜索条件**：5日均线上穿20日均线（金叉信号）
- **均线计算**：基于日历时间（过去N个交易日的数据）
- **搜索间隔**：1小时
- **运行时间**：仅交易时间（工作日9:30-15:00）
- **通知方式**：钉钉群Webhook
- **Python环境**：使用venv虚拟环境

---

## Optimization Suggestions

### 1. 信号去重机制
**问题**：金叉信号可能持续多根K线，每小时扫描会重复通知。
**方案**：记录已通知的股票，同一金叉信号只通知一次，当均线死叉后重置状态。

### 2. 错过开盘时段处理
**问题**：如果程序在10:00启动，会错过9:30的扫描。
**方案**：程序启动时立即执行一次扫描，然后再进入定时循环。

### 3. 容错与重试
**问题**：网络请求可能失败，导致数据获取异常。
**方案**：
- 添加请求重试机制（最多3次）
- 单只股票失败不影响其他股票扫描
- 记录失败日志便于排查

### 4. 数据本地缓存
**问题**：每小时重新获取所有300只股票的K线数据，请求量大。
**方案**：
- 缓存已获取的K线数据，下一小时只增量获取新数据
- 减少API调用次数，提高响应速度

---

## Implementation Plan

### 项目结构

```
stock-v2/
├── main.py              # 主程序入口
├── config.py            # 配置文件（钉钉webhook、时间参数等）
├── requirements.txt     # 依赖包
├── setup.sh             # 环境初始化脚本
├── .env.example         # 环境变量示例文件
├── data/
│   ├── hs300_stocks.json      # 沪深300股票列表缓存
│   ├── notified_state.json    # 已通知股票状态
│   └── klines_cache/          # K线数据缓存目录
├── src/
│   ├── __init__.py
│   ├── data_source.py   # 股票数据获取（AkShare）
│   ├── indicators.py    # 技术指标计算（均线）
│   ├── scanner.py       # 股票扫描逻辑
│   ├── notifier.py      # 钉钉通知
│   ├── scheduler.py     # 定时任务调度
│   ├── state_manager.py # 信号状态管理（去重）
│   └── cache.py         # 数据缓存管理
└── logs/                # 日志目录
```

### Step 0: 创建虚拟环境

**文件**: `setup.sh`

```bash
#!/bin/bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**使用方式**：
```bash
# 首次运行
chmod +x setup.sh && ./setup.sh

# 后续运行
source venv/bin/activate && python main.py
```

### Step 1: 创建配置文件

**文件**: `config.py`

配置项：
- 钉钉 Webhook URL（从环境变量读取）
- K线周期：15分钟
- 均线参数：MA5, MA20
- 扫描间隔：1小时
- 交易时间段：9:30-11:30, 13:00-15:00

### Step 2: 实现数据获取模块

**文件**: `src/data_source.py`

功能：
- 获取沪深300股票列表（使用AkShare的`index_stock_cons_weight_csindex`接口）
- 获取股票15分钟K线数据（使用AkShare的`stock_zh_a_hist_min_em`接口）
- 实现数据缓存，避免频繁请求

关键代码逻辑：
```python
# 获取沪深300成分股
def get_hs300_stocks() -> List[dict]

# 获取单只股票的15分钟K线
def get_stock_klines(code: str, days: int = 30) -> pd.DataFrame
```

### Step 3: 实现技术指标计算

**文件**: `src/indicators.py`

均线计算逻辑：
- 在15分钟K线上计算均线
- 5日均线：过去5个交易日的数据点收盘价均值
- 交易日约16根15分钟K线（4小时交易时间）
- MA5 ≈ 80根K线（5天 × 16根/天）
- MA20 ≈ 320根K线（20天 × 16根/天）

关键代码逻辑：
```python
def calculate_ma(close_prices: pd.Series, period: int) -> pd.Series

def detect_golden_cross(ma5: pd.Series, ma20: pd.Series) -> bool
```

### Step 4: 实现股票扫描器

**文件**: `src/scanner.py`

扫描逻辑：
1. 遍历沪深300股票列表
2. 获取每只股票的15分钟K线数据
3. 计算MA5和MA20
4. 检测金叉信号（前一根K线MA5<=MA20，当前K线MA5>MA20）
5. 收集所有符合条件的股票

### Step 5: 实现钉钉通知

**文件**: `src/notifier.py`

功能：
- 发送Markdown格式的消息到钉钉群
- 消息内容包括：股票代码、股票名称、触发时间、当前价格、均线值

### Step 6: 实现定时调度

**文件**: `src/scheduler.py`

调度逻辑：
- 使用`schedule`库实现定时任务
- 每小时执行一次扫描（交易时间内）
- 检查当前是否为交易时间
- **优化**：程序启动时立即执行一次扫描

### Step 7: 实现信号状态管理

**文件**: `src/state_manager.py`

状态管理（信号去重）：
- 使用JSON文件记录已通知的股票及其状态
- 金叉信号检测到后记录状态，避免重复通知
- 检测到死叉后清除该股票的通知状态
- 状态文件：`data/notified_state.json`

```python
# 状态结构示例
{
    "000001": {
        "notified_at": "2024-01-15 10:30:00",
        "ma5": 10.5,
        "ma20": 10.3,
        "status": "golden_cross"
    }
}
```

### Step 8: 实现数据缓存

**文件**: `src/cache.py`

缓存逻辑：
- 缓存K线数据到本地JSON文件
- 每次获取新数据时，只增量获取最新部分
- 缓存文件：`data/klines_cache/{code}.json`
- 缓存有效期：当日有效，隔日清空

### Step 9: 创建主程序入口

**文件**: `main.py`

功能：
- 初始化日志
- 启动定时任务
- **优化**：启动时立即执行一次扫描
- **优化**：异常处理和重试逻辑

---

## Dependencies

```txt
akshare>=1.12.0
pandas>=2.0.0
requests>=2.31.0
schedule>=1.2.0
python-dotenv>=1.0.0
```

---

## Verification

1. **单元测试**：手动运行各模块，验证数据获取和计算正确
2. **集成测试**：
   - 运行扫描器，检查是否能正确识别金叉
   - 测试钉钉通知是否发送成功
3. **定时任务测试**：
   - 设置短间隔（如1分钟）测试调度是否正常
   - 验证交易时间检测逻辑

---

## Notes

- 钉钉Webhook URL从`.env`文件读取，使用`python-dotenv`管理
- `.env.example`提供配置模板，不包含敏感信息
- 日志按日期存储在`logs/`目录，便于问题排查
- 信号去重避免同一金叉重复通知
- 数据缓存减少API调用，提高响应速度