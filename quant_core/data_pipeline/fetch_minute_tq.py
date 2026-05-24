import os
import time
import pandas as pd
import akshare as ak

# 获取当前项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ==============================================================================
# 国内期货最活跃、最核心的品种列表（新浪财经主力连续合约代码）
# ==============================================================================
FUTURES_MARKET_MAP = {
    "SR0":  "白糖主力",
    "RB0":  "螺纹主力",
    "I0":   "铁矿主力",
    "MA0":  "甲醇主力",
    "TA0":  "PTA主力",
    "RU0":  "橡胶主力",
    "AU0":  "黄金主力",
    "AG0":  "白银主力",
    "CU0":  "沪铜主力",
    "M0":   "豆粕主力",
    "Y0":   "豆油主力",
    "P0":   "棕榈主力",
    "JD0":  "鸡蛋主力"
}

def download_minute_data_free(symbol: str, period: str = "5"):
    """
    通过 AkShare 免费接口获取国内期货主力合约的高频分钟线数据并保存为 CSV
    (该接口完全免登录、免账号、无付费限制)
    
    :param symbol: 期货主力连续合约代码，如 "RB0", "SR0"
    :param period: 数据周期（分钟），可选值为 "1", "5", "15", "30", "60"
    """
    contract_show_name = FUTURES_MARKET_MAP.get(symbol, symbol)
    period_str = f"{period}m"
    file_name = f"future_{symbol.lower().replace('0', '')}_{period_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)
    
    print(f"\n[DATA] 正在通过 AkShare 免费通道下载 {contract_show_name} ({symbol}) 的 {period_str} 行情数据...")
    
    try:
        # 调用新浪财经的公开高频分时接口 (免账号密码，完全免费)
        df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
        
        if df.empty:
            print(f"[WARNING] 未获取到 {symbol} 的分钟线数据。")
            return pd.DataFrame()
            
        # 重命名列名，使其与我们日线系统字段保持一致
        df = df.rename(columns={
            "datetime": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "hold": "open_interest"
        })
        
        # 确保时间列格式化正确并排序
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        # 保存为 CSV
        df.to_csv(file_path, index=False)
        print(f"[SUCCESS] {contract_show_name} {period_str} 历史数据抓取成功！")
        print(f"[SUCCESS] 保存路径: {file_path} (共 {len(df)} 行最新记录)")
        return df
        
    except Exception as e:
        print(f"[ERROR] 抓取 {symbol} 分钟线数据失败: {e}")
        return pd.DataFrame()

def download_all_active_futures_minute(period: str = "5"):
    """
    一键获取所有主流活跃期货品种的分钟K线数据
    """
    total = len(FUTURES_MARKET_MAP)
    success_count = 0
    fail_count = 0
    
    print("\n==============================================================")
    print(f"--- 开始执行全市场期货主力分钟线 ({period}分钟) 批量下载，共计 {total} 个品种 ---")
    print("==============================================================")
    
    start_time = time.time()
    
    for idx, (symbol, name) in enumerate(FUTURES_MARKET_MAP.items(), 1):
        print(f"\n[{idx}/{total}] 正在下载: {symbol} - {name}")
        df = download_minute_data_free(symbol=symbol, period=period)
        
        if not df.empty:
            success_count += 1
        else:
            fail_count += 1
            
        # 合理延时 0.5 秒，保护公共 API 的同时提高下载速度
        time.sleep(0.5)
        
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n==============================================================")
    print("--- 高频分钟线批量下载任务执行完毕！ ---")
    print(f"    成功: {success_count} 个品种")
    print(f"    失败: {fail_count} 个品种")
    print(f"    总耗时: {duration:.2f} 秒")
    print("==============================================================")

if __name__ == "__main__":
    print(">>> AlphaQuant 免费版高频分钟线抓取器 (免登录·无限制版) <<<")
    print("[INFO] 天勤量化免费版对历史高频下载实施了商业限制。")
    print("[INFO] 系统已自动帮您无缝升级为基于 AkShare 的完全免费开源行情引擎！")
    print("[INFO] 无需任何账号和密码，即可一键下载全市场分钟线数据。")
    
    # 默认执行：下载所有国内主流活跃期货主力合约最新的 5分钟 K 线数据
    download_all_active_futures_minute(period="5")
