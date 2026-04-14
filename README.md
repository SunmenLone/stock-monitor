# 沪深300均线交叉检测系统

自动监控沪深300股票，检测MA5/MA20金叉信号，并通过钉钉群机器人发送通知。

## 功能特性

- 监控沪深300全部300只股票
- 使用**日K线**计算MA5和MA20均线
- 自动检测金叉信号（MA5上穿MA20）
- 每日16:00-19:00时段检测（间隔30分钟）
- 启动即检测，当天完成不再重复
- **增量拉取**：根据缓存中最后K线日期，只拉取缺失的新数据
- 钉钉群机器人实时通知（开始检测、完成统计、金叉信号）
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

编辑 `.env` 文件，填写以下配置：

### TuShare配置（主数据源）

TuShare是主要数据源，提供稳定的分钟K线数据。

```env
# TuShare Token（必需）
# 注册地址: https://tushare.pro
# 注册后获取Token，免费积分可获取分钟K线
TUSHARE_TOKEN=your_tushare_token_here
```

### 钉钉机器人配置

```env
# 钉钉群机器人Webhook URL
DINGDING_WEBHOOK=https://oapi.dingtalk.com/sendmsg?access_token=YOUR_TOKEN

# 钉钉签名密钥（可选，如启用加签验证）
DINGDING_SECRET=YOUR_SECRET
```

### 阿里云OSS配置（可选）

用于上传图表图片，使通知中显示图表链接。

```env
OSS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET=YOUR_ACCESS_KEY_SECRET
OSS_BUCKET_NAME=your-bucket-name
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_PREFIX=stock-charts/
```

## 数据源

| 数据源 | 说明 |
|--------|------|
| **BaoStock** | 日K数据源，免费无需注册，稳定无风控，无需请求延迟 |

## 扫描时间

| 时间 | 说明 |
|------|------|
| 16:00 | 收盘后首次检测 |
| 16:30 | 第二轮检测 |
| 17:00 | 第三轮检测 |
| 17:30 | 第四轮检测 |
| 18:00 | 第五轮检测 |
| 18:30 | 第六轮检测 |
| 19:00 | 最后一轮检测 |

说明：
- 启动时立即执行检测（如果当天未完成）
- 当天检测完成后，后续时间点不再执行
- 未完成的股票下次继续检测
- BaoStock稳定无风控，无需请求延迟

## 使用

```bash
# 启动程序
python main.py

# 测试数据源
python test_akshare.py
```

## 项目结构

```
stock-monitor/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── requirements.txt     # 依赖列表
├── .env.example         # 配置模板
├── src/
│   ├── data_source.py   # 数据获取（BaoStock日K）
│   ├── daily_scanner.py # 日K扫描器
│   ├── daily_scheduler.py # 日K调度器
│   ├── daily_cache.py   # 日K缓存（增量更新）
│   ├── daily_state.py   # 每日检测状态管理
│   ├── indicators.py    # 技术指标计算
│   ├── notifier.py      # 钉钉通知
├── data/
│   ├── daily_klines_cache/  # 日K缓存目录
│   ├── daily_scan_state.json  # 每日检测状态
│   ├── hs300_stocks.json  # 沪深300股票列表
│   ├── trade_dates.json  # 交易日历
├── logs/                # 日志目录
```

## 通知示例

### 开始检测
```
🔍 日K金叉检测启动
时间: 2026-04-14 16:00
总股票: 300只
已拉取: 0只
待检测: 300只

系统正在检测沪深300日K金叉信号，请稍候...
```

### 完成统计
```
✅ 日K金叉检测完成 (40只金叉)
完成时间: 2026-04-14 18:52
总股票: 300只
完成检测: 300只
待检测: 0只
耗时: 288.5秒

当日状态: 已完成（当天不再检测）
金叉信号: 📊40 只
```

### 金叉信号
```
📊 日K金叉信号 (40只)
检测时间: 2026-04-14 18:52
信号数量: 40只

---

### 平安银行 (000001)
- 当前价: 10.50
- MA5: 10.52
- MA20: 10.48
- 均线差: +0.38%
- K线日期: 2026-04-14
```

## 技术参数

- K线周期：日K线
- 短期均线：MA5（5根日K）
- 长期均线：MA20（20根日K）
- 数据源：BaoStock
- 缓存保留：最近30条日K数据

## 缓存机制

### 日K缓存
- 本地JSON缓存，每个股票一个文件
- **增量拉取**：根据缓存中`last_kline_time`，只获取缺失的新数据
- **数据保留**：日期变更后保留历史数据（最近30条），仅更新日期字段
- 更新判断：最后K线日期距今天 >= 1天则需要更新
- 失败容错：API失败时使用缓存数据

## License

MIT