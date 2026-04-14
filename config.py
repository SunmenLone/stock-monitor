"""
股票均线交叉检测系统配置模块
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 钉钉配置
DINGDING_WEBHOOK = os.getenv("DINGDING_WEBHOOK", "")
DINGDING_SECRET = os.getenv("DINGDING_SECRET", "")  # 可选签名密钥

# 阿里云OSS配置
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")  # 如: oss-cn-shanghai.aliyuncs.com
OSS_PREFIX = os.getenv("OSS_PREFIX", "stock-charts/")  # 上传路径前缀

# K线配置
KLINE_PERIOD = "15"  # 15分钟K线
MA_SHORT = 5  # 短期均线周期（日）
MA_LONG = 20  # 长期均线周期（日）

# 15分钟K线，每日约16根（4小时交易）
# MA5 ≈ 80根K线（5天 × 16根）
# MA20 ≈ 320根K线（20天 × 16根）
MA_SHORT_KLINES = MA_SHORT * 16  # 80
MA_LONG_KLINES = MA_LONG * 16   # 320

# 扫描配置
SCAN_INTERVAL_HOURS = 1  # 扫描间隔（小时）- 备用配置
SCAN_INTERVAL_SECONDS = SCAN_INTERVAL_HOURS * 3600

# 盘中扫描时间点（交易时间内）
SCAN_TIMES = [
    "09:45",  # 开盘后15分钟
    "10:30",  # 盘中检测
    "11:15",  # 上午收盘前
    "13:15",  # 下午开盘后
    "14:30",  # 收盘前半小时
]

# 收盘后扫描时间（指导次日购入）
SCAN_AFTER_CLOSE = "15:05"  # 收盘后5分钟，获取完整数据

# 交易时间配置
TRADING_MORNING_START = "09:30"
TRADING_MORNING_END = "11:30"
TRADING_AFTERNOON_START = "13:00"
TRADING_AFTERNOON_END = "15:00"

# 数据配置
KLINE_DAYS = 25  # 获取K线天数（略多于MA20所需）
HS300_CACHE_FILE = "data/hs300_stocks.json"
NOTIFIED_STATE_FILE = "data/notified_state.json"
KLINES_CACHE_DIR = "data/klines_cache"
TRADE_DATE_CACHE_FILE = "data/trade_dates.json"

# 网络配置
REQUEST_RETRY_TIMES = 3
REQUEST_TIMEOUT = 10  # 秒

# 请求延迟配置（规避风控）
REQUEST_DELAY_MIN = 1.0  # 最小延迟（秒）
REQUEST_DELAY_MAX = 2.0  # 最大延迟（秒）- 随机范围
REQUEST_DELAY_ON_ERROR = 5.0  # 失败后延迟（秒）

# 日志配置
LOG_DIR = "logs"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"