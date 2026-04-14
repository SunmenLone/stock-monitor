# 沪深300均线交叉检测系统

自动监控沪深300股票，检测MA5/MA20金叉信号，并通过钉钉群机器人发送通知。

## 功能特性

- 监控沪深300全部300只股票
- 使用15分钟K线计算MA5和MA20均线
- 自动检测金叉信号（MA5上穿MA20）
- 盘中定时扫描 + 收盘后总结扫描
- 钉钉群机器人实时通知
- 图表上传阿里云OSS，通知中显示图表链接
- 支持非交易日启动时回溯最近交易日数据
- 通知去重，避免重复通知同一信号
- 多数据源支持：TuShare（主）、BaoStock（备）、AkShare（备）

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

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| **1** | TuShare | 主数据源，官方API，稳定无风控 |
| **2** | BaoStock | 备用数据源，免费无需注册 |
| **3** | AkShare | 备用数据源，默认不启用（易风控） |

### TuShare注册指南

1. 访问 https://tushare.pro 注册账号
2. 在"用户中心"获取Token
3. 通过签到等方式积累积分（分钟K线需一定积分）
4. 将Token填入 `.env` 文件

## 扫描时间

| 时间 | 类型 | 说明 |
|------|------|------|
| 09:45 | 盘中 | 开盘后15分钟 |
| 10:30 | 盘中 | 盘中检测 |
| 11:15 | 盘中 | 上午收盘前 |
| 13:15 | 盘中 | 下午开盘后 |
| 14:30 | 盘中 | 收盘前半小时 |
| **15:05** | 收盘后 | 总结扫描，指导次日决策 |

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
├── test_akshare.py      # 数据源测试脚本
├── test_oss.py          # OSS上传测试
├── src/
│   ├── data_source.py   # 数据获取（TuShare/BaoStock/AkShare）
│   ├── scanner.py       # 股票扫描器
│   ├── indicators.py    # 技术指标计算
│   ├── notifier.py      # 钉钉通知
│   ├── chart_generator.py # 图表生成
│   ├── oss_uploader.py  # OSS上传
│   ├── scheduler.py     # 定时调度
│   ├── state_manager.py # 通知状态管理
│   ├── cache.py         # K线缓存（增量更新）
├── data/                # 数据缓存目录
├── logs/                # 日志目录
└── charts/              # 图表目录
```

## 通知示例

```
📊 沪深300金叉信号检测

检测时间: 2026-04-14 14:30
信号数量: 2只

---

### 平安银行 (000001)
- 当前价: 10.50
- MA5: 10.52
- MA20: 10.48
- 均线差: +0.38%
- 数据时间: 2026-04-14 14:30

📈 [查看均线图表](https://your-bucket.oss-cn-shanghai.aliyuncs.com/stock-charts/000001.png)
```

## 技术参数

- K线周期：15分钟
- 短期均线：MA5（约80根15分钟K线）
- 长期均线：MA20（约320根15分钟K线）
- 数据源优先级：TuShare → BaoStock → AkShare

## K线缓存机制

- 本地JSON缓存，支持增量更新
- 缓存检查：最后K线时间缺失超过15分钟则更新
- 增量查询：从上次时间回溯30分钟获取新数据
- 失败容错：API失败时使用缓存数据

## License

MIT