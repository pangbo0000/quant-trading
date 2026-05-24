from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from backend.app.services.backtest_service import (
    get_all_symbols,
    get_all_periods,
    run_dynamic_backtest
)

# 初始化 API 路由器
router = APIRouter()

# ==============================================================================
# Pydantic 核心数据模型验证定义
# ==============================================================================

class BacktestRequest(BaseModel):
    symbol: str = Field(..., description="期货主力合约品种代号，如 'rb' (螺纹钢), 'sr' (白糖), 'i' (铁矿石)")
    period: str = Field(..., description="回测数据周期，可选 '1m', '5m', '15m', '30m', '60m', 'daily', 'weekly', 'monthly'")
    strategy: str = Field(default="double_ma", description="选择的回测策略，默认 'double_ma' 双均线交叉策略")
    params: Dict[str, Any] = Field(
        default={"fast_period": 5, "slow_period": 20},
        description="用于计算策略信号的动态指标参数对"
    )
    initial_capital: float = Field(default=1000000.0, description="账户初始资本金 (元)")
    commission_rate: float = Field(default=0.0001, description="单边手续费率 (万分之一输入 0.0001)")
    slippage_points: float = Field(default=1.0, description="滑点点数损耗 (螺纹钢设 1.0 表示 1 点=10元)")

# ==============================================================================
# API 路由路径配置
# ==============================================================================

@router.get("/data/symbols", summary="获取系统支持的全部期货品种列表")
def api_get_symbols():
    """
    返回当前 AlphaQuant 系统行情库中支持的 55 个核心期货主力合约代码及中文名称。
    用于前端下拉菜单的选择框填充。
    """
    try:
        symbols_map = get_all_symbols()
        return {
            "success": True,
            "total": len(symbols_map),
            "data": symbols_map
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取品种列表失败: {str(e)}")

@router.get("/data/periods", summary="获取系统支持的全部时间周期列表")
def api_get_periods():
    """
    返回系统当前支持的全部回测时间周期级别（包含日内高频分钟线与本地高精度合成长周期）。
    """
    try:
        periods_list = get_all_periods()
        return {
            "success": True,
            "data": periods_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取周期列表失败: {str(e)}")

@router.post("/backtest/run", summary="执行动态配置实时量化策略回测")
def api_run_backtest(request: BacktestRequest):
    """
    前端点击“开始回测”的终极接口！
    后端接收动态输入的品种、周期、初始资金、手续费率、滑点以及自适应策略参数，
    在毫秒级内自动读取本地 CSV、驱动回测引擎，返回包括绩效分析、资金曲线、带有买卖信号的K线序列以及交易明细在内的完备 JSON。
    """
    try:
        print(f"[API] 收到回测请求: 品种={request.symbol} | 周期={request.period} | 策略={request.strategy} | 参数={request.params}")
        
        # 运行底层极速回测服务
        result = run_dynamic_backtest(
            symbol=request.symbol,
            period=request.period,
            strategy_name=request.strategy,
            params=request.params,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage_points=request.slippage_points
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("message", "回测执行失败！"))
            
        return result
        
    except Exception as e:
        print(f"[API_ERROR] 回测接口调用异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"回测内部计算异常: {str(e)}")
