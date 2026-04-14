"""
数据源K线拉取测试脚本

测试各数据源是否正常工作：TuShare、BaoStock、AkShare
"""
import time
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 测试配置
TEST_STOCKS = [
    "000001",  # 平安银行
    "600519",  # 贵州茅台
    "601318",  # 中国平安
    "600036",  # 招商银行
    "000858",  # 五粮液
    "601166",  # 兴业银行
    "600000",  # 浦发银行
    "601398",  # 工商银行
    "002415",  # 海康威视
    "000333",  # 美的集团
]

# 延迟配置（与主程序一致）
DELAY_MIN = 1.0  # 最小延迟（秒）
DELAY_MAX = 2.0  # 最大延迟（秒）
DELAY_ON_ERROR = 5.0  # 失败后延迟（秒）
RETRY_TIMES = 3  # 重试次数
KLINE_PERIOD = "15"  # 15分钟K线

# TuShare配置
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 伪装浏览器请求头（东方财富）
FAKE_HEADERS_EM = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://quote.eastmoney.com/",
}


def get_ts_code(code: str) -> str:
    """转换为TuShare代码格式（SZ/SH后缀）"""
    if code.startswith("6"):
        return f"{code}.SH"
    else:
        return f"{code}.SZ"


def get_bs_code(code: str) -> str:
    """转换为BaoStock代码格式（sh/sz前缀）"""
    if code.startswith("6"):
        return f"sh.{code}"
    else:
        return f"sz.{code}"


# ========== TuShare 测试 ==========

def test_single_stock_tushare(code: str, ts_pro=None) -> tuple:
    """
    TuShare测试单只股票

    Returns:
        (success: bool, data_info: str)
    """
    if ts_pro is None:
        if not TUSHARE_TOKEN:
            return False, "TuShare Token未配置"
        try:
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            ts_pro = ts.pro_api()
        except ImportError:
            return False, "TuShare未安装"
        except Exception as e:
            return False, f"TuShare初始化失败: {e}"

    ts_code = get_ts_code(code)
    end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    for attempt in range(RETRY_TIMES):
        try:
            print(f"  拉取 {code} ({ts_code})...")
            df = ts_pro.query(
                'stk_mins',
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                freq='15min'
            )

            if df is None or df.empty:
                return False, "数据为空"

            first_time = df['trade_time'].iloc[0]
            last_time = df['trade_time'].iloc[-1]
            return True, f"范围: {first_time} ~ {last_time}, {len(df)}条"

        except Exception as e:
            error_msg = str(e)
            if attempt < RETRY_TIMES - 1:
                wait_time = DELAY_ON_ERROR * (2 ** attempt)
                print(f"  ❌ {code} 失败 (尝试 {attempt+1}): {error_msg[:50]}...")
                print(f"  等待 {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                return False, error_msg[:80]

    return False, "重试次数耗尽"


def test_batch_tushare(stocks: list) -> dict:
    """TuShare批量测试"""
    print(f"\n{'='*50}")
    print(f"TuShare测试: {len(stocks)} 只股票")
    print(f"数据源: TuShare Pro API")
    print(f"{'='*50}\n")

    # 初始化TuShare
    if not TUSHARE_TOKEN:
        print("❌ TuShare Token未配置，请在.env中设置 TUSHARE_TOKEN")
        return {"success": 0, "failed": len(stocks), "failed_codes": stocks}

    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        ts_pro = ts.pro_api()
        print("✓ TuShare初始化成功")
    except Exception as e:
        print(f"❌ TuShare初始化失败: {e}")
        return {"success": 0, "failed": len(stocks), "failed_codes": stocks}

    success = 0
    failed = 0
    failed_codes = []

    start_time = time.time()

    for i, code in enumerate(stocks, 1):
        print(f"[{i}/{len(stocks)}]", end="")

        result, info = test_single_stock_tushare(code, ts_pro)

        if result:
            success += 1
            print(f"  ✓ {code} 成功，{info}")
        else:
            failed += 1
            failed_codes.append(code)
            print(f"  ❌ {code} 失败，{info}")

        # TuShare官方API，无需长延迟
        if i < len(stocks):
            time.sleep(0.5)

    elapsed = time.time() - start_time

    print(f"\n{'='*50}")
    print(f"TuShare测试结果:")
    print(f"  成功: {success}/{len(stocks)}")
    print(f"  失败: {failed}/{len(stocks)}")
    if failed_codes:
        print(f"  失败股票: {', '.join(failed_codes)}")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"{'='*50}")

    return {"success": success, "failed": failed, "failed_codes": failed_codes, "elapsed": elapsed}


