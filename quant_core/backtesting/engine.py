import os
import numpy as np
import pandas as pd
from datetime import datetime

# 获取当前项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

class BacktestEngine:
    """
    AlphaQuant 高性能、极简自研量化回测引擎 (路线 B 🌟)
    采用‘向量化计算信号 + 事件驱动仿真账户资金’混合架构，兼具极速回测与高精度仿真的优势。
    """
    def __init__(self, initial_capital: float = 1000000.0, commission_rate: float = 0.0001, slippage_points: float = 1.0, point_value: float = 10.0):
        """
        初始化回测引擎
        
        :param initial_capital: 初始资金（默认 100 万）
        :param commission_rate: 双边手续费率（默认万分之一）
        :param slippage_points: 滑点点数（默认 1 个最小变动价位，例如螺纹钢 1 点=10元）
        :param point_value: 合约乘数 / 每点价值（例如螺纹钢 1 手 = 10 吨，每点 10 元）
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_points = slippage_points
        self.point_value = point_value
        
        self.df = pd.DataFrame()
        self.results = pd.DataFrame()
        self.trades = []
        self.metrics = {}
        self.file_name = ""

    def load_data(self, file_name: str) -> pd.DataFrame:
        """
        加载本地 CSV 行情数据文件
        """
        file_path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"[ERROR] 行情文件不存在: {file_path}")
            
        print(f"[ENGINE] 正在加载历史行情数据: {file_name}...")
        df = pd.read_csv(file_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        self.df = df
        self.file_name = file_name
        print(f"[ENGINE] 数据加载成功，共 {len(self.df)} 行记录 (时间跨度: {self.df['date'].min()} -> {self.df['date'].max()})")
        return self.df

    def run_backtest(self, strategy_func) -> pd.DataFrame:
        """
        运行策略回测
        
        :param strategy_func: 策略算法函数。该函数接收行情 DataFrame，并自动在其中计算生成 'signal' 列
                              ('signal': 1=持有多头, -1=持有空头, 0=平仓/空仓)
        """
        if self.df.empty:
            raise ValueError("[ERROR] 请先加载行情数据！")
            
        print("[ENGINE] 正在通过策略函数计算买卖交易信号...")
        # 1. 调用策略生成交易信号
        df = strategy_func(self.df.copy())
        
        if "signal" not in df.columns:
            raise ValueError("[ERROR] 策略函数必须返回包含 'signal' 列的 DataFrame！")
            
        # 确保信号只包含 1, -1, 0 且无空值
        df["signal"] = df["signal"].fillna(0).astype(int)
        
        print("[ENGINE] 正在启动高精度账户资金与交易流水仿真...")
        
        # 2. 模拟资金流动与委托执行
        cash = self.initial_capital
        position = 0      # 当前持仓仓位: 0=空仓, 1=多头, -1=空头
        entry_price = 0.0 # 入场均价
        entry_time = None
        
        portfolio_values = [] # 记录组合净值曲线
        
        # 遍历每一行（每一根 K 线）
        for idx, row in df.iterrows():
            current_signal = row["signal"]
            current_close = row["close"]
            current_time = row["date"]
            
            # 手续费和滑点折算
            slippage_cost = self.slippage_points * self.point_value
            
            # 检测信号变化（发生交易开/平仓）
            if current_signal != position:
                # A. 先平掉已有仓位
                if position != 0:
                    exit_price = current_close
                    # 期货双边交易：多头平仓价格要扣除滑点，空头平仓要加上滑点
                    if position == 1:
                        real_exit_price = exit_price - self.slippage_points
                    else:
                        real_exit_price = exit_price + self.slippage_points
                        
                    # 计算盈亏金额 (平仓价与入场价的价差)
                    trade_pnl = position * (real_exit_price - entry_price) * self.point_value
                    
                    # 扣除平仓手续费
                    close_commission = real_exit_price * self.point_value * self.commission_rate
                    trade_pnl -= close_commission
                    cash -= close_commission
                    
                    # 组合账户资金结算
                    cash += trade_pnl
                    
                    # 记录一笔完整的交易流水
                    pnl_ratio = (real_exit_price / entry_price - 1.0) * position
                    self.trades.append({
                        "symbol": self.file_name.split("_")[1].upper(),
                        "type": "LONG" if position == 1 else "SHORT",
                        "entry_time": entry_time,
                        "entry_price": entry_price,
                        "exit_time": current_time,
                        "exit_price": real_exit_price,
                        "pnl_amount": trade_pnl,
                        "pnl_ratio": pnl_ratio,
                        "duration": (current_time - entry_time).total_seconds() / 60.0 # 持续时间（分钟）
                    })
                    
                # B. 开新仓
                if current_signal != 0:
                    entry_price = current_close
                    # 多头开仓加滑点，空头开仓减滑点
                    if current_signal == 1:
                        entry_price += self.slippage_points
                    else:
                        entry_price -= self.slippage_points
                        
                    entry_time = current_time
                    
                    # 扣除开仓手续费
                    open_commission = entry_price * self.point_value * self.commission_rate
                    cash -= open_commission
                    
                position = current_signal
                
            # C. 每日/每分钟的资金曲线持仓估值结算
            if position != 0:
                # 浮动盈亏估值
                floating_pnl = position * (current_close - entry_price) * self.point_value
                current_portfolio_value = cash + floating_pnl
            else:
                current_portfolio_value = cash
                
            portfolio_values.append(current_portfolio_value)
            
        df["portfolio_value"] = portfolio_values
        df["returns"] = df["portfolio_value"].pct_change().fillna(0)
        self.results = df
        
        # 3. 计算绩效指标
        self.calculate_metrics()
        return self.results

    def calculate_metrics(self):
        """
        高精度计算策略回测绩效分析指标
        """
        df = self.results
        trades = self.trades
        
        if df.empty:
            return
            
        total_days = (df["date"].max() - df["date"].min()).days
        if total_days == 0:
            total_days = 1
            
        # 计算资金曲线基础数据
        portfolio_value = df["portfolio_value"]
        total_return = portfolio_value.iloc[-1] / self.initial_capital - 1.0
        
        # 年化收益率 (以 250 个交易日折算)
        annualized_return = (1.0 + total_return) ** (365.0 / total_days) - 1.0
        
        # 计算最大回撤 (Max Drawdown)
        cum_max = portfolio_value.cummax()
        drawdown = (portfolio_value - cum_max) / cum_max
        max_drawdown = drawdown.min()
        
        # 计算夏普比率 (Sharpe Ratio)
        # 期货策略由于交易频次 and 数据采样不一，我们使用收益率波动比折算年化夏普
        returns = df["returns"]
        if returns.std() != 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(250 * 240 if len(df) > 5000 else 250)
        else:
            sharpe_ratio = 0.0
            
        # 统计交易历史
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["pnl_amount"] > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        profit_amounts = [t["pnl_amount"] for t in trades if t["pnl_amount"] > 0]
        loss_amounts = [t["pnl_amount"] for t in trades if t["pnl_amount"] <= 0]
        
        avg_profit = np.mean(profit_amounts) if profit_amounts else 0.0
        avg_loss = np.mean(loss_amounts) if loss_amounts else 0.0
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0.0
        
        self.metrics = {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_loss_ratio": profit_loss_ratio,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss
        }

    def output_report(self):
        """
        用极其精美、富有科技感的排版在控制台打印策略回测分析报告 (兼容所有控制台编码)
        """
        m = self.metrics
        if not m:
            print("[ENGINE] 回测指标为空，请先运行回测！")
            return
            
        print("\n" + "="*60)
        print("[REPORT]   AlphaQuant 极速量化策略回测绩效分析报告   [REPORT]")
        print("="*60)
        print(f" 初始资金  : {self.initial_capital:,.2f} 元")
        print(f" 期末资产  : {self.results['portfolio_value'].iloc[-1]:,.2f} 元")
        print(f" 时间跨度  : {self.results['date'].min()} 至 {self.results['date'].max()}")
        print("-" * 60)
        print(f" [+] 累计收益率  : {m['total_return']:+.2%}")
        print(f" [+] 年化收益率  : {m['annualized_return']:+.2%}")
        print(f" [-] 最大资金回撤: {m['max_drawdown']:.2%}")
        print(f" [*] 策略夏普比率: {m['sharpe_ratio']:.3f}")
        print("-" * 60)
        print(f" [STATS] 总交易笔数  : {m['total_trades']} 笔")
        print(f" [WIN]   策略胜率    : {m['win_rate']:.2%}")
        print(f" [RATIO] 盈亏金额比  : {m['profit_loss_ratio']:.2f} (单笔平均盈利/单笔平均亏损)")
        print(f" [+] 平均单笔盈利: {m['avg_profit']:+,.2f} 元")
        print(f" [-] 平均单笔亏损: {m['avg_loss']:+,.2f} 元")
        print("="*60)
        
        # 打印最近 5 笔交易明细
        if self.trades:
            print("\n[DETAILS] 最近 5 笔交易详细明细:")
            print("-" * 80)
            print(f"{'品种':^6}{'方向':^6}{'入场时间':^18}{'入场价':^10}{'出场时间':^18}{'出场价':^10}{'盈亏(元)':^10}")
            print("-" * 80)
            for t in self.trades[-5:]:
                print(f"{t['symbol']:^8}{t['type']:^6}{t['entry_time'].strftime('%m-%d %H:%M'):^18}{t['entry_price']:^11.1f}{t['exit_time'].strftime('%m-%d %H:%M'):^18}{t['exit_price']:^11.1f}{t['pnl_amount']:^12+,.2f}")
            print("-" * 80 + "\n")

# ==============================================================================
# 5. 经典量化交易策略展示（双均线策略）
# ==============================================================================

def double_ma_strategy(df: pd.DataFrame, fast_period: int = 5, slow_period: int = 20) -> pd.DataFrame:
    """
    经典双均线交叉交易策略 (Double Moving Average Crossover)
    * 金叉（快线从下方穿过慢线）：满仓持有多头 (signal = 1)
    * 死叉（快线从上方穿过慢线）：满仓持有空头 (signal = -1)
    """
    # 1. 计算均线
    df["fast_ma"] = df["close"].rolling(window=fast_period).mean()
    df["slow_ma"] = df["close"].rolling(window=slow_period).mean()
    
    # 2. 向量化判断信号
    # 初始化信号为 0
    df["signal"] = 0
    
    # 金叉条件：快线 > 慢线
    # 死叉条件：快线 < 慢线
    df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1
    df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1
    
    # 3. 仓位向前移位 1 位，避开未来函数（本Bar结束产生信号，下个Bar开盘才能成交）
    df["signal"] = df["signal"].shift(1).fillna(0).astype(int)
    return df

if __name__ == "__main__":
    print(">>> 启动 AlphaQuant 独立回测引擎验证...")
    
    # 1. 初始化回测引擎 (以螺纹钢为例，1 手 10吨，价格变动 1点 = 10元，滑点设为 1点)
    engine = BacktestEngine(
        initial_capital=1000000.0, 
        commission_rate=0.0001, 
        slippage_points=1.0, 
        point_value=10.0
    )
    
    # 2. 加载最近自动下载好的螺纹钢 5 分钟线数据
    try:
        # data/future_rb_5m.csv 已经在上一步圆满下载建仓成功！
        engine.load_data("future_rb_5m.csv")
        
        # 3. 运行经典 5/20周期 双均线回测
        engine.run_backtest(double_ma_strategy)
        
        # 4. 精美排版打印分析报告
        engine.output_report()
        
    except Exception as e:
        print(f"[ERROR] 回测验证运行失败: {e}")
