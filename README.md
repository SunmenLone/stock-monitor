# 沪深300信号检测系统

自动监控沪深300股票，检测复合信号条件，并通过钉钉群机器人发送通知。

## 检测条件

满足以下**全部条件**即触发信号：

| 条件 | 说明 |
|------|------|
| **金叉+DIF>0** | MA5上穿MA20（金叉） 且 DIF > 0 |

### 条件详解

- **金叉**：MA5从下方穿越MA20（前日MA5≤MA20，当日MA5>MA20）
- **DIF>0**：MACD的DIF线在零轴上方

## 功能特性

- 监控沪深300全部300只股票
- 使用日K线计算MA5/MA10/MA20均线和MACD指标
- 复合信号检测（金叉+DIF>0）
- 每日16:00-19:00时段检测（间隔30分钟）
- 启动即检测，当天完成不再重复
- **增量拉取**：根据缓存中最后K线日期，只拉取缺失的新数据
- 钉钉群机器人实时通知
- 日K数据缓存，保留最近30条历史数据

## 安装

```bash
# 克隆仓库
git clone https://github.com/SunmenLone/stock-monitor.git
cd stock-monitor

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

复制配置模板并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写钉钉机器人配置：

```env
# 钉钉群机器人Webhook URL（必填）
DINGDING_WEBHOOK=https://oapi.dingtalk.com/sendmsg?access_token=YOUR_TOKEN

# 钉钉签名密钥（可选，如启用加签验证）
DINGDING_SECRET=YOUR_SECRET
```

## 数据源

| 数据源 | 说明 |
|--------|------|
| **BaoStock** | 日K数据源，免费无需注册，稳定无风控 |

## 扫描时间

| 时间 | 说明 |
|------|------|
| 16:00 - 19:00 | 收盘后检测窗口，每30分钟一轮 |

说明：
- 启动时立即执行检测（如果目标日期未完成）
- **目标日期**：使用最新交易日（而非当前日期）
- 目标日期检测完成后，后续时间点不再执行
- 未完成的股票下次继续检测（数据需同步到目标日期）

## 使用

```bash
# 激活虚拟环境后启动
venv\Scripts\python.exe main.py
```

## 项目结构

```
stock-monitor/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── requirements.txt     # 依赖列表
├── .env.example         # 配置模板
├── src/
│   ├── data_source.py       # 数据获取（BaoStock）
│   ├── data_sync_service.py # 数据同步服务
│   ├── scan_orchestrator.py # 扫描编排器
│   ├── daily_scheduler.py   # 日K调度器
│   ├── daily_cache.py       # 日K缓存
│   ├── daily_state.py       # 每日检测状态
│   ├── indicators/          # 指标计算框架
│   │   ├── ma.py            # MA/EMA均线
│   │   ├── macd.py          # MACD指标
│   │   ├── engine.py        # 指标计算引擎
│   ├── detection/           # 信号检测框架
│   │   ├── golden_cross.py  # 金叉/死叉检测
│   │   ├── golden_cross_macd.py  # 复合条件检测
│   │   ├── detector.py      # 信号检测器
│   ├── notifier.py          # 钉钉通知
├── data/
│   ├── daily_klines_cache/  # 日K缓存目录
│   ├── daily_scan_state.json  # 每日检测状态
│   ├── hs300_stocks.json    # 沪深300股票列表
│   ├── trade_dates.json     # 交易日历（last_sync_date记录同步时间）
├── logs/                    # 日志目录
```

## 通知示例

### 开始检测

```
🔍 股票信号检测启动
时间: 2026-04-15 16:00
总股票: 300只
待检测: 300只

系统正在检测沪深300股票信号，请稍候...
```

### 完成统计

```
✅ 股票信号检测完成 (5只信号)
完成时间: 2026-04-15 18:52
总股票: 300只
完成检测: 300只
耗时: 288.5秒

当日状态: 已完成（目标日期不再检测）
检测信号: 📊 5 只
```

### 信号详情

```
📊 检测信号 (5只)
检测时间: 2026-04-15 18:52

---

### 平安银行 (000001)
- **触发条件**: 金叉+DIF>0
- 当前价: **10.50**
- MA5: 10.52
- MA10: 10.30
- MA20: 10.48
- 均线差: +0.38%
- DIF: 0.1234
- K线日期: 2026-04-15
```

## 技术参数

| 参数 | 值 |
|------|-----|
| K线周期 | 日K线 |
| 短期均线 | MA5 |
| 中期均线 | MA10 |
| 长期均线 | MA20 |
| MACD快线 | 12周期 |
| MACD慢线 | 26周期 |
| MACD信号线 | 9周期 |
| 数据源 | BaoStock |
| 缓存保留 | 最近30条日K |

## 扩展指南

详见 [INDICATORS.md](INDICATORS.md)

### 新增指标

```python
# src/indicators/my_indicator.py
from src.indicators.base import Indicator

class MyIndicator(Indicator):
    @property
    def name(self) -> str:
        return "MY_IND"
    
    def calculate(self, data):
        # 计算逻辑
        return result
```

### 新增检测条件

```python
# src/detection/my_condition.py
from src.detection.base import SignalCondition

class MyCondition(SignalCondition):
    @property
    def required_indicators(self) -> list:
        return ["MY_IND"]
    
    def detect(self, code, name, data, indicators):
        # 检测逻辑
        return signal
```

## License

MIT