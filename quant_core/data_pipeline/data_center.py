import os
import time
import pandas as pd
import akshare as ak
from datetime import datetime

# 获取当前项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ==============================================================================
# 1. 国内期货市场全家桶品种映射库（共 55 个核心最活跃主力连续合约）
# 命名格式兼容新浪财经：品种大写英文/拼音缩写 + 0 (代表主力连续合约)
# ==============================================================================
FUTURES_MARKET_MAP = {
    # --- 上海期货交易所 (SHFE) ---
    "RB0":  "螺纹钢主力",
    "HC0":  "热卷主力",
    "RU0":  "天然橡胶主力",
    "FU0":  "燃料油主力",
    "BU0":  "石油沥青主力",
    "AU0":  "黄金主力",
    "AG0":  "白银主力",
    "CU0":  "沪铜主力",
    "AL0":  "沪铝主力",
    "ZN0":  "沪锌主力",
    "PB0":  "沪铅主力",
    "NI0":  "沪镍主力",
    "SN0":  "沪锡主力",
    "SP0":  "纸浆主力",
    "SS0":  "不锈钢主力",
    "AO0":  "氧化铝主力",

    # --- 大连商品交易所 (DCE) ---
    "M0":   "豆粕主力",
    "Y0":   "豆油主力",
    "P0":   "棕榈油主力",
    "C0":   "玉米主力",
    "CS0":  "玉米淀粉主力",
    "JD0":  "鸡蛋主力",
    "I0":   "铁矿石主力",
    "J0":   "焦炭主力",
    "JM0":  "焦煤主力",
    "L0":   "聚乙烯(塑料)主力",
    "V0":   "聚氯乙烯(PVC)主力",
    "PP0":  "聚丙烯主力",
    "EB0":  "苯乙烯主力",
    "EG0":  "乙二醇主力",
    "PG0":  "液化石油气主力",
    "LH0":  "生猪主力",
    "A0":   "黄大豆1号主力",
    "B0":   "黄大豆2号主力",

    # --- 郑州商品交易所 (CZCE) ---
    "SR0":  "白糖主力",
    "CF0":  "棉花主力",
    "TA0":  "PTA主力",
    "MA0":  "甲醇主力",
    "FG0":  "玻璃主力",
    "SA0":  "纯碱主力",
    "SF0":  "硅铁主力",
    "SM0":  "锰硅主力",
    "AP0":  "苹果主力",
    "CJ0":  "红枣主力",
    "UR0":  "尿素主力",
    "OI0":  "菜油主力",
    "RM0":  "菜粕主力",
    "PF0":  "短纤主力",

    # --- 中国金融期货交易所 (CFFEX) ---
    "IF0":  "沪深300股指主力",
    "IH0":  "上证50股指主力",
    "IC0":  "中证500股指主力",
    "IM0":  "中证1000股指主力",

    # --- 上海国际能源交易中心 (INE) & 广州期货交易所 (GFEX) ---
    "SC0":  "原油主力",
    "SI0":  "工业硅主力",
    "LC0":  "碳酸锂主力"
}

# 用于增量高频分钟线下载的 13 个最核心、最具日内波动和流动性的品种
ACTIVE_MINUTES_LIST = [
    "RB0", "SR0", "I0", "MA0", "TA0", "RU0", "AU0", "AG0", "CU0", "M0", "Y0", "P0", "JD0"
]

# ==============================================================================
# 2. 核心抓取与增量缝合追加引擎
# ==============================================================================

def fetch_daily_data(symbol: str, start_date: str = "20000101") -> pd.DataFrame:
    """
    抓取国内期货主力合约历史日线行情数据（支持追溯至 2000 年）
    """
    name = FUTURES_MARKET_MAP.get(symbol, symbol)
    today_str = datetime.today().strftime("%Y%m%d")
    file_path = os.path.join(DATA_DIR, f"future_{symbol.lower().replace('0', '')}_daily.csv")
    
    print(f"[DAILY] 正在下载 {name} ({symbol}) 自 {start_date} 至今的历史日线...")
    
    try:
        df = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=today_str)
        
        if df.empty:
            print(f"[WARNING] 未获取到 {symbol} 的日线数据。")
            return pd.DataFrame()
            
        df = df.rename(columns={
            "日期": "date",
            "开盘价": "open",
            "最高价": "high",
            "最低价": "low",
            "收盘价": "close",
            "成交量": "volume",
            "持仓量": "open_interest",
            "动态结算价": "settlement"
        })
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        # 导出 CSV
        df.to_csv(file_path, index=False)
        print(f"[SUCCESS] {name} 日线数据保存成功，共 {len(df)} 行记录 -> {file_path}")
        return df
        
    except Exception as e:
        print(f"[ERROR] 下载 {symbol} 日线数据失败: {e}")
        return pd.DataFrame()

