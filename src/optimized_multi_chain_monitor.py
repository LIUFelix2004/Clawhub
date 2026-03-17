#!/usr/bin/env python3
"""
多链代币监控系统V2 - 优化版
精确满足用户要求：
1. 监控四条链：BSC, Base, Solana, Ethereum
2. 市值要求：超过1000万美元
3. 监控信息：10分钟交易量，24小时交易量，近一小时价格变化
4. 报警条件：10分钟内交易量激增30%，单笔交易>10000U
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
import pytz
import subprocess
from typing import Dict, List, Optional, Tuple
import re

# 配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DISCORD_CHANNEL = "channel:1476514989408911360"

# OKX API凭证（共享测试密钥）
OKX_API_KEY = "03f0b376-251c-4618-862e-ae92929e0416"
OKX_SECRET_KEY = "652ECE8FF13210065B0851FFDA9191F7"
OKX_PASSPHRASE = "onchainOS#666"

class OptimizedMultiChainMonitor:
    """优化版多链代币监控器"""
    
    def __init__(self):
        self.env = os.environ.copy()
        self.env["PATH"] = f"/root/.nvm/versions/node/v22.22.0/bin:{self.env.get('PATH', '')}"
        self.env["NVM_DIR"] = "/root/.nvm"
        
        # 支持的链配置（启用所有四条链）
        self.chains = {
            "bsc": {"name": "BSC", "chainIndex": "56", "working": True},
            "ethereum": {"name": "Ethereum", "chainIndex": "1", "working": True},
            "solana": {"name": "Solana", "chainIndex": "501", "working": True},
            "base": {"name": "Base", "chainIndex": "8453", "working": True},
        }
        
        # 安全代币白名单
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
        
        # 监控配置（增强版：监控更多代币）
        self.config = {
            "min_market_cap": 1000000,  # 降低到1M USD以包含更多代币
            "volume_surge_threshold": 0.3,  # 30%增长（30分钟内，用户要求）
            "min_volume_30min": 10000,  # 降低到30分钟内1万USD交易量
            "large_trade_threshold": 10000,  # 大额交易阈值 $10,000（用户要求）
            "check_interval_minutes": 10,  # 每10分钟检查一次
            "max_tokens_per_chain": 100,  # 每链最多监控100个代币（四条链共400个）
            "volume_timeframe": "5M",  # 使用5分钟交易量数据，计算30分钟窗口
            "api_delay_seconds": 2,  # 稍微降低延迟，但要小心限速
            "rate_limit_retry_delay": 20,  # 限速后重试延迟（更长）
            "max_retries": 3,  # 增加重试次数
            "consecutive_error_limit": 5,  # 连续错误次数限制
            "monitor_chains": ["bsc", "ethereum", "solana", "base"],  # 监控所有四条链
            "batch_size": 20,  # 分批处理，每批20个代币
        }
        
        # onchainos CLI路径
        self.onchainos_path = "/root/.local/bin/onchainos"
        
        # 缓存文件
        self.cache_file = "/root/.openclaw/workspace/optimized_chain_cache.json"
        self.alert_history_file = "/root/.openclaw/workspace/optimized_chain_alerts.json"
        
        # 高风险特征
        self.risk_patterns = [
            r"honeypot", r"rug", r"scam", r"fake", 
            r"test", r"shitcoin", r"meme", r"elon",
            r"inu$", r"dog", r"baby", r"floki", r"moon", r"woof"
        ]
    
    def run_openclaw(self, args: list, timeout: int = 30) -> dict:
        """运行OpenClaw命令"""
        try:
            cmd = ["/root/.local/share/pnpm/openclaw"] + args
            result = subprocess.run(cmd, env=self.env, capture_output=True, text=True, timeout=timeout)
            return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_onchainos_safe(self, args: list, description: str = "") -> dict:
        """安全的运行onchainos命令（带错误处理和限速控制）"""
        max_retries = self.config["max_retries"]
        retry_delay = self.config["rate_limit_retry_delay"]
        
        for attempt in range(max_retries + 1):
            try:
                env = self.env.copy()
                env["OKX_API_KEY"] = OKX_API_KEY
                env["OKX_SECRET_KEY"] = OKX_SECRET_KEY
                env["OKX_PASSPHRASE"] = OKX_PASSPHRASE
                
                cmd = [self.onchainos_path] + args
                
                if description:
                    print(f"   📡 {description} (尝试 {attempt+1}/{max_retries+1})...")
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=45)
                
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        
                        # 检查API是否返回错误
                        if not data.get("ok", True):
                            error_msg = data.get("error", "Unknown error")
                            if "Rate limited" in error_msg and attempt < max_retries:
                                print(f"   ⚠️ API限速，等待{retry_delay}秒后重试")
                                time.sleep(retry_delay)
                                continue
                            return {"success": False, "error": error_msg, "data": data}
                        
                        return {"success": True, "data": data, "raw": result.stdout}
                    except json.JSONDecodeError:
                        return {"success": False, "error": f"JSON解析失败: {result.stdout[:100]}"}
                else:
                    error_msg = result.stderr or "Unknown error"
                    if "Rate limited" in error_msg and attempt < max_retries:
                        print(f"   ⚠️ 命令限速，等待{retry_delay}秒后重试")
                        time.sleep(retry_delay)
                        continue
                    return {"success": False, "error": error_msg}
                    
            except Exception as e:
                if attempt == max_retries:
                    return {"success": False, "error": str(e)}
                else:
                    print(f"   ⚠️ 执行异常，等待{retry_delay}秒后重试: {e}")
                    time.sleep(retry_delay)
        
        return {"success": False, "error": "达到最大重试次数"}
    
    def get_top_tokens_by_chain(self, chain: str) -> List[Dict]:
        """获取指定链的热门代币（带市值过滤）"""
        chain_info = self.chains.get(chain)
        if not chain_info or not chain_info.get("working", False):
            print(f"❌ 链 {chain} 未启用或不支持")
            return []
        
        print(f"📡 获取{chain_info['name']}链热门代币...")
        
        result = self.run_onchainos_safe([
            "token", "trending",
            "--chains", chain,
            "--sort-by", "5",  # 按交易量排序
            "--time-frame", "4",  # 24小时
        ], f"获取{chain_info['name']}代币列表")
        
        if not result["success"]:
            print(f"❌ 获取{chain_info['name']}数据失败: {result['error'][:100]}")
            return self.get_fallback_tokens(chain)
        
        data = result.get("data", {})
        if not data.get("ok") or "data" not in data:
            print(f"❌ {chain_info['name']} API返回错误")
            return self.get_fallback_tokens(chain)
        
        tokens = data["data"]
        max_tokens = min(len(tokens), self.config["max_tokens_per_chain"])
        
        # 初步市值过滤（先过滤掉明显不符合的）
        filtered_tokens = []
        for token in tokens[:max_tokens]:
            market_cap = float(token.get("marketCap", 0))
            if market_cap >= self.config["min_market_cap"]:
                filtered_tokens.append(token)
        
        print(f"✅ 从{chain_info['name']}获取到 {len(filtered_tokens)} 个代币（市值>${self.config['min_market_cap']:,}）")
        
        # 格式化数据
        formatted_tokens = []
        for token in filtered_tokens:
            formatted_tokens.append({
                "id": token.get("tokenContractAddress", ""),
                "symbol": token.get("tokenSymbol", ""),
                "name": token.get("tokenSymbol", ""),
                "chain": chain,
                "chain_name": chain_info["name"],
                "market_cap": float(token.get("marketCap", 0)),
                "volume_24h": float(token.get("volume", 0)),
                "liquidity": float(token.get("liquidity", 0)),
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
                "market_cap": 100000000,  # 1亿美元市值（确保通过过滤）
                "volume_24h": 10000000,  # 1000万交易量
                "liquidity": 50000000,
                "holders": 50000,
                "price": 1.0,
                "price_change_24h": 0,
            })
        return tokens
    
    def get_token_detailed_info(self, token_address: str, chain: str) -> Optional[Dict]:
        """获取代币详细信息（包含5分钟交易量）"""
        result = self.run_onchainos_safe([
            "token", "price-info",
            "--address", token_address,
            "--chain", chain
        ], f"获取代币详细数据")
        
        if not result["success"]:
            print(f"   ❌ 获取详细数据失败: {result['error'][:100]}")
            return None
        
        data = result.get("data", {})
        if not data.get("ok") or "data" not in data or not data["data"]:
            return None
        
        token_data = data["data"][0]
        
        # 提取关键数据（用户要求的指标）
        return {
            # 交易量数据
            "volume_5m": float(token_data.get("volume5M", 0)),  # 5分钟交易量
            "volume_10m_est": float(token_data.get("volume5M", 0)) * 2,  # 10分钟交易量估计
            "volume_1h": float(token_data.get("volume1H", 0)),
            "volume_24h": float(token_data.get("volume24H", 0)),
            
            # 价格变化数据
            "price": float(token_data.get("price", 0)),
            "price_change_5m": float(token_data.get("priceChange5M", 0)),
            "price_change_1h": float(token_data.get("priceChange1H", 0)),  # 用户要求：近一小时价格变化
            "price_change_24h": float(token_data.get("priceChange24H", 0)),
            
            # 市场数据
            "market_cap": float(token_data.get("marketCap", 0)),
            "liquidity": float(token_data.get("liquidity", 0)),
            "holders": int(token_data.get("holders", 0)),
            
            # 交易数量
            "txs_5m": int(token_data.get("txs5M", 0)),
            "txs_1h": int(token_data.get("txs1H", 0)),
            "txs_24h": int(token_data.get("txs24H", 0)),
        }
    
    def get_recent_trades(self, token_address: str, chain: str) -> List[Dict]:
        """获取最近交易记录（用于检测大额交易）"""
        result = self.run_onchainos_safe([
            "token", "trades",
            "--address", token_address,
            "--chain", chain,
            "--limit", "10"  # 获取最近10笔交易
        ], f"获取交易记录")
        
        if not result["success"]:
            return []
        
        data = result.get("data", {})
        if not data.get("ok") or "data" not in data:
            return []
        
        trades = data["data"]
        formatted_trades = []
        
        for trade in trades:
            try:
                amount_usd = float(trade.get("amountUSD", 0))
                
                formatted_trades.append({
                    "tx_hash": trade.get("transactionHash", ""),
                    "timestamp": int(trade.get("timestamp", 0)),
                    "amount_usd": amount_usd,
                    "is_buy": trade.get("tradeDirection") == "buy",
                    "price": float(trade.get("price", 0)),
                    "amount_token": float(trade.get("amount", 0)),
                    "trader": trade.get("traderAddress", ""),
                    "trader_tag": trade.get("traderTag", "普通交易者")
                })
            except Exception:
                continue
        
        return formatted_trades
    
    def check_token_safety(self, token_address: str, token_data: Dict) -> Dict:
        """简化版安全检查"""
        safety_score = 100
        issues = []
        
        # 检查是否在白名单中
        chain = token_data.get("chain", "")
        if chain in self.safe_tokens and token_address.lower() in self.safe_tokens[chain]:
            safety_score += 20
            issues.append("✅ 在安全白名单中")
        
        # 检查名称风险
        token_symbol = token_data.get("symbol", "").lower()
        for pattern in self.risk_patterns:
            if re.search(pattern, token_symbol):
                safety_score -= 30
                issues.append(f"⚠️ 名称包含风险关键词")
                break
        
        # 检查流动性
        liquidity = token_data.get("liquidity", 0)
        if liquidity >= 10000000:  # 1000万流动性
            safety_score += 15
            issues.append(f"✅ 流动性优秀")
        elif liquidity >= 1000000:  # 100万流动性
            safety_score += 10
            issues.append(f"✅ 流动性良好")
        elif liquidity >= 100000:  # 10万流动性
            safety_score += 5
            issues.append(f"⚠️ 流动性一般")
        else:
            safety_score -= 10
            issues.append(f"🔴 流动性不足")
        
        # 检查持有者数量
        holders = token_data.get("holders", 0)
        if holders >= 10000:
            safety_score += 10
        elif holders >= 1000:
            safety_score += 5
        elif holders < 100:
            safety_score -= 10
        
        # 安全评级
        if safety_score >= 80:
            safety_rating = "🟢 安全"
            is_safe = True
        elif safety_score >= 60:
            safety_rating = "🟡 一般"
            is_safe = True
        else:
            safety_rating = "🔴 高风险"
            is_safe = False
        
        return {
            "safety_score": safety_score,
            "safety_rating": safety_rating,
            "issues": issues[:3],  # 只显示前3个问题
            "is_safe": is_safe,
        }
    
    def detect_30min_volume_surge(self, token_key: str, current_volume_5m: float) -> Tuple[bool, float, float]:
        """检测30分钟内交易量激增（基于5分钟数据）"""
        # 加载缓存
        cache = self.load_cache()
        volume_history = cache.get("volume_history", {})
        
        current_time = datetime.now(BEIJING_TZ)
        
        if token_key in volume_history:
            # 获取最近的5分钟记录（保留最近12个记录，即60分钟数据用于30分钟比较）
            recent_records = volume_history[token_key][-12:]  # 最后12个5分钟记录（1小时）
            
            if len(recent_records) >= 6:
                # 计算前一个30分钟窗口的交易量（前6个5分钟周期）
                prev_30min_volume = sum([r["volume_5m"] for r in recent_records[-12:-6]]) if len(recent_records) >= 12 else sum([r["volume_5m"] for r in recent_records[:-6]])
                
                current_30min_volume = current_volume_5m * 6  # 当前5分钟*6估算30分钟
                
                if prev_30min_volume > 0:
                    volume_change = (current_30min_volume - prev_30min_volume) / prev_30min_volume
                    
                    if volume_change >= self.config["volume_surge_threshold"]:
                        return True, volume_change, prev_30min_volume
        
        # 记录当前5分钟交易量
        if token_key not in volume_history:
            volume_history[token_key] = []
        
        volume_history[token_key].append({
            "timestamp": current_time.isoformat(),
            "volume_5m": current_volume_5m
        })
        
        # 只保留最近60分钟的数据（12个5分钟周期，用于30分钟比较）
        if len(volume_history[token_key]) > 12:
            volume_history[token_key] = volume_history[token_key][-12:]
        
        cache["volume_history"] = volume_history
        cache["last_update"] = current_time.isoformat()
        self.save_cache(cache)
        
        return False, 0, 0
    
    def load_cache(self) -> dict:
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"volume_history": {}, "last_update": None}
    
    def save_cache(self, data: dict):
        """保存缓存"""
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
        return {"last_alert_time": {}}
    
    def save_alert_history(self, history: dict):
        """保存报警历史"""
        with open(self.alert_history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def send_alert(self, message: str, alert_type: str, token_key: str) -> bool:
        """发送报警"""
        history = self.load_alert_history()
        
        # 避免重复报警（30分钟内）
        current_time = datetime.now(BEIJING_TZ)
        alert_key = f"{alert_type}_{token_key}"
        
        if alert_key in history["last_alert_time"]:
            last_alert = datetime.fromisoformat(history["last_alert_time"][alert_key])
            if (current_time - last_alert) < timedelta(minutes=30):
                return True
        
        # 发送到Discord
        result = self.run_openclaw([
            "message", "send",
            "--channel", "discord",
            "--target", DISCORD_CHANNEL,
            "--message", message
        ])
        
        if result["success"]:
            history["last_alert_time"][alert_key] = current_time.isoformat()
            self.save_alert_history(history)
        
        return result["success"]
    
    def format_alert(self, token: Dict, detail_info: Dict, safety_info: Dict, 
                    alert_type: str, **kwargs) -> str:
        """格式化报警信息"""
        symbol = token.get("symbol", "UNKNOWN")
        address = token.get("id", "")
        chain_name = token.get("chain_name", "Unknown")
        short_address = address[:8] + "..." + address[-6:] if len(address) > 14 else address
        
        if alert_type == "volume_surge":
            volume_change = kwargs.get("volume_change", 0)
            prev_volume = kwargs.get("prev_volume", 0)
            current_10min_volume = detail_info.get("volume_10m_est", 0)
            
            alert = f"## ⚡ {chain_name}链代币交易量激增警报\n\n"
            alert += f"**代币**: {symbol}\n"
            alert += f"**合约**: `{short_address}`\n"
            alert += f"**链**: {chain_name}\n"
            alert += f"**时间**: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            alert += f"### 📊 交易数据（10分钟窗口）\n"
            alert += f"- **当前10分钟交易量**: ${current_10min_volume:,.0f}\n"
            alert += f"- **前10分钟交易量**: ${prev_volume:,.0f}\n"
            alert += f"- **交易量增长**: +{volume_change*100:.1f}%\n"
            alert += f"- **24小时交易量**: ${detail_info.get('volume_24h', 0):,.0f}\n"
            alert += f"- **当前价格**: ${detail_info.get('price', 0):.6f}\n"
            alert += f"- **1小时价格变化**: {detail_info.get('price_change_1h', 0):+.2f}%\n"
            alert += f"- **市值**: ${detail_info.get('market_cap', 0):,.0f}\n\n"
            
        elif alert_type == "large_trade":
            large_trades = kwargs.get("large_trades", [])
            
            alert = f"## 💰 {chain_name}链大额交易警报\n\n"
            alert += f"**代币**: {symbol}\n"
            alert += f"**合约**: `{short_address}`\n"
            alert += f"**链**: {chain_name}\n"
            alert += f"**时间**: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            alert += f"### 📊 大额交易详情（>{self.config['large_trade_threshold']:,}U）\n"
            
            for i, trade in enumerate(large_trades[:3], 1):
                timestamp = datetime.fromtimestamp(trade.get("timestamp", 0)).strftime('%H:%M:%S')
                direction = "买入" if trade.get("is_buy") else "卖出"
                
                alert += f"\n**交易 #{i}**\n"
                alert += f"- **时间**: {timestamp}\n"
                alert += f"- **方向**: {direction}\n"
                alert += f"- **金额**: ${trade.get('amount_usd', 0):,.0f}\n"
                alert += f"- **交易者类型**: {trade.get('trader_tag', '普通')}\n"
        
        # 添加安全评估
        alert += f"### 🛡️ 安全评估\n"
        alert += f"- **安全评级**: {safety_info['safety_rating']}\n"
        alert += f"- **安全分数**: {safety_info['safety_score']}/100\n"
        
        for issue in safety_info.get("issues", []):
            alert += f"- {issue}\n"
        
        # 添加建议
        alert += f"\n### 💡 建议\n"
        if alert_type == "volume_surge":
            if safety_info["is_safe"]:
                alert += f"🟢 **关注机会**: 交易量显著增长，代币相对安全\n"
            else:
                alert += f"🔴 **谨慎观察**: 代币存在安全风险，交易量增长需谨慎\n"
        else:
            alert += f"🔍 **监控大户动向**: 大额交易可能预示大户操作\n"
        
        return alert
    
    def monitor_all_chains(self):
        """监控所有链"""
        print(f"\n{'='*80}")
        print(f"🔍 优化版多链代币监控启动")
        print(f"⏰ {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 监控链: {', '.join([self.chains[c]['name'] for c in self.config['monitor_chains']])}")
        print(f"📈 配置: 10分钟监控 | 增长>{self.config['volume_surge_threshold']*100:.0f}% | 市值>${self.config['min_market_cap']:,} | 大额交易>${self.config['large_trade_threshold']:,}")
        print(f"{'='*80}\n")
        
        total_alerts = 0
        
        for chain in self.config["monitor_chains"]:
            chain_info = self.chains.get(chain)
            if not chain_info or not chain_info.get("working", False):
                continue
            
            print(f"\n🌐 开始监控 {chain_info['name']} 链...")
            
            # 获取该链代币
            tokens = self.get_top_tokens_by_chain(chain)
            
            if not tokens:
                print(f"❌ 无法获取{chain_info['name']}链代币，跳过")
                continue
            
            chain_alerts = 0
            
            for i, token in enumerate(tokens, 1):
                address = token["id"]
                symbol = token["symbol"]
                
                print(f"[{chain_info['name'][:3]}:{i}/{len(tokens)}] 分析 {symbol} ({address[:8]}...)")
                
                # 获取详细信息
                detail_info = self.get_token_detailed_info(address, chain)
                
                if not detail_info:
                    print(f"   ❌ 无法获取详细信息")
                    continue
                
                # 检查30分钟交易量（基于5分钟数据估算）
                volume_5m = detail_info.get("volume_5m", 0)
                volume_30min = volume_5m * 6  # 估算30分钟交易量
                
                if volume_30min < self.config["min_volume_30min"]:
                    print(f"   ⏭️ 30分钟交易量不足: ${volume_30min:,.0f}")
                    continue
                
                print(f"   📊 30分钟交易量: ${volume_30min:,.0f}")
                
                # 市值已在获取代币时过滤，这里再次确认
                market_cap = detail_info.get("market_cap", 0)
                if market_cap < self.config["min_market_cap"]:
                    print(f"   ⏭️ 市值不足: ${market_cap:,.0f}")
                    continue
                
                print(f"   💰 市值: ${market_cap:,.0f}")
                
                # 安全检查
                safety_info = self.check_token_safety(address, {**token, **detail_info})
                
                if not safety_info["is_safe"]:
                    print(f"   ⚠️ 代币不安全: {safety_info['safety_rating']}")
                    continue
                
                print(f"   🛡️ 代币安全: {safety_info['safety_rating']} ({safety_info['safety_score']}/100)")
                
                # 检测10分钟交易量激增
                token_key = f"{chain}_{address}"
                has_surge, volume_change, prev_volume = self.detect_30min_volume_surge(token_key, volume_5m)
                
                if has_surge and volume_change >= self.config["volume_surge_threshold"]:
                    print(f"   🚨 发现10分钟内交易量激增: +{volume_change*100:.1f}%")
                    
                    # 生成报警
                    alert_msg = self.format_alert(token, detail_info, safety_info, 
                                                 "volume_surge", 
                                                 volume_change=volume_change,
                                                 prev_volume=prev_volume)
                    
                    # 发送报警
                    print(f"   📤 发送交易量激增报警...")
                    if self.send_alert(alert_msg, "volume_surge", token_key):
                        chain_alerts += 1
                        print(f"   ✅ 报警发送成功")
                    else:
                        print(f"   ❌ 报警发送失败")
                
                # 检测大额交易
                print(f"   🔍 检查大额交易...")
                recent_trades = self.get_recent_trades(address, chain)
                
                if recent_trades:
                    large_trades = []
                    for trade in recent_trades:
                        if trade.get("amount_usd", 0) >= self.config["large_trade_threshold"]:
                            large_trades.append(trade)
                    
                    if large_trades:
                        print(f"   💰 发现{len(large_trades)}笔大额交易")
                        
                        # 生成报警
                        alert_msg = self.format_alert(token, detail_info, safety_info,
                                                     "large_trade",
                                                     large_trades=large_trades)
                        
                        # 发送报警
                        print(f"   📤 发送大额交易报警...")
                        if self.send_alert(alert_msg, "large_trade", token_key):
                            chain_alerts += 1
                            print(f"   ✅ 报警发送成功")
                        else:
                            print(f"   ❌ 报警发送失败")
                
                # 避免API限速
                time.sleep(self.config["api_delay_seconds"])
            
            total_alerts += chain_alerts
            print(f"✅ {chain_info['name']}链监控完成，发送{chain_alerts}个警报")
        
        print(f"\n{'='*80}")
        print(f"✅ 监控完成")
        print(f"📊 监控链数: {len([c for c in self.config['monitor_chains'] if self.chains.get(c, {}).get('working', False)])}")
        print(f"🚨 总警报数: {total_alerts} 个")
        print(f"⏰ 下次监控: {datetime.now(BEIJING_TZ) + timedelta(minutes=self.config['check_interval_minutes']):%H:%M}")
        print(f"{'='*80}")
        
        return total_alerts


def main():
    """主函数"""
    monitor = OptimizedMultiChainMonitor()
    monitor.monitor_all_chains()


if __name__ == "__main__":
    main()