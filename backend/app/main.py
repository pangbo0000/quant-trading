from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.endpoints import router as api_router

# 初始化 FastAPI 应用
app = FastAPI(
    title="AlphaQuant 量化回测 Web API 引擎",
    description="提供全市场多周期期货数据获取及实时动态策略回测计算服务的低延迟 Web API 引擎",
    version="1.0.0"
)

# 配置 CORS 跨域中间件
# 允许前端（如跑在 localhost:5173 的 React 或 Vue）能顺畅地跨域发起 API 请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名跨域访问，方便开发调试
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有的 HTTP 方法 (GET, POST, OPTIONS 等)
    allow_headers=["*"],  # 允许所有的 HTTP 头
)

# 挂载核心 API 路由器，添加 /api/v1 前缀
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    """
    系统根欢迎路径
    """
    return {
        "status": "online",
        "system": "AlphaQuant Trading System",
        "author": "Antigravity Pair Programmed",
        "docs_url": "/docs",
        "message": "如果您看到此信息，说明您的 AlphaQuant 后端服务已经完美运行！请访问 /docs 查看并调试 Swagger API 文档。"
    }
