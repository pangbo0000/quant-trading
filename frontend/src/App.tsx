import React, { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

// 后端 API 地址
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// ==============================================================================
// 1. TradingView 交互式 K 线图组件 (内置时间戳严格去重单调递增过滤)
// ==============================================================================
interface ChartData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  signal: number;
}

const TVChart: React.FC<{ data: ChartData[] }> = ({ data }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // 清理之前的图表容器
    chartContainerRef.current.innerHTML = '';

    // A. 初始化 TradingView 图表，注入极致暗黑赛博主题
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#12161C' },
        textColor: '#848E9C',
        fontFamily: "'Outfit', sans-serif",
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.02)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.02)' },
      },
      crosshair: {
        mode: 1, // Magnet 模式
        vertLine: { color: '#3B82F6', labelBackgroundColor: '#3B82F6' },
        horzLine: { color: '#3B82F6', labelBackgroundColor: '#3B82F6' },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.06)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.06)',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // B. 创建 K 线序列，配置极光绿和霓虹红的 K 线配色
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#0ECB81',
      downColor: '#F6465D',
      borderUpColor: '#0ECB81',
      borderDownColor: '#F6465D',
      wickUpColor: '#0ECB81',
      wickDownColor: '#F6465D',
    });

    // 🚀 高阶防崩溃设计：对数据进行时间戳严格去重与单调递增过滤
    // 这能 100% 避免因节假日时差重合数据抛出 "time must be strictly increasing" 断言错误导致页面白屏卸载
    const seenTimes = new Set<number>();
    const formattedData: any[] = [];
    const markers: any[] = [];

    // 对原始数据按日期正序排序，确保单调性
    const sortedData = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    sortedData.forEach(item => {
      const timestamp = Math.floor(new Date(item.date).getTime() / 1000);
      
      // 过滤掉无效时间戳和重复时间戳
      if (!isNaN(timestamp) && !seenTimes.has(timestamp)) {
        seenTimes.add(timestamp);
        
        // 加入 K 线点
        formattedData.push({
          time: timestamp as any,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
        });

        // 绑定信号标记
        if (item.signal === 1) {
          markers.push({
            time: timestamp as any,
            position: 'belowBar',
            color: '#0ECB81',
            shape: 'arrowUp',
            text: 'BUY',
            size: 1.5
          });
        } else if (item.signal === -1) {
          markers.push({
            time: timestamp as any,
            position: 'aboveBar',
            color: '#F6465D',
            shape: 'arrowDown',
            text: 'SELL',
            size: 1.5
          });
        }
      }
    });

    // 喂入清洗后的完美递增数据
    candlestickSeries.setData(formattedData);

    if (markers.length > 0) {
      candlestickSeries.setMarkers(markers);
    }

    // 自动缩放适应屏幕
    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    // 自适应视口缩放
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={chartContainerRef} style={{ width: '100%', height: '100%', borderRadius: '8px', overflow: 'hidden' }} />
    </div>
  );
};

// ==============================================================================
// 2. 主 App 页面
// ==============================================================================

