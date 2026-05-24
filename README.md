# 📊 AlphaQuant 智能量化交易系统

AlphaQuant 是一个面向未来的、前后端分离的闭环智能量化交易系统。该系统集成了**数据管道、回测引擎、策略中心、模拟/实盘执行**四大核心功能，并提供直观且富科技感的**前端交易仪表盘（Dashboard）**，帮助交易者实现从策略研发到实盘运行的一站式闭环。

---

## 🏗️ 系统架构设计

系统采用**高内聚、低耦合**的分层模块化设计。通过 Python 强大的数据处理生态负责策略计算与数据流转，通过 FastAPI 构建高效的异步 API，前端使用 React/Vite 进行动态交易可视化与监控。

```mermaid
graph TD
    %% 外部数据源
    subgraph DataSources["外部数据源 (Yahoo/Binance/Tushare)"]
        DS[行情API / WebSockets]
    end

    %% 量化核心层
    subgraph QuantCore["量化核心层 (quant_core/)"]
        DP[数据管道 data_pipeline] --> DB[(本地数据库 SQLite/PG)]
        BT[回测引擎 backtesting] --> STR[策略中心 strategies]
        STR --> EX[执行模块 execution]
        DB --> BT
    end

    %% 后端 API 层
    subgraph BackendLayer["后端 API 层 (backend/)"]
        API[FastAPI Web 服务]
        WS[WebSocket 实时推送]
    end

    %% 前端交互层
    subgraph FrontendLayer["前端交互层 (frontend/)"]
        UI[React/Vite 交易面板]
        KLine[TradingView K线图表]
    end

    %% 数据与信号流向
    DS -->|行情数据获取| DP
    API -->|获取账户持仓/回测报告| UI
    WS -->|实时行情与订单状态| KLine
    EX -->|交易指令提交| Broker[券商/交易所API]
    Broker -->|成交回报与账户状态| EX
    STR -->|实时交易信号| API
```

---

## 📁 目录结构规划

```text
quant-trading/
├── data/                      # [LOCAL ONLY] 存放本地 CSV 行情数据及数据库文件
├── quant_core/                # 量化核心底层（独立于 Web 服务的算法核心）
│   ├── __init__.py
│   ├── data_pipeline/         # 数据收集与清洗模块（K线爬虫、入库逻辑）
│   ├── strategies/            # 交易策略中心（存放各类策略逻辑，如双均线等）
│   ├── backtesting/           # 回测引擎模块（读取历史数据，计算夏普、回撤等指标）
│   └── execution/             # 模拟盘/实盘交易执行模块（对接 API 下单）
├── backend/                   # 后端 Web API 层（使用 FastAPI 包装算法接口）
│   ├── app/
│   │   ├── api/               # API 路由接口 (策略配置, 账户持仓, 回测触发)
│   │   ├── core/              # 系统基础配置与安全设置
│   │   ├── models/            # 数据库ORM模型
│   │   ├── services/          # Web 业务逻辑层
│   │   └── main.py            # FastAPI 启动文件
│   ├── requirements.txt       # 后端依赖包
│   └── .env                   # 敏感环境变量（API Key、数据库链接等）
├── frontend/                  # 前端 Web 交互层（Vite + React + TS）
│   ├── src/
│   │   ├── components/        # 页面组件（K线图、持仓表、回测配置器）
│   │   ├── hooks/             # 自定义 React Hooks
│   │   ├── views/             # 页面视图 (Dashboard, Backtest, settings)
│   │   └── App.tsx
│   ├── package.json           # 前端依赖与构建脚本
│   └── vite.config.ts
├── .gitignore                 # Git 忽略文件（保护敏感资产和大体积数据）
├── .env.example               # 环境变量配置模板
└── README.md                  # 本设计白皮书
```

---

## 🛠️ 技术栈选型

* **后端 (Backend)**:
  * **语言**: Python 3.10+
  * **Web 框架**: FastAPI (异步、超高性能、内置 OpenAPI 文档)
  * **数据处理**: Pandas, NumPy
  * **回测核心**: Backtrader / 自定义轻量事件驱动回测引擎
* **前端 (Frontend)**:
  * **构建工具**: Vite
  * **框架**: React + TypeScript
  * **可视化**: TradingView Lightweight Charts (轻量级交互式 K 线图), Recharts/ECharts
  * **样式**: Vanilla CSS / Tailwind CSS
* **数据库 (Database)**:
  * **开发阶段**: SQLite (简单高效，无需配置)
  * **生产阶段**: PostgreSQL / InfluxDB (时序数据首选)

---

## 🚀 启动与运行计划

### 1. 准备本地开发环境
请确保本地已安装：
* **Python 3.10+** (可以在终端输入 `python --version` 验证)
* **Node.js 18+** (可以在终端输入 `node -v` 验证)
* **Git** (可以在终端输入 `git --version` 验证)

### 2. 关联您的 GitHub 仓库
我们已经在本地初始化了 Git 仓库，您可以按照以下步骤将本地代码推送到您的私有 GitHub 仓库中：
1. 登录 [GitHub](https://github.com/)，在右上角点击 **New repository**。
2. 填入 Repository name: `quant-trading`。
3. 务必选择 **Private**（私有仓库，防止策略和敏感 API 泄露）。
4. 不要勾选 "Initialize this repository with..." 任何选项。
5. 点击 **Create repository**。
6. 在本地的 `D:\ai\quant-trading` 目录下运行终端，依次执行以下命令：
   ```bash
   git branch -M main
   git remote add origin https://github.com/pangbo0000/quant-trading.git
   git push -u origin main
   ```
