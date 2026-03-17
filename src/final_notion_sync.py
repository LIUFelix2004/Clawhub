#!/usr/bin/env python3
"""
最终Notion同步脚本 - 使用发现的属性名同步数据
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# 北京时区
BEIJING_TZ = datetime.now().astimezone().tzinfo

class FinalNotionSync:
    def __init__(self, database_id: str = None):
        self.api_key = self.load_notion_key()
        self.database_id = database_id or os.environ.get("NOTION_DATABASE_ID")
        
        if not self.database_id:
            print("❌ 未提供数据库ID")
            print("请设置环境变量: export NOTION_DATABASE_ID='your_database_id'")
            sys.exit(1)
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2025-09-03",
            "Content-Type": "application/json"
        }
        
        # 发现的属性映射（根据数据库实际属性名）
        self.property_mapping = {
            "name": "代币名称",           # Title类型
            "symbol": "代币符号",         # Rich text类型
            "chain": "Chain",             # Select类型（选项：BSC, Ethereum, Solana, Base）
            "address": "合约地址",        # Rich text类型
            "market_cap": "市值",         # Number类型
            "price": "价格",              # Number类型
            "status": "Status",           # Select类型（选项：Active, Watching, Inactive）
            "last_alert": "LastAlert"     # Select类型（选项：None, Volume Surge, Large Trade, High Risk）
        }
        
        print(f"🔗 使用数据库ID: {self.database_id}")
        print(f"📋 属性映射配置:")
        for key, value in self.property_mapping.items():
            print(f"   {key:12} → {value}")
    
    def load_notion_key(self) -> str:
        """加载Notion API密钥"""
        config_path = os.path.expanduser("~/.config/notion/api_key")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                key = f.read().strip()
                if key.startswith("ntn_") or key.startswith("secret_"):
                    return key
        
        env_key = os.environ.get("NOTION_API_KEY")
        if env_key and (env_key.startswith("ntn_") or env_key.startswith("secret_")):
            return env_key
        
        print("❌ 未找到有效的Notion API密钥")
        sys.exit(1)
    
    def test_connection(self) -> bool:
        """测试连接和属性映射"""
        print(f"\n🔍 测试连接和属性映射...")
        
        try:
            # 测试创建简单页面
            properties = {
                self.property_mapping["name"]: {"title": [{"text": {"content": "连接测试代币"}}]},
                self.property_mapping["symbol"]: {"rich_text": [{"text": {"content": "TEST"}}]},
                self.property_mapping["chain"]: {"select": {"name": "BSC"}},
                self.property_mapping["address"]: {"rich_text": [{"text": {"content": "0xTEST..."}}]},
            }
            
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json={
                    "parent": {"database_id": self.database_id},
                    "properties": properties
                },
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"✅ 连接测试成功！")
                page_info = response.json()
                print(f"   测试页面ID: {page_info.get('id')}")
                return True
            else:
                print(f"❌ 连接测试失败: {response.status_code}")
                print(f"   错误: {response.text[:200]}")
                
                # 尝试不使用select属性
                print(f"\n🔧 尝试简化测试（不使用select属性）...")
                simple_properties = {
                    self.property_mapping["name"]: {"title": [{"text": {"content": "简化测试"}}]},
                    self.property_mapping["symbol"]: {"rich_text": [{"text": {"content": "SIM"}}]},
                }
                
                simple_response = requests.post(
                    "https://api.notion.com/v1/pages",
                    headers=self.headers,
                    json={
                        "parent": {"database_id": self.database_id},
                        "properties": simple_properties
                    },
                    timeout=15
                )
                
                if simple_response.status_code == 200:
                    print(f"✅ 简化测试成功！")
                    print(f"   ⚠️ Select属性可能选项不正确")
                    return True
                else:
                    print(f"❌ 简化测试也失败: {simple_response.text[:200]}")
                    return False
        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
            return False
    
    def load_monitor_data(self) -> Dict:
        """加载监控数据"""
        cache_path = "/root/.openclaw/workspace/optimized_chain_cache.json"
        
        if not os.path.exists(cache_path):
            print(f"❌ 监控缓存文件不存在: {cache_path}")
            return {"tokens": []}
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            volume_history = cache_data.get("volume_history", {})
            tokens = []
            
            print(f"📊 加载监控数据...")
            print(f"   找到 {len(volume_history)} 个代币的历史数据")
            
            # 转换数据结构
            for token_key, history in volume_history.items():
                # token_key格式: chain:symbol:address 或 bsc_0x...
                if ":" in token_key:
                    parts = token_key.split(":")
                    if len(parts) >= 3:
                        chain = parts[0]
                        symbol = parts[1]
                        address = parts[2]
                    else:
                        continue
                else:
                    # 格式: bsc_0xe6df05ce8c8301223373cf5b969afcb1498c5528
                    if token_key.startswith("bsc_"):
                        chain = "BSC"
                        symbol = "UNKNOWN"
                        address = token_key[4:] if len(token_key) > 4 else "0x"
                    elif token_key.startswith("eth_"):
                        chain = "Ethereum"
                        symbol = "UNKNOWN"
                        address = token_key[4:] if len(token_key) > 4 else "0x"
                    else:
                        chain = "unknown"
                        symbol = "UNKNOWN"
                        address = token_key
                
                # 获取最新的数据
                latest_volume = 0
                latest_timestamp = datetime.now(BEIJING_TZ).isoformat()
                
                if history and isinstance(history, list):
                    for entry in reversed(history):
                        if isinstance(entry, dict):
                            latest_volume = entry.get("volume_5m", 0)
                            latest_timestamp = entry.get("timestamp", latest_timestamp)
                            break
                
                token_data = {
                    "symbol": symbol if symbol != "UNKNOWN" else f"TOKEN_{len(tokens)}",
                    "chain": chain,
                    "address": address,
                    "short_address": address[:8] + "..." + address[-6:] if len(address) > 14 else address,
                    "market_cap": 10000000,  # 默认值，实际应从其他API获取
                    "price": 1.0,            # 默认值
                    "volume_24h": latest_volume * 288,  # 估算24小时交易量
                    "latest_volume": latest_volume,
                    "latest_timestamp": latest_timestamp,
                    "safety_score": 50,      # 默认安全分
                    "status": "Watching",    # 默认状态
                    "last_alert": "None"     # 默认无警报
                }
                
                tokens.append(token_data)
            
            return {"tokens": tokens}
        
        except Exception as e:
            print(f"❌ 加载监控数据失败: {e}")
            return {"tokens": []}
    
    def create_token_page(self, token_data: Dict) -> bool:
        """创建代币页面"""
        symbol = token_data.get("symbol", "UNKNOWN")
        chain = token_data.get("chain", "unknown").upper()
        
        # 构建属性
        properties = {}
        
        # 代币名称 (Title)
        if "name" in self.property_mapping:
            properties[self.property_mapping["name"]] = {
                "title": [{"text": {"content": f"{symbol} ({chain})"}}]
            }
        
        # 代币符号 (Rich text)
        if "symbol" in self.property_mapping:
            properties[self.property_mapping["symbol"]] = {
                "rich_text": [{"text": {"content": symbol}}]
            }
        
        # 链 (Select) - 映射到数据库中的选项
        if "chain" in self.property_mapping:
            # 映射链名称到数据库选项
            chain_mapping = {
                "BSC": "BSC",
                "ETHEREUM": "Ethereum",
                "SOLANA": "Solana",
                "BASE": "Base",
                "ETH": "Ethereum",
                "SOL": "Solana"
            }
            db_chain = chain_mapping.get(chain, "BSC")
            properties[self.property_mapping["chain"]] = {
                "select": {"name": db_chain}
            }
        
        # 地址 (Rich text)
        if "address" in self.property_mapping:
            address = token_data.get("address", "")
            short_addr = token_data.get("short_address", address[:8] + "..." + address[-6:] if len(address) > 14 else address)
            properties[self.property_mapping["address"]] = {
                "rich_text": [{"text": {"content": short_addr}}]
            }
        
        # 市值 (Number)
        if "market_cap" in self.property_mapping:
            market_cap = token_data.get("market_cap", 0)
            if market_cap:
                properties[self.property_mapping["market_cap"]] = {
                    "number": market_cap
                }
        
        # 价格 (Number)
        if "price" in self.property_mapping:
            price = token_data.get("price", 0)
            if price:
                properties[self.property_mapping["price"]] = {
                    "number": price
                }
        
        # 状态 (Select)
        if "status" in self.property_mapping:
            status = token_data.get("status", "Watching")
            properties[self.property_mapping["status"]] = {
                "select": {"name": status}
            }
        
        # 最后警报 (Select)
        if "last_alert" in self.property_mapping:
            last_alert = token_data.get("last_alert", "None")
            properties[self.property_mapping["last_alert"]] = {
                "select": {"name": last_alert}
            }
        
        try:
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json={
                    "parent": {"database_id": self.database_id},
                    "properties": properties
                },
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"   ✅ 创建代币: {symbol} ({chain})")
                return True
            else:
                error_text = response.text.lower()
                if "select" in error_text and "expected" in error_text:
                    # Select选项错误，尝试使用默认值
                    print(f"   ⚠️ Select选项错误: {symbol}")
                    
                    # 移除可能有问题的select属性
                    for prop_key in [self.property_mapping.get("chain"), 
                                    self.property_mapping.get("status"),
                                    self.property_mapping.get("last_alert")]:
                        if prop_key and prop_key in properties:
                            del properties[prop_key]
                    
                    # 重新尝试
                    retry_response = requests.post(
                        "https://api.notion.com/v1/pages",
                        headers=self.headers,
                        json={
                            "parent": {"database_id": self.database_id},
                            "properties": properties
                        },
                        timeout=15
                    )
                    
                    if retry_response.status_code == 200:
                        print(f"   ✅ 重试成功（不使用select属性）: {symbol}")
                        return True
                    else:
                        print(f"   ❌ 重试失败: {retry_response.status_code}")
                
                print(f"   ❌ 创建失败 {symbol}: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ 创建异常 {symbol}: {e}")
            return False
    
    def sync_data(self, max_tokens: int = 10):
        """同步数据到Notion"""
        print(f"\n🔄 开始同步数据到Notion...")
        
        # 测试连接
        if not self.test_connection():
            print(f"❌ 连接测试失败，无法继续")
            return False
        
        # 加载监控数据
        monitor_data = self.load_monitor_data()
        tokens = monitor_data.get("tokens", [])
        
        if not tokens:
            print(f"⚠️ 没有代币数据可同步")
            return False
        
        print(f"📊 准备同步 {len(tokens)} 个代币")
        print(f"   （限制为前 {max_tokens} 个进行测试）")
        
        # 同步数据
        success_count = 0
        sync_tokens = tokens[:max_tokens]
        
        for i, token_data in enumerate(sync_tokens):
            symbol = token_data.get("symbol", f"TOKEN_{i}")
            chain = token_data.get("chain", "unknown")
            
            print(f"   [{i+1}/{len(sync_tokens)}] 同步 {symbol} ({chain})...")
            
            if self.create_token_page(token_data):
                success_count += 1
            else:
                print(f"   ⚠️ 跳过 {symbol} 的后续同步")
                break  # 如果连续失败，停止同步
        
        print(f"\n📈 同步完成")
        print(f"   成功: {success_count}/{len(sync_tokens)}")
        print(f"   失败: {len(sync_tokens) - success_count}/{len(sync_tokens)}")
        
        return success_count > 0

def main():
    database_id = os.environ.get("NOTION_DATABASE_ID")
    
    print("🚀 最终Notion同步系统")
    print("=" * 60)
    
    if not database_id:
        print("❌ 未设置数据库ID")
        print()
        print("📋 使用指南:")
        print("   export NOTION_DATABASE_ID='2357520df8254ae694a25ccaec614edd'")
        print("   python3 final_notion_sync.py")
        print()
        print("或一次性运行:")
        print("   NOTION_DATABASE_ID='2357520df8254ae694a25ccaec614edd' python3 final_notion_sync.py")
        print("=" * 60)
        return
    
    # 初始化同步器
    sync = FinalNotionSync(database_id)
    
    # 同步数据（限制为前10个代币进行测试）
    sync.sync_data(max_tokens=10)
    
    print("=" * 60)
    print("\n📋 配置说明:")
    print(f"   数据库ID: {database_id}")
    print(f"   发现的属性: {sync.property_mapping}")
    print(f"\n💡 如果Select属性有问题，请在Notion中检查:")
    print(f"   1. Chain属性的选项: BSC, Ethereum, Solana, Base")
    print(f"   2. Status属性的选项: Active, Watching, Inactive")
    print(f"   3. LastAlert属性的选项: None, Volume Surge, Large Trade, High Risk")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()