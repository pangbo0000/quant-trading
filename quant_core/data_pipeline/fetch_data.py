import os
import time
import pandas as pd
import akshare as ak
from datetime import datetime

# 获取当前项目根目录下的 data 文件夹路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 确保 data 目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# ==============================================================================
# 国内期货最活跃、最核心的品种列表（新浪财经主力连续合约代码）
# 新浪财经的命名规则通常是：品种大写英文/拼音缩写 + 0
# ==============================================================================
FUTURES_MARKET_MAP = {
    # 1. 贵金属 & 有色金属
    "AU0": "黄金主力",
    "AG0": "白银主力",
    "CU0": "沪铜主力",
    "AL0": "沪铝主力",
    "ZN0": "沪锌主力",
    "PB0": "沪铅主力",
    "NI0": "沪镍主力",
    "SN0": "沪锡主力",
    
    # 2. 黑色金属 & 建材
    "RB0": "螺纹钢主力",
    "HC0": "热卷主力",
    "I0":  "铁矿石主力",
    "J0":  "焦炭主力",
    "JM0": "焦煤主力",
    "FG0": "玻璃主力",
    "SA0": "纯碱主力",
    
    # 3. 能源化工
    "SC0":  "原油主力",
    "RU0":  "橡胶主力",
    "BU0":  "沥青主力",
    "MA0":  "甲醇主力",
    "TA0":  "PTA主力",
    "EG0":  "乙二醇主力",
    "PP0":  "聚丙烯主力",
    "L0":   "塑料主力",
    "PVC0": "PVC主力",
    "EB0":  "苯乙烯主力",
    "FU0":  "燃料油主力",
    "SP0":  "纸浆主力",
    
    # 4. 农产品
    "M0":   "豆粕主力",
    "Y0":   "豆油主力",
    "P0":   "棕榈油主力",
    "OI0":  "菜油主力",
    "RM0":  "菜粕主力",
    "C0":   "玉米主力",
    "CS0":  "淀粉主力",
    "JD0":  "鸡蛋主力",
    "LH0":  "生猪主力",
    "AP0":  "苹果主力",
    "CF0":  "棉花主力",
    "SR0":  "白糖主力",
    "CJ0":  "红枣主力",
    
    # 5. 金融期货（股指期货）
    "IF0":  "沪深300股指主力",
    "IH0":  "上证50股指主力",
    "IC0":  "中证500股指主力",
    "IM0":  "中证1000股指主力"
}

def fetch_stock_daily(symbol: str, start_date: str = "20200101", end_date: str = None) -> pd.DataFrame:
    """
    获取国内 A 股历史日线行情数据
    """
    if not end_date:
        end_date = datetime.today().strftime("%Y%m%d")
        
    print(f"[DATA] 正在从 AkShare 获取 A股股票 {symbol} 的日线数据 ({start_date} -> {end_date})...")
    
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol, 
            period="daily", 
            start_date=start_date, 
            end_date=end_date, 
            adjust="qfq"
        )
        
        if df.empty:
            print(f"[WARNING] 未获取到股票 {symbol} 的数据。")
            return pd.DataFrame()
            
        column_mapping = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_change",
            "涨跌额": "change_amount",
            "换手率": "turnover"
        }
        df = df.rename(columns=column_mapping)
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        file_path = os.path.join(DATA_DIR, f"stock_{symbol}_daily.csv")
        df.to_csv(file_path, index=False)
        print(f"[SUCCESS] 数据成功保存至: {file_path} (共 {len(df)} 行记录)")
        return df
        
    except Exception as e:
        print(f"[ERROR] 获取股票 {symbol} 数据失败: {e}")
        return pd.DataFrame()

def fetch_future_daily(symbol: str, start_date: str = "20200101", end_date: str = None) -> pd.DataFrame:
    """
    获取国内期货主力合约历史日线行情数据
    
    :param symbol: 期货主力合约代码，如 "SR0" (白糖主力)
    :param start_date: 开始日期，格式 YYYYMMDD
    :param end_date: 结束日期，格式 YYYYMMDD，默认为今天
    :return: Pandas DataFrame 行情数据
    """
    if not end_date:
        end_date = datetime.today().strftime("%Y%m%d")
        
    contract_name = FUTURES_MARKET_MAP.get(symbol, "未知主力合约")
    print(f"[DATA] 正在获取期货主力合约 {symbol} ({contract_name}) 的历史日线数据...")
    
    try:
        # 获取新浪财经的期货主力合约历史数据
        df = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=end_date)
        
        if df.empty:
            print(f"[WARNING] 未获取到期货主力合约 {symbol} 的数据。")
            return pd.DataFrame()
            
        # 格式化日期和重命名
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
        
        # 保存为本地 CSV 文件
        file_path = os.path.join(DATA_DIR, f"future_{symbol}_daily.csv")
        df.to_csv(file_path, index=False)
        print(f"[SUCCESS] 数据成功保存至: {file_path} (共 {len(df)} 行记录)")
        return df
        
    except Exception as e:
        print(f"[ERROR] 获取期货主力合约 {symbol} 数据失败: {e}")
        return pd.DataFrame()

def fetch_all_futures(start_date: str = "20200101"):
    """
    批量获取并下载所有国内主流期货主力合约的历史数据
    """
    total = len(FUTURES_MARKET_MAP)
    success_count = 0
    fail_count = 0
    
    print("\n==============================================================")
    print(f"📦 开始执行全市场期货主力合约下载，共计 {total} 个品种")
    print("==============================================================")
    
    start_time = time.time()
    
    for idx, (symbol, name) in enumerate(FUTURES_MARKET_MAP.items(), 1):
        print(f"\n[{idx}/{total}] 正在抓取: {symbol} - {name}")
        
        df = fetch_future_daily(symbol=symbol, start_date=start_date)
        
        if not df.empty:
            success_count += 1
        else:
            fail_count += 1
            
        # 每次请求后合理延时 1 秒，防止请求频率过密被服务器封禁 IP
        time.sleep(1.0)
        
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n==============================================================")
    print("🏁 下载任务执行完毕！")
    print(f"📊 成功: {success_count} 个品种")
    print(f"❌ 失败: {fail_count} 个品种")
    print(f"⏱️ 总耗时: {duration:.2f} 秒")
    print("==============================================================")

if __name__ == "__main__":
    print(">>> AlphaQuant 历史行情数据下载器启动...")
    
    # 默认执行：下载所有国内主流期货品种主力合约的历史日线数据（从 2020 年 1 月 1 日至今）
    fetch_all_futures(start_date="20200101")
