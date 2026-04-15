"""
股票均线交叉检测系统配置模块
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 钉钉配置
DINGDING_WEBHOOK = os.getenv("DINGDING_WEBHOOK", "")
DINGDING_SECRET = os.getenv("DINGDING_SECRET", "")  # 可选签名密钥

# 阿里云OSS配置（可选）
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")  # 如: oss-cn-shanghai.aliyuncs.com
OSS_PREFIX = os.getenv("OSS_PREFIX", "stock-charts/")  # 上传路径前缀

# 日K检测配置
MA_SHORT_DAYS = 5  # 日K短期均线周期（天）
MA_LONG_DAYS = 20  # 日K长期均线周期（天）
DAILY_KLINE_DAYS = 30  # 获取日K天数（略多于MA20）

# 日K均线所需K线数（日K：1天=1根）
MA_SHORT_KLINES_DAILY = MA_SHORT_DAYS  # 5根
MA_LONG_KLINES_DAILY = MA_LONG_DAYS   # 20根

# ========== 新架构配置 ==========

# 默认检测条件配置
DEFAULT_INDICATORS = ["MA5", "MA20"]  # 默认计算的指标列表
DEFAULT_CONDITIONS = ["golden_cross"]  # 默认的检测条件列表

# 指标引擎配置（可扩展）
INDICATOR_CONFIGS = {
    "daily_kline": {
        "ma": {"short": MA_SHORT_DAYS, "long": MA_LONG_DAYS},
        # 后续可添加更多指标配置，如：
        # "macd": {"fast": 12, "slow": 26, "signal": 9},
        # "kdj": {"k": 9, "d": 3, "j": 3},
    }
}

# 检测条件配置（可扩展）
CONDITION_CONFIGS = {
    "daily_kline": {
        "cross": {"short": MA_SHORT_DAYS, "long": MA_LONG_DAYS},
        # 后续可添加更多检测条件配置
    }
}

# 日K检测时间窗口（16:00-19:00，间隔30分钟）
DAILY_SCAN_TIMES = [
    "16:00",
    "16:30",
    "17:00",
    "17:30",
    "18:00",
    "18:30",
    "19:00",
]

# 交易时间配置（用于判断是否交易日）
TRADING_MORNING_START = "09:30"
TRADING_MORNING_END = "11:30"
TRADING_AFTERNOON_START = "13:00"
TRADING_AFTERNOON_END = "15:00"

# 数据文件路径
HS300_CACHE_FILE = "data/hs300_stocks.json"
TRADE_DATE_CACHE_FILE = "data/trade_dates.json"
DAILY_KLINES_CACHE_DIR = "data/daily_klines_cache"  # 日K缓存目录
DAILY_SCAN_STATE_FILE = "data/daily_scan_state.json"  # 每日检测状态文件

# 日K检测：仅BaoStock
DATASOURCE_AVAILABLE_DAILY = {"tushare": False, "baostock": True, "akshare": False}

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