def fetch_minute_incremental(symbol: str, period: str = "5") -> pd.DataFrame:
    """
    通过高灵敏增量去重缝合引擎，获取最新的 1023 条分钟 K 线并追加到本地 CSV 尾部
    
    :param symbol: 期货代码，如 "RB0"
    :param period: 周期（分钟），"1", "5", "15", "30", "60"
    """
    name = FUTURES_MARKET_MAP.get(symbol, symbol)
    period_str = f"{period}m"
    file_name = f"future_{symbol.lower().replace('0', '')}_{period_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)
    
    try:
        # 1. 抓取云端最新的 1023 条数据
        df_new = ak.futures_zh_minute_sina(symbol=symbol, period=period)
        if df_new.empty:
            print(f"[WARNING] 从云端未获取到 {symbol} 的 {period_str} 数据。")
            return pd.DataFrame()
            
        df_new = df_new.rename(columns={
            "datetime": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "hold": "open_interest"
        })
        df_new["date"] = pd.to_datetime(df_new["date"])
        df_new = df_new.sort_values("date").reset_index(drop=True)
        
        # 2. 判断本地是否存在历史数据
        if os.path.exists(file_path):
            # 读取本地数据，检测最新时间戳
            df_local = pd.read_csv(file_path)
            if not df_local.empty:
                df_local["date"] = pd.to_datetime(df_local["date"])
                last_timestamp = df_local["date"].max()
                
                # 过滤出比本地最新时间戳还要新的新数据（增量缝合核心）
                df_incremental = df_new[df_new["date"] > last_timestamp]
                
                if not df_incremental.empty:
                    # 追加方式写入本地文件，不写 Header
                    df_incremental.to_csv(file_path, mode='a', header=False, index=False)
                    print(f"[INCREMENTAL] {name} {period_str} 缝合成功！追加 {len(df_incremental)} 行新记录 -> {file_path}")
                else:
                    print(f"[SKIP] {name} {period_str} 无更新数据，本地已是最新。")
            else:
                # 本地文件为空，则直接覆盖
                df_new.to_csv(file_path, index=False)
                print(f"[SUCCESS] {name} {period_str} 初次建仓完成，共 {len(df_new)} 行记录 -> {file_path}")
        else:
            # 本地文件不存在，初次建仓
            df_new.to_csv(file_path, index=False)
            print(f"[SUCCESS] {name} {period_str} 初次建仓完成，共 {len(df_new)} 行记录 -> {file_path}")
            
        return df_new
        
    except Exception as e:
        print(f"[ERROR] 增量抓取 {symbol} {period_str} 数据失败: {e}")
        return pd.DataFrame()

# ==============================================================================
# 3. 本地高精度重采样长周期合成引擎
# ==============================================================================

