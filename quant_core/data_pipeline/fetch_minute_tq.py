import os
import sys
from datetime import datetime

# 获取当前项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 尝试导入 tqsdk
try:
    from tqsdk import TqApi, TqAuth
    from tqsdk.tools import DataDownloader
except ImportError:
    print("[ERROR] 未检测到 tqsdk 库。请先在终端运行: pip install tqsdk")
    sys.exit(1)

# ==============================================================================
# 天勤量化 (TqSdk) 期货主力连续合约代码映射
# 天勤的商品期货主力连续合约格式为：KQ.m@交易所代码.品种小写代码
# 交易所代码包括：SHFE (上期所), CZCE (郑商所), DCE (大商所), CFFEX (中金所), INE (能源中心)
# ==============================================================================
TQ_FUTURES_MAP = {
    "KQ.m@CZCE.SR":  "白糖主连",
    "KQ.m@SHFE.rb":  "螺纹主连",
    "KQ.m@DCE.i":    "铁矿主连",
    "KQ.m@CZCE.ma":  "甲醇主连",
    "KQ.m@CZCE.ta":  "PTA主连",
    "KQ.m@SHFE.ru":  "橡胶主连",
    "KQ.m@SHFE.au":  "黄金主连",
    "KQ.m@SHFE.ag":  "白银主连",
    "KQ.m@SHFE.cu":  "沪铜主连",
    "KQ.m@DCE.m":    "豆粕主连",
    "KQ.m@DCE.y":    "豆油主连",
    "KQ.m@DCE.p":    "棕榈主连",
    "KQ.m@DCE.jd":   "鸡蛋主连"
}

def download_minute_data(username: str, password: str, symbol: str, duration_seconds: int = 60, start_date: str = "2023-01-01 09:00:00"):
    """
    通过天勤量化 (TqSdk) 下载高频分钟线历史数据并保存为 CSV
    
    :param username: 天勤量化官网注册的账号（手机号）
    :param password: 天勤量化账号密码
    :param symbol: 天勤合约代码，如 "KQ.m@SHFE.rb" 或 "KQ.m@CZCE.SR"
    :param duration_seconds: K线周期（秒），60 表示 1分钟线，300 表示 5分钟线，900 表示 15分钟线
    :param start_date: 下载的起始时间，格式 YYYY-MM-DD HH:MM:SS
    """
    # 自动识别周期名称用于文件命名
    period_names = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h"}
    period_str = period_names.get(duration_seconds, f"{duration_seconds}s")
    
    # 提取品种的小写简称用于文件名，例如 "KQ.m@SHFE.rb" 提取出 "rb"
    if "KQ.m@" in symbol:
        try:
            symbol_name = symbol.split("@")[1].split(".")[1]
        except Exception:
            symbol_name = symbol.replace("@", "_").replace(".", "_")
    else:
        try:
            symbol_name = symbol.split(".")[1]
        except Exception:
            symbol_name = symbol
            
    contract_show_name = TQ_FUTURES_MAP.get(symbol, symbol)
    file_name = f"future_{symbol_name}_{period_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)
    
    print(f"\n[DATA] 准备下载 {contract_show_name} ({symbol}) 的 {period_str} 历史数据...")
    print(f"[DATA] 起始时间: {start_date} | 保存目标: {file_path}")
    
    try:
        # 1. 验证天勤账户并初始化 API 实例
        api = TqApi(auth=TqAuth(username, password))
        
        # 2. 将输入的起始时间转换为 datetime 类型
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        
        # 3. 获取交易所合约信息
        contract = api.get_quote(symbol)
        
        # 4. 创建天勤的高效数据下载器 (DataDownloader)
        downloader = DataDownloader(
            api=api,
            symbol_list=[symbol],
            dur_sec=duration_seconds,
            start_dt=start_dt,
            end_dt=datetime.now(),
            csv_file_name=file_path
        )
        
        print("[DOWNLOADING] 下载已启动，正在从天勤数据中心抓取，请稍候...")
        
        # 5. 循环监控下载进度
        while not downloader.is_finished():
            # 驱动 API 运转，获取最新进度
            api.wait_update()
            # 实时输出进度百分比
            print(f"\r⌛ 正在下载: [{downloader.get_progress():.2%}]", end="", flush=True)
            
        print(f"\n[SUCCESS] {contract_show_name} {period_str} 历史数据下载成功并已保存！")
        
        # 6. 关闭 API 连接，释放资源
        api.close()
        
    except Exception as e:
        print(f"\n[ERROR] 数据下载失败: {e}")
        print("[TIP] 请检查您的天勤用户名、密码是否正确，或者网络是否通畅。")

if __name__ == "__main__":
    print(">>> AlphaQuant 高频分钟线下载器 (基于 TqSdk) <<<")
    
    # ==============================================================================
    # ⚠️ 说明：天勤量化 (TqSdk) 获取分钟级及 Tick 级历史数据需要天勤账号授权。
    # 1. 请前往天勤量化官网 (https://www.shinnytech.com/tqsdk/) 注册一个免费开发者账号。
    # 2. 将您的账号（手机号）和密码填入下方。
    # ==============================================================================
    TQ_USER = "YOUR_PHONE_NUMBER"  # 请替换为您的天勤注册手机号
    TQ_PASS = "YOUR_PASSWORD"      # 请替换为您的天勤密码
    
    if TQ_USER == "YOUR_PHONE_NUMBER" or TQ_PASS == "YOUR_PASSWORD":
        print("\n[WARNING] 您尚未配置天勤量化的账号和密码！")
        print("请在脚本中填写您的账号（手机号）与密码后，再运行此分钟线下载器。")
        print("天勤账号注册地址: https://www.shinnytech.com/tqsdk/ (完全免费)")
    else:
        # 默认示例：下载 螺纹钢主力连续合约 (KQ.m@SHFE.rb) 2024年以来的 5分钟 (period=300) 数据
        download_minute_data(
            username=TQ_USER,
            password=TQ_PASS,
            symbol="KQ.m@SHFE.rb",
            duration_seconds=300,  # 300 秒 = 5 分钟
            start_date="2024-01-01 09:00:00"
        )