export default function App() {
  // 元数据状态
  const [symbols, setSymbols] = useState<Record<string, string>>({});
  const [periods, setPeriods] = useState<string[]>([]);
  
  // 回测请求表单参数状态
  const [selectedSymbol, setSelectedSymbol] = useState('rb');
  const [selectedPeriod, setSelectedPeriod] = useState('5m');
  const [fastPeriod, setFastPeriod] = useState(5);
  const [slowPeriod, setSlowPeriod] = useState(20);
  const [capital, setCapital] = useState(1000000);
  const [commission, setCommission] = useState(0.0001);
  const [slippage, setSlippage] = useState(1.0);
  
  // 回测结果数据状态
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [metrics, setMetrics] = useState<any>(null);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [klineData, setKlineData] = useState<ChartData[]>([]);
  const [trades, setTrades] = useState<any[]>([]);

  // A. 初始化加载品种与周期选项
  useEffect(() => {
    fetch(`${API_BASE_URL}/data/symbols`)
      .then(res => res.json())
      .then(json => {
        if (json.success) setSymbols(json.data);
      })
      .catch(err => console.error("获取品种列表异常:", err));

    fetch(`${API_BASE_URL}/data/periods`)
      .then(res => res.json())
      .then(json => {
        if (json.success) setPeriods(json.data);
      })
      .catch(err => console.error("获取周期列表异常:", err));
  }, []);

  // B. ⚡ 启动极速回测事件
  const handleRunBacktest = () => {
    setLoading(true);
    setErrorMsg('');
    setMetrics(null);
    setEquityCurve([]);
    setKlineData([]);
    setTrades([]);
    
    const requestPayload = {
      symbol: selectedSymbol,
      period: selectedPeriod,
      strategy: 'double_ma',
      params: {
        fast_period: fastPeriod,
        slow_period: slowPeriod
      },
      initial_capital: parseFloat(capital.toString()),
      commission_rate: parseFloat(commission.toString()),
      slippage_points: parseFloat(slippage.toString())
    };

    fetch(`${API_BASE_URL}/backtest/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestPayload)
    })
      .then(res => res.json())
      .then(json => {
        setLoading(false);
        if (json.success) {
          setMetrics(json.metrics);
          setEquityCurve(json.equity_curve);
          setKlineData(json.kline_data);
          setTrades(json.trades);
        } else {
          setErrorMsg(json.message || '回测执行失败！');
        }
      })
      .catch(err => {
        setLoading(false);
        setErrorMsg('无法连接量化后端，请确保 FastAPI 服务在本地 8000 端口完美运行中！');
        console.error(err);
      });
  };

  return (
    <div className="glass-container">
      {/* 头部顶栏 */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '15px', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '24px', fontWeight: 'bold', background: 'linear-gradient(135deg, #3B82F6 0%, #0ECB81 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            AlphaQuant 📊
          </span>
          <span style={{ fontSize: '18px', fontWeight: '500', color: 'var(--text-muted)' }}>智能量化交易 Dashboard</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <span className="badge badge-long">API ONLINE</span>
          <span style={{ color: 'var(--text-muted)' }}>服务器: 127.0.0.1:8000</span>
        </div>
      </header>

      {/* 主版面布局栅格 */}
      <div className="quant-layout">
        
        {/* 左侧策略与参数控制器面板 */}
        <aside className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', height: 'fit-content' }}>
          <h3 style={{ fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>📁 策略开发控制台</h3>
          
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>交易品种 (Symbol)</label>
            <select className="neon-input neon-select" value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)}>
              {Object.entries(symbols).map(([code, name]) => (
                <option key={code} value={code}>{name} ({code.toUpperCase()})</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>回测周期 (Period)</label>
            <select className="neon-input neon-select" value={selectedPeriod} onChange={e => setSelectedPeriod(e.target.value)}>
              {periods.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>快均线 (Fast)</label>
              <input type="number" className="neon-input" value={fastPeriod} onChange={e => setFastPeriod(parseInt(e.target.value) || 0)} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>慢均线 (Slow)</label>
              <input type="number" className="neon-input" value={slowPeriod} onChange={e => setSlowPeriod(parseInt(e.target.value) || 0)} />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>初始资本金 (元)</label>
            <input type="number" className="neon-input" value={capital} onChange={e => setCapital(parseInt(e.target.value) || 0)} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>手续费率</label>
              <input type="number" step="0.0001" className="neon-input" value={commission} onChange={e => setCommission(parseFloat(e.target.value) || 0)} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>单手滑点</label>
              <input type="number" step="1" className="neon-input" value={slippage} onChange={e => setSlippage(parseFloat(e.target.value) || 0)} />
            </div>
          </div>

          <button 
            className={`neon-btn ${loading ? 'neon-btn-disabled' : ''}`} 
            onClick={handleRunBacktest}
            disabled={loading}
          >
            {loading ? '回测结算中...' : '⚡ 启动极速回测'}
          </button>

          {errorMsg && (
            <div style={{ color: 'var(--neon-red)', fontSize: '12px', padding: '10px', backgroundColor: 'rgba(246, 70, 93, 0.08)', borderRadius: '6px', border: '1px solid rgba(246, 70, 93, 0.2)' }}>
              {errorMsg}
            </div>
          )}
        </aside>

        {/* 右侧：图表核心网格 */}
        <main className="chart-grid">
          {/* 上部：TradingView K 线交互图表 */}
          <div className="glass-card" style={{ padding: '15px', position: 'relative', minHeight: '0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '14px' }}>
              <span style={{ fontWeight: 600 }}>📈 TradingView 极客交互式 K 线行情图 (带交易标记)</span>
              {klineData.length > 0 && <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>已加载 K 线: {klineData.length} 根</span>}
            </div>
            {klineData.length > 0 ? (
              <TVChart data={klineData} />
            ) : (
              <div style={{ height: 'calc(100% - 30px)', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)' }}>
                {loading ? '量化核心高速运算中，正在加载 TradingView 图表组件...' : '请在左侧配置好参数，点击“启动极速回测”以激活 TradingView 交互式 K 线图表'}
              </div>
            )}
          </div>

          {/* 下部：资金曲线折线图 */}
          <div className="glass-card" style={{ padding: '15px', minHeight: '0' }}>
            <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '10px' }}>📉 组合总资产权益净值走势曲线 (Equity Curve)</div>
            {equityCurve.length > 0 ? (
              <div style={{ width: '100%', height: '200px' }}>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={equityCurve} margin={{ top: 5, right: 5, left: 10, bottom: 5 }}>
                    <defs>
                      <linearGradient id="colorGlow" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.25}/>
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.02)" />
                    <XAxis dataKey="date" stroke="rgba(255,255,255,0.2)" tick={{ fontSize: 10 }} tickLine={false} />
                    <YAxis 
                      domain={['dataMin - 1000', 'dataMax + 1000']} 
                      stroke="rgba(255,255,255,0.2)" 
                      tick={{ fontSize: 10 }} 
                      tickLine={false} 
                      tickFormatter={val => `${(val / 10000).toFixed(1)}万`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#161A22', borderColor: 'rgba(255,255,255,0.08)', borderRadius: '6px', color: 'var(--text-main)' }}
                      labelStyle={{ color: 'var(--text-muted)', fontSize: '11px' }}
                      itemStyle={{ color: '#3B82F6', fontSize: '13px', fontFamily: 'var(--font-mono)' }}
                      formatter={(value: any) => [`${parseFloat(value).toLocaleString()} 元`, '权益净值']}
                    />
                    <Area type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} fillOpacity={1} fill="url(#colorGlow)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div style={{ height: 'calc(100% - 30px)', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)' }}>
                {loading ? '量化核心高速运算中，正在加载资金净值曲线...' : '暂无回测资金曲线数据'}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* 下方核心绩效指标卡片 */}
      {metrics && (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '20px' }}>
          <div className="glass-card" style={{ padding: '15px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px' }}>累计收益率 (Total Return)</div>
            <div className={`color-${metrics.total_return >= 0 ? 'up' : 'down'}`} style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
              {metrics.total_return >= 0 ? '+' : ''}{(metrics.total_return * 100).toFixed(2)}%
            </div>
          </div>
          <div className="glass-card" style={{ padding: '15px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px' }}>年化收益率 (Annualized)</div>
            <div className={`color-${metrics.annualized_return >= 0 ? 'up' : 'down'}`} style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
              {metrics.annualized_return >= 0 ? '+' : ''}{(metrics.annualized_return * 100).toFixed(2)}%
            </div>
          </div>
          <div className="glass-card" style={{ padding: '15px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px' }}>最大资金回撤 (Max Drawdown)</div>
            <div className="color-down" style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
              {(metrics.max_drawdown * 100).toFixed(2)}%
            </div>
          </div>
          <div className="glass-card" style={{ padding: '15px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px' }}>策略夏普比率 (Sharpe Ratio)</div>
            <div className="color-blue" style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
              {metrics.sharpe_ratio.toFixed(3)}
            </div>
          </div>
          <div className="glass-card" style={{ padding: '15px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px' }}>策略胜率 / 交易笔数</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
              {(metrics.win_rate * 100).toFixed(1)}% <span style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 400 }}>({metrics.total_trades}笔)</span>
            </div>
          </div>
        </section>
      )}

      {/* 最下方交易历史明细表 */}
      {trades.length > 0 && (
        <section className="glass-card" style={{ marginTop: '20px', padding: '20px' }}>
          <h3 style={{ fontSize: '15px', marginBottom: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>📋 交易平仓历史明细账单 (全量记录)</h3>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <table className="neon-table">
              <thead>
                <tr>
                  <th>品种</th>
                  <th>方向</th>
                  <th>入场时间</th>
                  <th>入场价格</th>
                  <th>出场时间</th>
                  <th>出场价格</th>
                  <th>净盈亏 (元)</th>
                  <th>收益率</th>
                  <th>持仓时长 (分钟)</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, idx) => (
                  <tr key={idx}>
                    <td>{t.symbol}</td>
                    <td>
                      <span className={`badge badge-${t.type.toLowerCase()}`}>{t.type}</span>
                    </td>
                    <td>{t.entry_time}</td>
                    <td>{t.entry_price.toFixed(1)}</td>
                    <td>{t.exit_time}</td>
                    <td>{t.exit_price.toFixed(1)}</td>
                    <td className={`color-${t.pnl_amount >= 0 ? 'up' : 'down'}`} style={{ fontWeight: 500 }}>
                      {t.pnl_amount >= 0 ? '+' : ''}{t.pnl_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    </td>
                    <td className={`color-${t.pnl_ratio >= 0 ? 'up' : 'down'}`}>
                      {t.pnl_ratio >= 0 ? '+' : ''}{(t.pnl_ratio * 100).toFixed(2)}%
                    </td>
                    <td>{t.duration} m</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
