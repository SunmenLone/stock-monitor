# 沪深300均线交叉检测系统

自动监控沪深300股票，检测MA5/MA20金叉信号，并通过钉钉群机器人发送通知。

- 监控沪深300全部300只股票
- 使用15分钟K线计算MA5和MA20均线
- 自动检测金叉信号（MA5上穿MA20）
- 定时扫描（交易时间每小时）
- 钉钉群机器人实时通知
- 图表上传阿里云OSS，通知中显示图表链接
- 支持非交易日启动时回溯最近交易日数据
- 通知去重，避免重复通知同一信号

## 安装

```bash
# 克隆仓库
git clone https://github.com/SunmenLone/stock-monitor.git
cd stock-v2

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

复制配置模板并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写以下配置：

```env
# 钉钉群机器人Webhook URL
DINGDING_WEBHOOK=https://oapi.dingtalk.com/sendmsg?access_token=YOUR_TOKEN

# 钉钉签名密钥（可选）
DINGDING_SECRET=YOUR_SECRET

# 阿里云OSS配置（用于上传图表图片）
OSS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET=YOUR_ACCESS_KEY_SECRET
OSS_BUCKET_NAME=your-bucket-name
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_PREFIX=stock-charts/
```

### 钉钉机器人配置

1. 在钉钉群中添加自定义机器人
2. 获取Webhook URL和签名密钥（如启用加签）
3. 填入 `.env` 文件

### 阿里云OSS配置

1. 创建OSS Bucket并设置为公开读
2. 创建AccessKey并填入配置
3. Endpoint根据Bucket所在区域设置

## 使用

```bash
# 启动程序（后台运行）
source venv/bin/activate
python main.py

# 单次扫描（测试）
python main.py --once

# 测试OSS上传
python test_oss.py
```

## 项目结构

```
stock-v2/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── requirements.txt     # 依赖列表
├── .env.example         # 配置模板
├── test_oss.py          # OSS上传测试
├── src/
│   ├── data_source.py   # 数据获取（BaoStock主源）
│   ├── scanner.py       # 股票扫描器
│   ├── indicators.py    # 技术指标计算
│   ├── notifier.py      # 钉钉通知
│   ├── chart_generator.py # 图表生成
│   ├── oss_uploader.py  # OSS上传
│   ├── scheduler.py     # 定时调度
│   ├── state_manager.py # 通知状态管理
│   └── cache.py         # K线缓存
├── data/                # 数据缓存目录
├── logs/                # 日志目录
└── charts/              # 图表目录
```

## 扫描逻辑

1. **启动扫描**：清除状态，重新检测所有金叉信号并通知
2. **定时扫描**：保留状态，只通知新出现的金叉信号
3. **非交易日**：自动回溯到最近交易日数据

## 通知示例

```
📊 沪深300金叉信号检测

检测时间: 2026-04-03 14:30
信号数量: 2只

---

### 山金国际 (000975)
- 当前价: 29.50
- MA5: 29.90
- MA20: 29.88
- 均线差: +0.07%

📈 [查看均线图表](https://your-bucket.oss-cn-shanghai.aliyuncs.com/stock-charts/000975.png)
```

## 技术参数

- K线周期：15分钟
- 短期均线：MA5（约80根15分钟K线）
- 长期均线：MA20（约320根15分钟K线）
- 扫描间隔：每小时（交易时间）
- 数据源：BaoStock（主），AkShare（备用）

## License

MIT