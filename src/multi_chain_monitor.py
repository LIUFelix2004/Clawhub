#!/usr/bin/env python3
"""
多链代币实时监控系统 - 使用OKX API
监控BSC、Base、Solana、Ethereum链上交易量激增和大额交易
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
import pytz
import subprocess
from typing import Dict, List, Optional, Tuple, Set
import re

# 配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DISCORD_CHANNEL = "channel:1476514989408911360"

# OKX API凭证（共享测试密钥）
OKX_API_KEY = "03f0b376-251c-4618-862e-ae92929e0416"
OKX_SECRET_KEY = "652ECE8FF13210065B0851FFDA9191F7"
OKX_PASSPHRASE = "onchainOS#666"

# BSCScan API
BSCSCAN_API_KEY = "RZA3QZITWHKTXUTAICJVTBGHK74VRE7PCS"

class MultiChainTokenMonitor:
    """多链代币实时监控器 - 使用OKX API"""
    
    def __init__(self):
        self.env = os.environ.copy()
        self.env["PATH"] = f"/root/.nvm/versions/node/v22.22.0/bin:{self.env.get('PATH', '')}"
        self.env["NVM_DIR"] = "/root/.nvm"
        
        # 缓存文件
        self.cache_file = "/root/.openclaw/workspace/multi_chain_cache.json"
        self.alert_history_file = "/root/.openclaw/workspace/multi_chain_alerts.json"
        
        # 支持的链配置
        self.chains = {
            "bsc": {"name": "BSC", "chainIndex": "56", "scan_api": "bscscan"},
            "base": {"name": "Base", "chainIndex": "8453", "scan_api": "basescan"},
            "solana": {"name": "Solana", "chainIndex": "501", "scan_api": "solscan"},
            "ethereum": {"name": "Ethereum", "chainIndex": "1", "scan_api": "etherscan"}
        }
        
        # 安全代币白名单（各链主要代币）
        self.safe_tokens = {
            "bsc": {
                "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": {"symbol": "WBNB", "name": "Wrapped BNB"},
                "0x55d398326f99059ff775485246999027b3197955": {"symbol": "USDT", "name": "Tether USD"},
                "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": {"symbol": "USDC", "name": "USD Coin"},
                "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82": {"symbol": "CAKE", "name": "PancakeSwap"},
            },
            "ethereum": {
                "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": {"symbol": "WETH", "name": "Wrapped Ethereum"},
                "0xdac17f958d2ee523a2206206994597c13d831ec7": {"symbol": "USDT", "name": "Tether USD"},
                "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {"symbol": "USDC", "name": "USD Coin"},
                "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0": {"symbol": "MATIC", "name": "Polygon"},
            },
            "solana": {
                "So11111111111111111111111111111111111111112": {"symbol": "SOL", "name": "Solana"},
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {"symbol": "USDC", "name": "USD Coin"},
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": {"symbol": "USDT", "name": "Tether USD"},
                "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": {"symbol": "BONK", "name": "Bonk"},
            },
            "base": {
                "0x4200000000000000000000000000000000000006": {"symbol": "WETH", "name": "Wrapped Ethereum"},
                "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {"symbol": "USDC", "name": "USD Coin"},
                "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2": {"symbol": "USDbC", "name": "USD Base Coin"},
            }
        }
        
        # 高风险特征
        self.risk_patterns = [
            r"honeypot", r"rug", r"scam", r"fake", 
            r"test", r"shitcoin", r"meme", r"elon",
            r"inu$", r"dog", r"baby", r"floki", r"moon", r"woof"
        ]
        
        # 监控配置（按用户要求优化）
        self.config = {
            "min_market_cap": 10000000,  # 10M USD（提高要求）
            "volume_surge_threshold": 0.3,  # 30%增长（30分钟内）
            "min_volume_30min": 100000,  # 30分钟内10万USD交易量
            "large_trade_threshold": 10000,  # 大额交易阈值 $10,000
            "check_interval_minutes": 10,  # 每10分钟检查一次
            "max_tokens_per_chain": 30,  # 每链最多监控30个代币
            "volume_timeframe": "30min",  # 使用30分钟交易量数据
            "api_delay_seconds": 2,  # API调用间隔
            "rate_limit_retry_delay": 10,  # 限速后重试延迟
            "max_retries": 3,  # 最大重试次数
            "consecutive_error_limit": 5,  # 连续错误次数限制
            "monitor_chains": ["bsc", "base", "solana", "ethereum"]  # 监控的链
        }
        
        # onchainos CLI路径
        self.onchainos_path = "/root/.local/bin/onchainos"
        
    def run_openclaw(self, args: list, timeout: int = 30) -> dict:
        """运行OpenClaw命令"""
        try:
            cmd = ["/root/.local/share/pnpm/openclaw"] + args
            result = subprocess.run(cmd, env=self.env, capture_output=True, text=True, timeout=timeout)
            return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_onchainos(self, args: list, timeout: int = 30) -> dict:
        """运行onchainos命令（带速率限制重试）"""
        max_retries = self.config.get("max_retries", 2)
        retry_delay = self.config.get("rate_limit_retry_delay", 5)
        
        for attempt in range(max_retries + 1):
            try:
                env = self.env.copy()
                env["OKX_API_KEY"] = OKX_API_KEY
                env["OKX_SECRET_KEY"] = OKX_SECRET_KEY
                env["OKX_PASSPHRASE"] = OKX_PASSPHRASE
                
                cmd = [self.onchainos_path] + args
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
                
                # 解析JSON输出
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        
                        # 检查API是否返回错误（如速率限制）
                        if not data.get("ok", True):
                            error_msg = data.get("error", "Unknown error")
                            if "Rate limited" in error_msg and attempt < max_retries:
                                print(f"⚠️ API速率限制，等待{retry_delay}秒后重试 ({attempt+1}/{max_retries})")
                                time.sleep(retry_delay)
                                continue
                            else:
                                return {"success": False, "error": error_msg, "data": data}
                        
                        return {"success": True, "data": data, "raw": result.stdout}
                    except json.JSONDecodeError:
                        return {"success": False, "error": f"JSON解析失败: {result.stdout[:100]}"}
                else:
                    # 检查stderr中是否有速率限制信息
                    stderr = result.stderr
                    if "Rate limited" in stderr and attempt < max_retries:
                        print(f"⚠️ 子进程速率限制，等待{retry_delay}秒后重试 ({attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    return {"success": False, "error": stderr}
            except Exception as e:
                if attempt == max_retries:
                    return {"success": False, "error": str(e)}
                else:
                    print(f"⚠️ 执行异常，等待{retry_delay}秒后重试 ({attempt+1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
        
        return {"success": False, "error": "达到最大重试次数"}
    
    def load_cache(self) -> dict:
        """加载缓存数据"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "volume_history": {},  # 格式: {chain_token_address: [{timestamp, volume30min}, ...]}
            "last_trades": {},  # 上次检查的交易ID
            "last_update": None,
        }
    
    def save_cache(self, data: dict):
        """保存缓存数据"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_alert_history(self) -> dict:
        """加载报警历史"""
        if os.path.exists(self.alert_history_file):
            try:
                with open(self.alert_history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"alerts": {}, "last_alert_time": {}}
    
    def save_alert_history(self, history: dict):
        """保存报警历史"""
        with open(self.alert_history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_top_tokens_by_chain(self, chain: str, limit: int = 30) -> List[Dict]:
        """使用OKX API获取指定链的热门代币"""
        chain_info = self.chains.get(chain)
        if not chain_info:
            print(f"❌ 不支持的链: {chain}")
            return []
        
        print(f"📡 使用OKX API获取{chain_info['name']}链热门代币...")
        
        # 使用onchainos token trending命令
        result = self.run_onchainos([
            "token", "trending",
            "--chains", chain,
            "--sort-by", "5",  # 按交易量排序
            "--time-frame", "4",  # 24小时
        ])
        
        if not result["success"]:
            print(f"❌ 获取{chain_info['name']}数据失败: {result['error']}")
            return self.get_fallback_tokens(chain)
        
        data = result.get("data", {})
        if not data.get("ok") or "data" not in data:
            print(f"❌ {chain_info['name']} API返回错误: {data}")
            return self.get_fallback_tokens(chain)
        
        tokens = data["data"]
        max_tokens = min(len(tokens), limit)
        
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
        
        print(f"✅ 从{chain_info['name']}获取到 {len(tokens)} 个代币")
        
        # 格式化数据
        formatted_tokens = []
        for token in tokens:
            formatted_tokens.append({
                "id": token.get("tokenContractAddress", ""),
                "symbol": token.get("tokenSymbol", ""),
                "name": token.get("tokenSymbol", ""),
                "chain": chain,
                "chain_name": chain_info["name"],
                "market_cap": float(token.get("marketCap", 0)),
                "volume_24h": float(token.get("volume", 0)),
                "liquidity": float(token.get("liquidity", 0)),
                "txs_24h": int(token.get("txs", 0)),
                "holders": int(token.get("holders", 0)),
                "price": float(token.get("price", 0)),
                "price_change_24h": float(token.get("change", 0)),
            })
        
        return formatted_tokens
    
    def get_fallback_tokens(self, chain: str) -> List[Dict]:
        """获取备用代币列表"""
        tokens = []
        chain_tokens = self.safe_tokens.get(chain, {})
        
        for address, info in chain_tokens.items():
            tokens.append({
                "id": address,
                "symbol": info["symbol"],
                "name": info["name"],
                "chain": chain,
                "chain_name": self.chains.get(chain, {}).get("name", chain),
                "market_cap": 10000000,  # 默认10M市值
                "volume_24h": 1000000,  # 默认1M交易量
                "liquidity": 5000000,
                "txs_24h": 1000,
                "holders": 10000,
                "price": 1.0,
                "price_change_24h": 0,
            })
        return tokens
    
    def get_token_price_info(self, token_address: str, chain: str) -> Optional[Dict]:
        """获取代币详细价格信息"""
        result = self.run_onchainos([
            "token", "price-info",
            "--address", token_address,
            "--chain", chain
        ])
        
        if not result["success"]:
            print(f"❌ 获取代币 {token_address} 价格信息失败: {result['error']}")
            return None
        
        data = result.get("data", {})
        if not data.get("ok") or "data" not in data or not data["data"]:
            return None
        
        token_data = data["data"][0]
        
        # 计算30分钟交易量（如果没有volume30min字段，用volume1H/2估算）
        volume_1h = float(token_data.get("volume1H", 0))
        volume_30min_est = volume_1h / 2
        
        # 提取关键数据
        return {
            "volume_30min": volume_30min_est,  # 30分钟交易量估计
            "volume_1h": volume_1h,
            "volume_4h": float(token_data.get("volume4H", 0)),
            "volume_24h": float(token_data.get("volume24H", 0)),
            "txs_1h": int(token_data.get("txs1H", 0)),
            "txs_24h": int(token_data.get("txs24H", 0)),
            "price": float(token_data.get("price", 0)),
            "price_change_1h": float(token_data.get("priceChange1H", 0)),
            "price_change_24h": float(token_data.get("priceChange24H", 0)),
            "market_cap": float(token_data.get("marketCap", 0)),
            "liquidity": float(token_data.get("liquidity", 0)),
            "holders": int(token_data.get("holders", 0)),
        }
    
    def get_token_recent_trades(self, token_address: str, chain: str, limit: int = 20) -> List[Dict]:
        """获取代币最近交易记录"""
        result = self.run_onchainos([
            "token", "trades",
            "--address", token_address,
            "--chain", chain,
            "--limit", str(limit)
        ])
        
        if not result["success"]:
            print(f"⚠️ 获取代币 {token_address} 交易记录失败: {result['error']}")
            return []
        
        data = result.get("data", {})
        if not data.get("ok") or "data" not in data:
            return []
        
        trades = data["data"]
        formatted_trades = []
        
        for trade in trades:
            try:
                # 解析交易金额
                amount_usd = float(trade.get("amountUSD", 0))
                
                formatted_trades.append({
                    "tx_hash": trade.get("transactionHash", ""),
                    "timestamp": int(trade.get("timestamp", 0)),
                    "amount_usd": amount_usd,
                    "is_buy": trade.get("tradeDirection") == "buy",
                    "price": float(trade.get("price", 0)),
                    "amount_token": float(trade.get("amount", 0)),
                    "trader": trade.get("traderAddress", ""),
                    "trader_tag": trade.get("traderTag", "")
                })
            except Exception as e:
                continue
        
        return formatted_trades
    
    def check_token_safety(self, token_address: str, token_data: Dict) -> Dict:
        """检查代币安全性（简化的安全检查）"""
        safety_score = 100
        issues = []
        
        # 检查是否在白名单中
        chain = token_data.get("chain", "")
        if chain in self.safe_tokens and token_address.lower() in self.safe_tokens[chain]:
            safety_score += 20
            issues.append("✅ 在安全白名单中")
        
        # 检查名称中的风险关键词
        token_symbol = token_data.get("symbol", "").lower()
        
        for pattern in self.risk_patterns:
            if re.search(pattern, token_symbol):
                safety_score -= 25
                issues.append(f"⚠️ 名称包含风险关键词: {pattern}")
                break
        
        # 检查流动性
        liquidity = token_data.get("liquidity", 0)
        if liquidity >= 1000000:  # 100万流动性
            safety_score += 10
            issues.append(f"✅ 流动性充足: ${liquidity:,.0f}")
        elif liquidity >= 500000:
            safety_score += 5
            issues.append(f"⚠️ 流动性一般: ${liquidity:,.0f}")
        else:
            safety_score -= 10
            issues.append(f"🔴 流动性不足: ${liquidity:,.0f}")
        
        # 检查持有者数量
        holders = token_data.get("holders", 0)
        if holders >= 10000:
            safety_score += 10
            issues.append(f"✅ 持有者较多: {holders:,}")
        elif holders >= 1000:
            safety_score += 5
            issues.append(f"⚠️ 持有者一般: {holders:,}")
        elif holders >= 100:
            safety_score += 2
            issues.append(f"⚠️ 持有者较少: {holders:,}")
        else:
            safety_score -= 10
            issues.append(f"🔴 持有者过少: {holders:,}")
        
        # 安全评级
        if safety_score >= 80:
            safety_rating = "🟢 安全"
            is_safe = True
        elif safety_score >= 60:
            safety_rating = "🟡 一般"
            is_safe = True
        elif safety_score >= 40:
            safety_rating = "🟠 风险"
            is_safe = False
        else:
            safety_rating = "🔴 高风险"
            is_safe = False
        
        return {
            "safety_score": safety_score,
            "safety_rating": safety_rating,
            "issues": issues,
            "is_safe": is_safe,
        }
    
    def detect_30min_volume_surge(self, token_key: str, current_volume_30min: float) -> Tuple[bool, float, float]:
        """检测30分钟内交易量激增"""
        cache = self.load_cache()
        volume_history = cache.get("volume_history", {})
        
        current_time = datetime.now(BEIJING_TZ)
        
        if token_key in volume_history:
            # 获取最近的记录（保留最近2小时的记录，即4个30分钟周期）
            recent_records = volume_history[token_key][-4:]  # 最后4个记录
            
            if len(recent_records) >= 2:
                # 计算过去30分钟的平均交易量（排除当前记录）
                recent_volumes = [r["volume30min"] for r in recent_records[:-1]]
                avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
                
                if avg_volume > 0:
                    volume_change = (current_volume_30min - avg_volume) / avg_volume
                    
                    if volume_change >= self.config["volume_surge_threshold"]:
                        return True, volume_change, avg_volume
        
        # 记录当前交易量
        if token_key not in volume_history:
            volume_history[token_key] = []
        
        volume_history[token_key].append({
            "timestamp": current_time.isoformat(),
            "volume30min": current_volume_30min
        })
        
        # 只保留最近2小时的数据（4个30分钟周期）
        if len(volume_history[token_key]) > 4:
            volume_history[token_key] = volume_history[token_key][-4:]
        
        cache["volume_history"] = volume_history
        cache["last_update"] = current_time.isoformat()
        self.save_cache(cache)
        
        return False, 0, 0
    
    def detect_large_trades(self, token_key: str, recent_trades: List[Dict]) -> List[Dict]:
        """检测大额交易"""
        large_trades = []
        large_threshold = self.config["large_trade_threshold"]
        
        for trade in recent_trades:
            amount_usd = trade.get("amount_usd", 0)
            
            if amount_usd >= large_threshold:
                # 标记为大额交易
                trade_copy = trade.copy()
                trade_copy["is_large"] = True
                large_trades.append(trade_copy)
        
        return large_trades
    
    def format_volume_surge_alert(self, token: Dict, price_info: Dict, safety_info: Dict, 
                                 volume_change: float, avg_volume: float) -> str:
        """格式化交易量激增报警信息"""
        symbol = token.get("symbol", "UNKNOWN")
        address = token.get("id", "")
        chain_name = token.get("chain_name", "Unknown")
        short_address = address[:8] + "..." + address[-6:] if len(address) > 14 else address
        
        current_volume_30min = price_info.get("volume_30min", 0)
        market_cap = price_info.get("market_cap", 0)
        liquidity = price_info.get("liquidity", 0)
        price = price_info.get("price", 0)
        price_change_1h = price_info.get("price_change_1h", 0)
        
        alert = f"## ⚡ {chain_name}链代币交易量激增警报\n\n"
        alert += f"**代币**: {symbol}\n"
        alert += f"**合约**: `{short_address}`\n"
        alert += f"**链**: {chain_name}\n"
        alert += f"**时间**: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n"
        alert += f"**监控周期**: 30分钟交易量变化\n\n"
        
        alert += f"### 📊 交易数据\n"
        alert += f"- **当前30分钟交易量**: ${current_volume_30min:,.0f}\n"
        alert += f"- **前30分钟平均交易量**: ${avg_volume:,.0f}\n"
        alert += f"- **交易量增长**: +{volume_change*100:.1f}%\n"
        alert += f"- **24小时交易量**: ${price_info.get('volume_24h', 0):,.0f}\n"
        alert += f"- **当前价格**: ${price:.6f}\n"
        alert += f"- **1小时价格变化**: {price_change_1h:+.2f}%\n"
        alert += f"- **市值**: ${market_cap:,.0f}\n"
        alert += f"- **流动性**: ${liquidity:,.0f}\n\n"
        
        alert += f"### 🛡️ 安全评估\n"
        alert += f"- **安全评级**: {safety_info['safety_rating']}\n"
        alert += f"- **安全分数**: {safety_info['safety_score']}/100\n"
        
        for issue in safety_info['issues'][:5]:  # 最多显示5个问题
            alert += f"- {issue}\n"
        
        # 添加建议
        alert += f"\n### 💡 建议\n"
        if safety_info['is_safe'] and volume_change > 0.5:
            alert += f"🟢 **强烈关注**：30分钟内交易量显著增长，代币相对安全\n"
        elif safety_info['is_safe']:
            alert += f"🟡 **保持关注**：交易量有所增长，代币安全\n"
        else:
            alert += f"🔴 **高度谨慎**：代币存在安全风险\n"
        
        # 添加链接
        alert += f"\n### 🔗 相关链接\n"
        if token.get("chain") == "bsc":
            alert += f"- [BSCScan](https://bscscan.com/address/{address})\n"
        elif token.get("chain") == "ethereum":
            alert += f"- [Etherscan](https://etherscan.io/address/{address})\n"
        elif token.get("chain") == "solana":
            alert += f"- [Solscan](https://solscan.io/token/{address})\n"
        elif token.get("chain") == "base":
            alert += f"- [Basescan](https://basescan.org/address/{address})\n"
        
        return alert
    
    def format_large_trade_alert(self, token: Dict, large_trades: List[Dict]) -> str:
        """格式化大额交易报警信息"""
        symbol = token.get("symbol", "UNKNOWN")
        address = token.get("id", "")
        chain_name = token.get("chain_name", "Unknown")
        short_address = address[:8] + "..." + address[-6:] if len(address) > 14 else address
        
        alert = f"## 💰 {chain_name}链大额交易警报\n\n"
        alert += f"**代币**: {symbol}\n"
        alert += f"**合约**: `{short_address}`\n"
        alert += f"**链**: {chain_name}\n"
        alert += f"**时间**: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n"
        alert += f"**大额交易阈值**: ${self.config['large_trade_threshold']:,}\n\n"
        
        alert += f"### 📊 大额交易详情\n"
        
        for i, trade in enumerate(large_trades[:5], 1):  # 最多显示5笔大额交易
            timestamp = datetime.fromtimestamp(trade.get("timestamp", 0)).strftime('%H:%M:%S') if trade.get("timestamp") else "Unknown"
            direction = "买入" if trade.get("is_buy") else "卖出"
            trader_tag = trade.get("trader_tag", "普通交易者")
            
            alert += f"\n**交易 #{i}**\n"
            alert += f"- **时间**: {timestamp}\n"
            alert += f"- **方向**: {direction}\n"
            alert += f"- **金额**: ${trade.get('amount_usd', 0):,.0f}\n"
            alert += f"- **价格**: ${trade.get('price', 0):.6f}\n"
            alert += f"- **交易者**: {trader_tag}\n"
        
        alert += f"\n### 💡 建议\n"
        alert += f"🔍 **监控重点**: 观察是否有连续大额交易，可能预示大户进场或离场\n"
        alert += f"📈 **市场影响**: 大额交易可能影响短期价格走势\n"
        
        return alert
    
    def send_alert(self, message: str, alert_type: str, token_key: str) -> bool:
        """发送报警（检查重复报警）"""
        history = self.load_alert_history()
        
        # 检查最近是否已报警（避免重复）
        current_time = datetime.now(BEIJING_TZ)
        alert_key = f"{alert_type}_{token_key}"
        
        if alert_key in history["last_alert_time"]:
            last_alert_str = history["last_alert_time"][alert_key]
            last_alert = datetime.fromisoformat(last_alert_str)
            
            # 如果30分钟内已报警过，不再重复
            if (current_time - last_alert) < timedelta(minutes=30):
                print(f"⚠️ {alert_type}报警 30分钟内已发送过，跳过")
                return True
        
        # 发送到Discord
        result = self.run_openclaw([
            "message", "send",
            "--channel", "discord",
            "--target", DISCORD_CHANNEL,
            "--message", message
        ])
        
        # 更新报警历史
        if result["success"]:
            history["last_alert_time"][alert_key] = current_time.isoformat()
            self.save_alert_history(history)
        
        return result["success"]
    
    def monitor_multi_chain(self):
        """监控多链代币"""
        print(f"\n{'='*80}")
        print(f"🔍 多链代币实时监控启动 (OKX API)")
        print(f"⏰ {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 监控链: {', '.join(self.config['monitor_chains'])}")
        print(f"📈 配置: 30分钟监控 | 增长>{self.config['volume_surge_threshold']*100:.0f}% | 市值>${self.config['min_market_cap']:,} | 大额交易>${self.config['large_trade_threshold']:,}")
        print(f"{'='*80}\n")
        
        total_alerts = 0
        
        # 遍历每个链
        for chain in self.config["monitor_chains"]:
            print(f"\n🌐 开始监控 {self.chains.get(chain, {}).get('name', chain)} 链...")
            
            # 获取该链的热门代币
            tokens = self.get_top_tokens_by_chain(chain, limit=self.config["max_tokens_per_chain"])
            
            if not tokens:
                print(f"❌ 无法获取{self.chains.get(chain, {}).get('name', chain)}链数据，跳过")
                continue
            
            chain_alerts = 0
            
            for i, token in enumerate(tokens, 1):
                address = token.get("id", "")
                symbol = token.get("symbol", "UNKNOWN")
                
                if not address or address == "0x0":
                    continue
                
                print(f"[{chain[:3].upper()}:{i}/{len(tokens)}] 分析 {symbol} ({address[:8]}...)")
                
                # 获取详细价格信息
                price_info = self.get_token_price_info(address, chain)
                
                if not price_info:
                    print(f"   ❌ 无法获取价格信息")
                    continue
                
                current_volume_30min = price_info.get("volume_30min", 0)
                
                if current_volume_30min < self.config["min_volume_30min"]:
                    print(f"   ⏭️ 30分钟交易量不足: ${current_volume_30min:,.0f}")
                    continue
                
                print(f"   📊 30分钟交易量: ${current_volume_30min:,.0f}")
                
                # 检查市值
                market_cap = price_info.get("market_cap", 0)
                
                if market_cap < self.config["min_market_cap"]:
                    print(f"   ⏭️ 市值不足: ${market_cap:,.0f} < ${self.config['min_market_cap']:,}")
                    continue
                
                print(f"   💰 市值: ${market_cap:,.0f}")
                
                # 检查安全性
                safety_info = self.check_token_safety(address, {**token, **price_info})
                
                if not safety_info["is_safe"]:
                    print(f"   ⚠️ 代币不安全: {safety_info['safety_rating']} ({safety_info['safety_score']}/100)")
                    continue
                
                print(f"   🛡️ 代币安全: {safety_info['safety_rating']} ({safety_info['safety_score']}/100)")
                
                # 检测30分钟内交易量激增
                token_key = f"{chain}_{address}"
                has_surge, volume_change, avg_volume = self.detect_30min_volume_surge(token_key, current_volume_30min)
                
                volume_alerts = 0
                if has_surge and volume_change >= self.config["volume_surge_threshold"]:
                    print(f"   🚨 发现30分钟内交易量激增: +{volume_change*100:.1f}%")
                    
                    # 生成交易量激增报警
                    alert_message = self.format_volume_surge_alert(token, price_info, safety_info, volume_change, avg_volume)
                    
                    # 发送报警
                    print(f"   📤 发送交易量激增报警...")
                    if self.send_alert(alert_message, "volume_surge", token_key):
                        volume_alerts += 1
                        chain_alerts += 1
                        print(f"   ✅ 报警发送成功")
                    else:
                        print(f"   ❌ 报警发送失败")
                
                # 获取最近交易记录，检测大额交易
                print(f"   🔍 检查大额交易...")
                recent_trades = self.get_token_recent_trades(address, chain, limit=10)
                
                if recent_trades:
                    large_trades = self.detect_large_trades(token_key, recent_trades)
                    
                    if large_trades:
                        print(f"   💰 发现{len(large_trades)}笔大额交易（>${self.config['large_trade_threshold']:,}）")
                        
                        # 生成大额交易报警
                        alert_message = self.format_large_trade_alert(token, large_trades)
                        
                        # 发送报警
                        print(f"   📤 发送大额交易报警...")
                        if self.send_alert(alert_message, "large_trade", token_key):
                            chain_alerts += 1
                            print(f"   ✅ 报警发送成功")
                        else:
                            print(f"   ❌ 报警发送失败")
                
                # 避免API速率限制
                delay = self.config.get("api_delay_seconds", 2)
                time.sleep(delay)
            
            total_alerts += chain_alerts
            print(f"✅ {self.chains.get(chain, {}).get('name', chain)}链监控完成，发送{chain_alerts}个警报")
        
        print(f"\n{'='*80}")
        print(f"✅ 多链监控完成")
        print(f"📊 监控链数: {len(self.config['monitor_chains'])}")
        print(f"🚨 总警报数: {total_alerts} 个")
        print(f"⏰ 下次监控: {datetime.now(BEIJING_TZ) + timedelta(minutes=self.config['check_interval_minutes']):%H:%M}")
        print(f"{'='*80}")
        
        return total_alerts > 0


def main():
    """主函数"""
    monitor = MultiChainTokenMonitor()
    monitor.monitor_multi_chain()


if __name__ == "__main__":
    main()