# ClawAlert - 多链代币智能监控系统

![ClawAlert Logo](https://img.shields.io/badge/ClawAlert-Multi--Chain%20Monitor-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🎯 项目简介

ClawAlert 是一个强大的多链代币监控系统，专为DeFi交易者和投资者设计。系统实时监控BSC、Ethereum、Solana和Base四条主流区块链上的代币，检测异常交易活动并提供实时警报。

## ✨ 核心功能

### 🔍 智能监控
- **多链支持**：同时监控 BSC、Ethereum、Solana、Base 四条链
- **市值过滤**：仅监控市值超过100万美元的优质代币
- **实时交易量分析**：每10分钟检测一次交易量变化
- **大额交易追踪**：识别超过1万美元的单笔交易

### ⚡ 智能警报
- **交易量激增检测**：30分钟内交易量增长超过30%时触发警报
- **安全风险评估**：自动检测高风险代币（蜜罐、骗局等）
- **多重通知渠道**：支持Discord实时通知

### 📊 数据可视化
- **Web监控面板**：内置Flask Web界面，实时查看监控数据
- **Notion数据同步**：自动同步监控数据到Notion数据库
- **历史数据分析**：完整记录交易量历史，支持趋势分析

### 🛡️ 安全特性
- **代币白名单**：内置主流安全代币列表
- **风险模式识别**：自动识别高风险代币名称和合约
- **API限速处理**：智能重试机制，避免API限制

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Git
- OKX API账号（用于获取代币数据）
- Discord Webhook（用于通知，可选）
- Notion API密钥（用于数据同步，可选）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/clawAlert.git
   cd clawAlert
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入您的API密钥
   ```

4. **运行监控系统**
   ```bash
   # 手动运行
   python src/optimized_multi_chain_monitor.py
   
   # 或使用脚本运行
   bash scripts/run_optimized_monitor.sh
   ```

5. **启动Web监控面板**
   ```bash
   python src/monitor_dashboard.py
   # 访问 http://localhost:5000
   ```

## ⚙️ 配置说明

### 主要配置文件

1. **环境变量 (.env)**
   ```bash
   # OKX API配置
   OKX_API_KEY="your_api_key"
   OKX_SECRET_KEY="your_secret_key"
   OKX_PASSPHRASE="your_passphrase"
   
   # 监控参数
   MIN_MARKET_CAP=1000000      # 最小市值 $1M
   VOLUME_SURGE_THRESHOLD=0.3  # 30%交易量增长
   LARGE_TRADE_THRESHOLD=10000 # $10,000大额交易
   ```

2. **链配置**
   - 在 `src/config.example.py` 中配置各链参数
   - 可启用/禁用特定链的监控
   - 可自定义安全代币白名单

### 定时任务配置

配置Cron定时任务（每10分钟运行一次）：
```bash
# 编辑crontab
crontab -e

# 添加以下行
*/10 * * * * cd /path/to/clawAlert && bash scripts/run_optimized_monitor.sh >> logs/monitor.log 2>&1
```

## 📈 系统架构

```
ClawAlert/
├── src/
│   ├── optimized_multi_chain_monitor.py  # 主监控脚本
│   ├── final_notion_sync.py              # Notion数据同步
│   └── monitor_dashboard.py              # Web监控面板
├── scripts/
│   ├── run_optimized_monitor.sh          # 运行脚本
│   └── run_multi_chain_monitor.sh        # 备用运行脚本
├── data/
│   ├── examples/                         # 示例数据文件
│   └── (运行时生成的缓存文件)
├── static/                               # Web静态文件
├── templates/                            # Web模板文件
├── docs/                                 # 文档
├── requirements.txt                      # Python依赖
├── .env.example                          # 环境变量示例
└── README.md                            # 本文档
```

## 🔧 核心模块说明

### 1. 多链监控器 (`optimized_multi_chain_monitor.py`)
- **主要功能**：监控四条链的代币交易活动
- **检测逻辑**：交易量激增、大额交易、安全风险
- **通知机制**：Discord实时通知

### 2. Notion数据同步器 (`final_notion_sync.py`)
- **功能**：将监控数据同步到Notion数据库
- **特性**：自动创建数据库、智能映射属性、错误恢复
- **配置**：需要Notion API密钥和数据库ID

### 3. Web监控面板 (`monitor_dashboard.py`)
- **技术栈**：Flask + REST API
- **功能**：实时数据显示、监控状态查看、历史记录查询
- **访问**：`http://localhost:5000`

## 📊 数据流

```
OKX API数据源 → 数据采集 → 交易量分析 → 警报检测
      ↓                              ↓
   缓存存储                       Discord通知
      ↓                              ↓
Notion同步 ←──── 数据聚合 ←──── Web面板展示
```

## 🚨 警报类型

| 警报类型 | 触发条件 | 说明 |
|----------|----------|------|
| **交易量激增** | 30分钟内交易量增长>30% | 可能的市场操纵或重大新闻 |
| **大额交易** | 单笔交易>$10,000 | 大户或机构活动 |
| **高风险代币** | 检测到风险模式 | 蜜罐、骗局或高风险代币 |
| **API异常** | API请求连续失败 | 可能的数据源问题 |

## 🔐 安全建议

1. **API密钥保护**
   - 永远不要将API密钥提交到版本控制
   - 使用环境变量或密钥管理服务
   - 定期轮换API密钥

2. **监控配置**
   - 根据需求调整监控阈值
   - 启用合适的链配置
   - 定期检查日志文件

3. **数据备份**
   - 定期备份缓存数据
   - 导出历史监控记录
   - 配置数据保留策略

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 支持与联系

如有问题或建议，请：
- 提交 [Issue](https://github.com/yourusername/clawAlert/issues)
- 查看 [Wiki](https://github.com/yourusername/clawAlert/wiki) 获取详细文档
- 通过Discord联系我们

---

**免责声明**：本项目仅为技术工具，不构成投资建议。加密货币交易存在高风险，请谨慎决策。