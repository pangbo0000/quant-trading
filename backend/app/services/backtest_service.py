import os
import pandas as pd
from typing import Dict, Any, List
# 引入我们写好的底层行情映射库和回测引擎、双均线策略
from quant_core.data_pipeline.data_center import FUTURES_MARKET_MAP
from quant_core.backtesting.engine import BacktestEngine, double_ma_strategy

def get_all_symbols() -> Dict[str, str]:
    """
    获取系统支持的全部品种，转换为小写不带 0 的代码形式作为 Key
    例如: {"rb": "螺纹钢", "sr": "白糖", ...}
    """
    clean_map = {}
    for code, name in FUTURES_MARKET_MAP.items():
        clean_code = code.lower().replace("0", "")
        # 去掉主力两个字，使名字更简洁
        clean_name = name.replace("主力", "")
        clean_map[clean_code] = clean_name
    return clean_map

def get_all_periods() -> List[str]:
    """
    获取系统支持的全部时间周期级别
    """
    return ["1m", "5m", "15m", "30m", "60m", "daily", "weekly", "monthly", "yearly"]

def run_dynamic_backtest(
    symbol: str, 
    period: str, 
    strategy_name: str, 
    params: Dict[str, Any],
    initial_capital: float,
    commission_rate: float,
    slippage_points: float
) -> Dict[str, Any]:
    """
    动态参数实时回测桥接服务
    """
    # 1. 匹配行情文件名，如 "future_rb_daily.csv" 或 "future_rb_5m.csv"
    clean_symbol = symbol.lower()
    clean_period = period.lower()
    file_name = f"future_{clean_symbol}_{clean_period}.csv"
    
    # 确认合约乘数 (每点价值)，根据品种简单设定，不匹配的默认按 10.0 计算
    point_value_map = {
        "rb": 10.0,   # 螺纹钢：1手 10吨，价格波动 1元=10元
        "hc": 10.0,   # 热卷：10吨
        "ru": 10.0,   # 橡胶：10吨
        "au": 1000.0, # 黄金：1手 1000克
        "ag": 15.0,   # 白银：1手 15千克
        "cu": 5.0,    # 沪铜：1手 5吨
        "al": 5.0,    # 沪铝：5吨
        "zn": 5.0,    # 沪锌：5吨
        "m":  10.0,   # 豆粕：10吨
        "y":  10.0,   # 豆油：10吨
        "p":  10.0,   # 棕榈油：10吨
        "sr": 10.0,   # 白糖：10吨
        "i":  100.0,  # 铁矿石：100吨
        "j":  100.0,  # 焦炭：100吨
        "jm": 60.0,   # 焦煤：60吨
    }
    point_value = point_value_map.get(clean_symbol, 10.0)
    
    # 2. 动态注入参数并组装策略
    if strategy_name == "double_ma":
        # 解析前端传来的均线窗口参数，若无则使用默认值
        fast_period = int(params.get("fast_period", 5))
        slow_period = int(params.get("slow_period", 20))
        
        # 封装为可传入回测引擎的单参数策略函数
        def strategy_func(df: pd.DataFrame) -> pd.DataFrame:
            return double_ma_strategy(df, fast_period=fast_period, slow_period=slow_period)
    else:
        # 未来可在此处扩展其他内置策略模型
        return {
            "success": False,
            "message": f"不支持的策略类型: {strategy_name}"
        }
        
    try:
        # 3. 初始化底层的回测引擎
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_points=slippage_points,
            point_value=point_value
        )
        
        # 4. 加载数据与执行回测
        engine.load_data(file_name)
        results_df = engine.run_backtest(strategy_func)
        
        # 5. 格式化回测数据曲线，以便前端图表渲染
        # A. 净值曲线 (Equity Curve)
        equity_curve = []
        for idx, row in results_df.iterrows():
            equity_curve.append({
                "date": row["date"].strftime("%Y-%m-%d %H:%M:%S"),
                "value": round(float(row["portfolio_value"]), 2)
            })
            
        # B. K线图数据与交易信号标记 (用于TradingView)
        kline_data = []
        for idx, row in results_df.iterrows():
            kline_data.append({
                "date": row["date"].strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "signal": int(row["signal"])  # 1=金叉, -1=死叉, 0=平仓
            })
            
        # C. 整理交易流水明细
        trades_list = []
        for t in engine.trades:
            trades_list.append({
                "symbol": t["symbol"],
                "type": t["type"],
                "entry_time": t["entry_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "entry_price": float(t["entry_price"]),
                "exit_time": t["exit_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "exit_price": float(t["exit_price"]),
                "pnl_amount": round(float(t["pnl_amount"]), 2),
                "pnl_ratio": round(float(t["pnl_ratio"]), 4),
                "duration": round(float(t["duration"]), 1)
            })
            
        # 6. 对绩效指标进行标准化封装
        m = engine.metrics
        metrics_payload = {
            "total_return": round(float(m["total_return"]), 4),
            "annualized_return": round(float(m["annualized_return"]), 4),
            "max_drawdown": round(float(m["max_drawdown"]), 4),
            "sharpe_ratio": round(float(m["sharpe_ratio"]), 3),
            "total_trades": int(m["total_trades"]),
            "win_rate": round(float(m["win_rate"]), 4),
            "profit_loss_ratio": round(float(m["profit_loss_ratio"]), 2),
            "avg_profit": round(float(m["avg_profit"]), 2),
            "avg_loss": round(float(m["avg_loss"]), 2)
        }
        
        return {
            "success": True,
            "metrics": metrics_payload,
            "equity_curve": equity_curve,
            "kline_data": kline_data,
            "trades": trades_list
        }
        
    except FileNotFoundError:
        # 当行情文件在本地缺失时的友好报错
        return {
            "success": False,
            "message": f"行情库文件未下载或未补全: {file_name}。请确保先在终端运行 data_center.py 补全该行情周期数据！"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"回测逻辑执行异常: {str(e)}"
        }
