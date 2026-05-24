import os
import pandas as pd
import akshare as ak
from datetime import datetime

# 获取当前项目根目录下的 data 文件夹路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 确保 data 目录存在
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_stock_daily(symbol: str, start_date: str = "20200101", end_date: str = None) -> pd.DataFrame:
    """
    获取国内 A 股历史日线行情数据
    
    :param symbol: 股票代码，如 "000001" (平安银行), "600519" (贵州茅台)
    :param start_date: 开始日期，格式 YYYYMMDD
    :param end_date: 结束日期，格式 YYYYMMDD，默认为今天
    :return: Pandas DataFrame 行情数据
    """
    if not end_date:
        end_date = datetime.today().strftime("%Y%m%dd")
        
    print(f"📡 正在从 AkShare 获取 A股股票 {symbol} 的日线数据 ({start_date} -> {end_date})...")
    
    try:
        # adjust="qfq" 表示前复权，这是量化回测必须的，消除了除权除息带来的价格跳空
        df = ak.stock_zh_a_hist(
            symbol=symbol, 
            period="daily", 
            start_date=start_date, 
            end_date=end_date, 
            adjust="qfq"
        )
        
        if df.empty:
            print(f"⚠️ 未获取到股票 {symbol} 的数据。")
            return pd.DataFrame()
            
        # 重命名列名，使其更符合量化系统的通用英文命名习惯
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
        
        # 将日期设为索引并排序
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        # 保存为本地 CSV 文件
        file_path = os.path.join(DATA_DIR, f"stock_{symbol}_daily.csv")
        df.to_csv(file_path, index=False)
        print(f"✅ 数据成功保存至: {file_path} (共 {len(df)} 行记录)")
        return df
        
    except Exception as e:
        print(f"❌ 获取股票 {symbol} 数据失败: {e}")
        return pd.DataFrame()

def fetch_future_daily(symbol: str, start_date: str = "20200101", end_date: str = None) -> pd.DataFrame:
    """
    获取国内期货主力合约历史日线行情数据
    
    :param symbol: 期货主力合约代码，如 "SR0" (白糖主力), "RU0" (天然橡胶主力), "M0" (豆粕主力)
    :param start_date: 开始日期，格式 YYYYMMDD
    :param end_date: 结束日期，格式 YYYYMMDD，默认为今天
    :return: Pandas DataFrame 行情数据
    """
    if not end_date:
        end_date = datetime.today().strftime("%Y%m%dd")
        
    print(f"📡 正在获取期货主力合约 {symbol} 的日线数据...")
    
    try:
        # 获取新浪财经的期货主力合约历史数据
        df = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=end_date)
        
        if df.empty:
            print(f"⚠️ 未获取到期货主力合约 {symbol} 的数据。")
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
        print(f"✅ 数据成功保存至: {file_path} (共 {len(df)} 行记录)")
        return df
        
    except Exception as e:
        print(f"❌ 获取期货主力合约 {symbol} 数据失败: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    print("🚀 AlphaQuant 历史行情数据下载器启动...")
    
    # 示例 1: 下载股票“平安银行”(000001) 的日线历史数据
    fetch_stock_daily(symbol="000001", start_date="20230101")
    
    # 示例 2: 下载期货主力合约“白糖”(SR0) 的日线历史数据
    # 注：新浪财经主力合约命名通常是品种大写字母拼音 + 0，例如白糖 SR0, 螺纹钢 RB0
    fetch_future_daily(symbol="SR0", start_date="20230101")
