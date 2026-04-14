"""
AkShare K线拉取测试脚本

测试IP风控是否解除，验证请求是否正常
"""
import time
import random
from datetime import datetime

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

# 伪装浏览器请求头
FAKE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://quote.eastmoney.com/",
}


def test_single_stock(code: str, use_retry: bool = False) -> tuple:
    """
    测试单只股票

    Returns:
        (success: bool, data_info: str)
    """
    import akshare as ak

    for attempt in range(RETRY_TIMES):
        try:
            print(f"  拉取 {code}...")
            df = ak.stock_zh_a_hist_min_em(
                symbol=code,
                period="15",
                adjust="qfq"
            )

            if df.empty:
                return False, "数据为空"

            # 显示数据时间范围
            first_time = df["时间"].iloc[0] if "时间" in df.columns else df.iloc[0, 0]
            last_time = df["时间"].iloc[-1] if "时间" in df.columns else df.iloc[-1, 0]
            return True, f"范围: {first_time} ~ {last_time}, {len(df)}条"

        except Exception as e:
            error_msg = str(e)
            if use_retry and attempt < RETRY_TIMES - 1:
                # 指数退避：5s, 10s, 20s
                wait_time = DELAY_ON_ERROR * (2 ** attempt)
                print(f"  ❌ {code} 失败 (尝试 {attempt+1}): {error_msg[:50]}...")
                print(f"  等待 {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                return False, error_msg[:80]

    return False, "重试次数耗尽"


def patch_requests_headers():
    """
    替换requests请求头，伪装浏览器

    通过monkey patch修改requests.Session的默认headers
    """
    import requests

    # 创建原始Session类
    OriginalSession = requests.Session

    # 创建带伪装headers的Session类
    class PatchedSession(OriginalSession):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # 设置伪装请求头
            self.headers.update(FAKE_HEADERS)

    # 替换requests.Session
    requests.Session = PatchedSession
    print("✓ 已替换请求头为浏览器伪装")
    print(f"  User-Agent: {FAKE_HEADERS['User-Agent'][:50]}...")

    return requests


def unpatch_requests_headers():
    """
    恢复原始requests
    """
    import requests
    import importlib
    importlib.reload(requests)
    print("✓ 已恢复原始请求头")


def test_batch(stocks: list, use_delay: bool = True, use_retry: bool = False) -> dict:
    """
    批量测试

    Args:
        stocks: 股票列表
        use_delay: 是否使用随机延迟
        use_retry: 是否使用指数退避重试
    """
    mode_desc = "无延迟" if not use_delay else ("指数退避" if use_retry else "随机延迟")
    print(f"\n{'='*50}")
    print(f"批量测试: {len(stocks)} 只股票")
    print(f"策略: {mode_desc}")
    print(f"{'='*50}\n")

    success = 0
    failed = 0
    failed_codes = []

    start_time = time.time()

    for i, code in enumerate(stocks, 1):
        print(f"[{i}/{len(stocks)}]", end="")

        result, info = test_single_stock(code, use_retry=use_retry)

        if result:
            success += 1
            print(f"  ✓ {code} 成功，{info}")
        else:
            failed += 1
            failed_codes.append(code)
            print(f"  ❌ {code} 失败，{info}")

        # 延迟
        if use_delay and i < len(stocks):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"  等待 {delay:.1f}秒...")
            time.sleep(delay)

    elapsed = time.time() - start_time

    # 统计
    print(f"\n{'='*50}")
    print(f"测试结果:")
    print(f"  成功: {success}/{len(stocks)}")
    print(f"  失败: {failed}/{len(stocks)}")
    if failed_codes:
        print(f"  失败股票: {', '.join(failed_codes)}")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"  平均: {elapsed/len(stocks):.1f}秒/只")
    print(f"{'='*50}")

    return {
        "success": success,
        "failed": failed,
        "failed_codes": failed_codes,
        "elapsed": elapsed
    }


def test_fast_mode():
    """快速测试（无延迟）- 检测是否被风控"""
    print("\n⚡ 快速模式测试（检测风控状态）")
    return test_batch(TEST_STOCKS[:5], use_delay=False, use_retry=False)


def test_normal_mode():
    """正常模式测试（与主程序一致：随机延迟 + 指数退避）"""
    print("\n🐢 正常模式测试（随机延迟 + 指数退避）")
    return test_batch(TEST_STOCKS, use_delay=True, use_retry=True)


def test_with_fake_headers():
    """伪装浏览器请求头测试"""
    print("\n🎭 伪装浏览器请求头测试")

    # 先patch requests
    patch_requests_headers()

    # 重新导入akshare（使其使用新的requests）
    import importlib
    import akshare as ak
    importlib.reload(ak)

    # 测试
    result = test_batch(TEST_STOCKS[:5], use_delay=True, use_retry=False)

    # 恢复原始requests
    unpatch_requests_headers()

    return result


def main():
    print("="*60)
    print("AkShare 15分钟K线拉取测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    print("\n选择测试模式:")
    print("  1. 快速测试（无延迟，检测风控）")
    print("  2. 正常测试（随机延迟 + 指数退避）")
    print("  3. 伪装浏览器测试（替换请求头）")
    print("  4. 全部测试")
    print("  q. 退出")

    choice = input("\n请输入选项: ").strip().lower()

    if choice == '1':
        test_fast_mode()
    elif choice == '2':
        test_normal_mode()
    elif choice == '3':
        test_with_fake_headers()
    elif choice == '4':
        # 先快速测试检测风控
        fast_result = test_fast_mode()

        if fast_result["success"] >= 3:
            print("\n✅ 快速测试通过，继续其他测试...")
            test_normal_mode()
        else:
            print("\n⚠️ 快速测试失败较多，尝试伪装浏览器...")
            test_with_fake_headers()
    elif choice == 'q':
        print("退出测试")
        return
    else:
        print("无效选项，执行快速测试")
        test_fast_mode()


if __name__ == "__main__":
    main()