# ========== AkShare 测试 ==========

def test_single_stock_akshare(code: str, use_retry: bool = False) -> tuple:
    """AkShare测试单只股票"""
    import akshare as ak

    for attempt in range(RETRY_TIMES):
        try:
            print(f"  拉取 {code}...")
            df = ak.stock_zh_a_hist_min_em(
                symbol=code,
                period=KLINE_PERIOD,
                adjust="qfq"
            )

            if df.empty:
                return False, "数据为空"

            first_time = df["时间"].iloc[0]
            last_time = df["时间"].iloc[-1]
            return True, f"范围: {first_time} ~ {last_time}, {len(df)}条"

        except Exception as e:
            error_msg = str(e)
            if use_retry and attempt < RETRY_TIMES - 1:
                wait_time = DELAY_ON_ERROR * (2 ** attempt)
                print(f"  ❌ {code} 失败 (尝试 {attempt+1}): {error_msg[:50]}...")
                print(f"  等待 {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                return False, error_msg[:80]

    return False, "重试次数耗尽"


def test_batch_akshare(stocks: list, use_delay: bool = True, use_retry: bool = True) -> dict:
    """AkShare批量测试"""
    mode_desc = "无延迟" if not use_delay else ("指数退避" if use_retry else "随机延迟")
    print(f"\n{'='*50}")
    print(f"AkShare测试: {len(stocks)} 只股票")
    print(f"数据源: 东方财富网")
    print(f"策略: {mode_desc}")
    print(f"{'='*50}\n")

    success = 0
    failed = 0
    failed_codes = []

    start_time = time.time()

    for i, code in enumerate(stocks, 1):
        print(f"[{i}/{len(stocks)}]", end="")

        result, info = test_single_stock_akshare(code, use_retry=use_retry)

        if result:
            success += 1
            print(f"  ✓ {code} 成功，{info}")
        else:
            failed += 1
            failed_codes.append(code)
            print(f"  ❌ {code} 失败，{info}")

        if use_delay and i < len(stocks):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"  等待 {delay:.1f}秒...")
            time.sleep(delay)

    elapsed = time.time() - start_time

    print(f"\n{'='*50}")
    print(f"AkShare测试结果:")
    print(f"  成功: {success}/{len(stocks)}")
    print(f"  失败: {failed}/{len(stocks)}")
    if failed_codes:
        print(f"  失败股票: {', '.join(failed_codes)}")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"{'='*50}")

    return {"success": success, "failed": failed, "failed_codes": failed_codes, "elapsed": elapsed}


# ========== BaoStock 测试 ==========

def test_single_stock_baostock(code: str, bs_logged_in: bool) -> tuple:
    """BaoStock测试单只股票"""
    import baostock as bs

    if not bs_logged_in:
        lg = bs.login()
        if lg.error_code != '0':
            return False, f"BaoStock登录失败: {lg.error_msg}"

    bs_code = get_bs_code(code)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")

    try:
        print(f"  拉取 {code} ({bs_code})...")
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,time,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start_date,
            end_date=end_date,
            frequency="15",
            adjustflag="3"
        )

        if rs.error_code != '0':
            return False, f"查询失败: {rs.error_msg}"

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return False, "数据为空"

        # 解析时间
        def parse_time(t):
            if len(t) >= 14:
                return f"{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}"
            return t

        last_time = parse_time(data_list[-1][1])
        return True, f"最后时间: {last_time}, {len(data_list)}条"

    except Exception as e:
        return False, str(e)[:80]


