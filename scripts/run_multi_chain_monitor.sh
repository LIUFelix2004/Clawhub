#!/bin/bash
# 多链代币实时监控运行脚本（使用OKX API）

# 设置环境变量
export PATH="/root/.nvm/versions/node/v22.22.0/bin:$PATH"
export NVM_DIR="/root/.nvm"

# OKX API凭证
export OKX_API_KEY="03f0b376-251c-4618-862e-ae92929e0416"
export OKX_SECRET_KEY="652ECE8FF13210065B0851FFDA9191F7"
export OKX_PASSPHRASE="onchainOS#666"

# 切换到工作目录
cd /root/.openclaw/workspace

# 创建日志目录
mkdir -p logs

# 运行Python脚本
python3 multi_chain_monitor.py >> logs/multi_chain_monitor.log 2>&1

# 记录运行时间
echo "=== 多链监控运行于: $(date '+%Y-%m-%d %H:%M:%S') ===" >> logs/multi_chain_monitor.log