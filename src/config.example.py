#!/usr/bin/env python3
"""
ClawAlert 配置示例
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置"""
    
    # OKX API配置
    OKX_API_KEY = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
    
    # Discord通知配置
    DISCORD_CHANNEL = os.getenv("DISCORD_CHANNEL", "channel:your_channel_id")
    OPENCLAW_PATH = os.getenv("OPENCLAW_PATH", "/usr/local/bin/openclaw")
    
    # Notion配置（可选）
    NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
    
    # 监控配置
    MIN_MARKET_CAP = int(os.getenv("MIN_MARKET_CAP", 1000000))  # $1M
    VOLUME_SURGE_THRESHOLD = float(os.getenv("VOLUME_SURGE_THRESHOLD", 0.3))  # 30%
    LARGE_TRADE_THRESHOLD = int(os.getenv("LARGE_TRADE_THRESHOLD", 10000))  # $10,000
    CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 10))
    
    # 链配置
    ENABLE_BSC = os.getenv("ENABLE_BSC", "true").lower() == "true"
    ENABLE_ETHEREUM = os.getenv("ENABLE_ETHEREUM", "true").lower() == "true"
    ENABLE_SOLANA = os.getenv("ENABLE_SOLANA", "true").lower() == "true"
    ENABLE_BASE = os.getenv("ENABLE_BASE", "true").lower() == "true"
    
    # 安全代币白名单
    SAFE_TOKENS = {
        "bsc": {
            "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": {"symbol": "WBNB", "name": "Wrapped BNB"},
            "0x55d398326f99059ff775485246999027b3197955": {"symbol": "USDT", "name": "Tether USD"},
            "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": {"symbol": "USDC", "name": "USD Coin"},
        },
        "ethereum": {
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": {"symbol": "WETH", "name": "Wrapped Ethereum"},
            "0xdac17f958d2ee523a2206206994597c13d831ec7": {"symbol": "USDT", "name": "Tether USD"},
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {"symbol": "USDC", "name": "USD Coin"},
        },
        "solana": {
            "So11111111111111111111111111111111111111112": {"symbol": "SOL", "name": "Solana"},
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {"symbol": "USDC", "name": "USD Coin"},
        },
        "base": {
            "0x4200000000000000000000000000000000000006": {"symbol": "WETH", "name": "Wrapped Ethereum"},
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {"symbol": "USDC", "name": "USD Coin"},
        }
    }
    
    # 风险模式匹配（用于检测高风险代币）
    RISK_PATTERNS = [
        r"honeypot", r"rug", r"scam", r"fake", 
        r"test", r"shitcoin", r"meme", r"elon",
        r"inu$", r"dog", r"baby", r"floki", r"moon", r"woof"
    ]

# 全局配置实例
config = Config()