def test_batch_baostock(stocks: list) -> dict:
    """BaoStock批量测试"""
    print(f"\n{'='*50}")
    print(f"BaoStock测试: {len(stocks)} 只股票")
    print(f"数据源: BaoStock")
    print(f"{'='*50}\n")

    # 登录BaoStock
    import baostock as bs
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ BaoStock登录失败: {lg.error_msg}")
        return {"success": 0, "failed": len(stocks), "failed_codes": stocks}

    print("✓ BaoStock登录成功")

    success = 0
    failed = 0
    failed_codes = []
    bs_logged_in = True

    start_time = time.time()

    for i, code in enumerate(stocks, 1):
        print(f"[{i}/{len(stocks)}]", end="")

        result, info = test_single_stock_baostock(code, bs_logged_in)

        if result:
            success += 1
            print(f"  ✓ {code} 成功，{info}")
        else:
            failed += 1
            failed_codes.append(code)
            print(f"  ❌ {code} 失败，{info}")

        # BaoStock请求间隔
        if i < len(stocks):
            time.sleep(0.5)

    elapsed = time.time() - start_time

    print(f"\n{'='*50}")
    print(f"BaoStock测试结果:")
    print(f"  成功: {success}/{len(stocks)}")
    print(f"  失败: {failed}/{len(stocks)}")
    if failed_codes:
        print(f"  失败股票: {', '.join(failed_codes)}")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"{'='*50}")

    return {"success": success, "failed": failed, "failed_codes": failed_codes, "elapsed": elapsed}


# ========== 伪装浏览器测试 ==========

def patch_requests_headers():
    """替换requests请求头，伪装浏览器"""
    import requests
    OriginalSession = requests.Session

    class PatchedSession(OriginalSession):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.headers.update(FAKE_HEADERS_EM)

    requests.Session = PatchedSession
    print("✓ 已替换请求头为浏览器伪装")


def unpatch_requests_headers():
    """恢复原始requests"""
    import requests
    import importlib
    importlib.reload(requests)
    print("✓ 已恢复原始请求头")


def test_with_fake_headers():
    """伪装浏览器请求头测试"""
    print("\n🎭 伪装浏览器请求头测试（AkShare）")

    patch_requests_headers()

    import importlib
    import akshare as ak
    importlib.reload(ak)

    result = test_batch_akshare(TEST_STOCKS[:5], use_delay=True, use_retry=False)

    unpatch_requests_headers()
    return result


# ========== 主函数 ==========

def main():
    print("="*60)
    print("数据源K线拉取测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    print("\n选择测试模式:")
    print("  1. TuShare测试（官方API）")
    print("  2. BaoStock测试（需登录）")
    print("  3. AkShare快速测试（检测风控）")
    print("  4. AkShare正常测试（随机延迟+指数退避）")
    print("  5. AkShare伪装浏览器测试")
    print("  6. 全部数据源测试（按优先级）")
    print("  q. 退出")

    choice = input("\n请输入选项: ").strip().lower()

    if choice == '1':
        test_batch_tushare(TEST_STOCKS)
    elif choice == '2':
        test_batch_baostock(TEST_STOCKS)
    elif choice == '3':
        test_batch_akshare(TEST_STOCKS[:5], use_delay=False, use_retry=False)
    elif choice == '4':
        test_batch_akshare(TEST_STOCKS, use_delay=True, use_retry=True)
    elif choice == '5':
        test_with_fake_headers()
    elif choice == '6':
        # 按优先级测试：TuShare > BaoStock > AkShare
        print("\n按数据源优先级测试...")

        # TuShare
        ts_result = test_batch_tushare(TEST_STOCKS[:5])
        if ts_result["success"] >= 3:
            print("\n✅ TuShare正常，跳过其他数据源测试")
            return

        # BaoStock
        print("\n⚠️ TuShare异常，测试BaoStock...")
        bs_result = test_batch_baostock(TEST_STOCKS[:5])
        if bs_result["success"] >= 3:
            print("\n✅ BaoStock正常")
            return

        # AkShare
        print("\n⚠️ BaoStock异常，测试AkShare...")
        test_batch_akshare(TEST_STOCKS[:5], use_delay=True, use_retry=True)

    elif choice == 'q':
        print("退出测试")
        return
    else:
        print("无效选项，执行AkShare快速测试")
        test_batch_akshare(TEST_STOCKS[:5], use_delay=False, use_retry=False)


if __name__ == "__main__":
    main()