def synthesize_long_periods(symbol: str):
    """
    基于本地已下载的 Daily 日线数据，通过 Pandas 高精度重采样（Resample）合成周线、月线与年线
    """
    name = FUTURES_MARKET_MAP.get(symbol, symbol)
    clean_symbol = symbol.lower().replace('0', '')
    daily_file = os.path.join(DATA_DIR, f"future_{clean_symbol}_daily.csv")
    
    if not os.path.exists(daily_file):
        print(f"[SYNTHESIZE] [SKIP] {name} 未在本地找到日线数据文件，请先下载日线。")
        return
        
    try:
        # 读取日线
        df = pd.read_csv(daily_file)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df.set_index("date", inplace=True)
        
        # 精准聚合规则，确保符合专业量化系统规范
        agg_rules = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "open_interest": "last" if "open_interest" in df.columns else "ignore",
            "settlement": "last" if "settlement" in df.columns else "ignore"
        }
        # 清除不存在的键
        agg_rules = {k: v for k, v in agg_rules.items() if v != "ignore" and k in df.columns}
        
        # 1. 合成周线 (Weekly - 'W')
        df_weekly = df.resample('W').agg(agg_rules).dropna(subset=["open"])
        df_weekly.reset_index().to_csv(os.path.join(DATA_DIR, f"future_{clean_symbol}_weekly.csv"), index=False)
        
        # 2. 合成月线 (Monthly - Pandas 2.0+ 推荐使用 'ME' 替代 'M' 表示 Month End)
        df_monthly = df.resample('ME').agg(agg_rules).dropna(subset=["open"])
        df_monthly.reset_index().to_csv(os.path.join(DATA_DIR, f"future_{clean_symbol}_monthly.csv"), index=False)
        
        # 3. 合成年线 (Yearly - Pandas 2.0+ 推荐使用 'YE' 替代 'Y' 表示 Year End)
        df_yearly = df.resample('YE').agg(agg_rules).dropna(subset=["open"])
        df_yearly.reset_index().to_csv(os.path.join(DATA_DIR, f"future_{clean_symbol}_yearly.csv"), index=False)
        
        print(f"[SYNTHESIZE] {name} 周期合成成功！周线: {len(df_weekly)}行 | 月线: {len(df_monthly)}行 | 年线: {len(df_yearly)}行")
        
    except Exception as e:
        print(f"[ERROR] 合成 {symbol} 长周期数据失败: {e}")

# ==============================================================================
# 4. 全市场一键运行数据中心
# ==============================================================================

def run_data_center(download_daily: bool = True, download_minute: bool = True, synthesize: bool = True):
    """
    一键运行数据中心，执行多周期“大建仓”任务
    """
    print("\n==============================================================")
    print("--- AlphaQuant 中央行情数据管理中心启动 ---")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"核心保存目录: {DATA_DIR}")
    print("==============================================================")
    
    # 步骤 1: 抓取 55 个主力合约的超长历史日线 (自 2000年1月1日)
    if download_daily:
        print("\n--- 步骤 1: 抓取 55 个核心主力合约的 2000 至今长历史日线 ---")
        total_daily = len(FUTURES_MARKET_MAP)
        for idx, symbol in enumerate(FUTURES_MARKET_MAP.keys(), 1):
            print(f"\n({idx}/{total_daily}) 品种处理中...")
            fetch_daily_data(symbol=symbol, start_date="20000101")
            # 延时 0.3 秒，安全防封 IP
            time.sleep(0.3)
            
    # 步骤 2: 基于本地 Daily 日线数据高精度合成周/月/年线
    if synthesize:
        print("\n--- 步骤 2: 高精度本地合成全市场周线、月线与年线 ---")
        for idx, symbol in enumerate(FUTURES_MARKET_MAP.keys(), 1):
            synthesize_long_periods(symbol=symbol)
            
    # 步骤 3: 批量获取 13 个最活跃主力合约的所有分钟线周期（1m, 5m, 15m, 30m, 60m）
    if download_minute:
        print("\n--- 步骤 3: 抓取/增量缝合最活跃品种的 5 大维度分钟线 (1m, 5m, 15m, 30m, 60m) ---")
        total_active = len(ACTIVE_MINUTES_LIST)
        periods = ["1", "5", "15", "30", "60"]
        
        for idx, symbol in enumerate(ACTIVE_MINUTES_LIST, 1):
            name = FUTURES_MARKET_MAP.get(symbol, symbol)
            print(f"\n({idx}/{total_active}) 批量同步高频分钟线: {name} ({symbol})")
            
            for p in periods:
                fetch_minute_incremental(symbol=symbol, period=p)
                # 延时 0.3 秒保护
                time.sleep(0.3)
                
    print("\n==============================================================")
    print("--- AlphaQuant 行情数据中心本次建仓任务全部圆满结束！ ---")
    print("==============================================================")

if __name__ == "__main__":
    # 一键启动数据中心（日线拉取 + 分钟线增量缝合 + 本地长周期高精度合成）
    run_data_center(download_daily=True, download_minute=True, synthesize=True)
