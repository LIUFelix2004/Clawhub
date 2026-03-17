#!/usr/bin/env python3
"""
简单Notion同步脚本
使用现有数据库ID直接同步数据
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# 北京时区
BEIJING_TZ = datetime.now().astimezone().tzinfo

class SimpleNotionSync:
    def __init__(self, database_id: str = None):
        self.api_key = self.load_notion_key()
        self.database_id = database_id or os.environ.get("NOTION_DATABASE_ID")
        
        if not self.database_id:
            print("❌ 未提供数据库ID")
            print("请设置环境变量: export NOTION_DATABASE_ID='your_database_id'")
            print("或运行: NOTION_DATABASE_ID='your_database_id' python3 simple_notion_sync.py")
            sys.exit(1)
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2025-09-03",
            "Content-Type": "application/json"
        }
        
        print(f"🔗 使用数据库ID: {self.database_id}")
    
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
        print("请按以下步骤设置：")
        print("1. 访问 https://notion.so/my-integrations 创建集成")
        print("2. 复制API密钥（以 'ntn_' 或 'secret_' 开头）")
        print("3. 保存到文件：mkdir -p ~/.config/notion && echo 'ntn_your_key' > ~/.config/notion/api_key")
        sys.exit(1)
    
    def test_database_access(self) -> bool:
        """测试数据库访问权限"""
        print(f"🔍 测试数据库访问...")
        
        try:
            response = requests.get(
                f"https://api.notion.com/v1/databases/{self.database_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                db_info = response.json()
                title = db_info.get('title', [{}])[0].get('text', {}).get('content', 'Untitled')
                properties = db_info.get('properties', {})
                
                print(f"✅ 数据库访问成功")
                print(f"   数据库标题: {title}")
                print(f"   属性数量: {len(properties)}")
                
                if properties:
                    print(f"   属性列表: {list(properties.keys())[:10]}...")
                else:
                    print(f"   ⚠️ 数据库没有属性")
                
                return True
            else:
                print(f"❌ 数据库访问失败: {response.status_code}")
                print(f"   错误: {response.text}")
                
                if "object_not_found" in response.text:
                    print(f"\n⚠️ 权限问题:")
                    print(f"   1. 数据库ID可能不正确")
                    print(f"   2. 集成 '代币监控系统' 没有被分享到这个数据库")
                    print(f"   3. 请在Notion中分享数据库给集成")
                
                return False
        except Exception as e:
            print(f"❌ 测试数据库异常: {e}")
            return False
    
    def load_monitor_data(self) -> Dict:
        """加载监控数据"""
        cache_path = "/root/.openclaw/workspace/optimized_chain_cache.json"
        
        if not os.path.exists(cache_path):
            print(f"❌ 监控缓存文件不存在: {cache_path}")
            print(f"   请先运行代币监控系统")
            return {"summary": {}, "tokens": [], "alerts": {}}
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            volume_history = cache_data.get("volume_history", {})
            tokens = []
            
            print(f"📊 加载监控数据...")
            print(f"   找到 {len(volume_history)} 个代币的历史数据")
            
            # 转换数据结构
            for token_key, history in volume_history.items():
                # token_key格式: chain:symbol:address
                parts = token_key.split(":")
                if len(parts) >= 3:
                    chain = parts[0]
                    symbol = parts[1]
                    address = parts[2]
                    
                    # 获取最新的数据
                    if history and isinstance(history, list):
                        latest_entry = history[-1] if isinstance(history[-1], dict) else {}
                        
                        token_data = {
                            "symbol": symbol,
                            "chain": chain,
                            "address": address,
                            "short_address": address[:8] + "..." + address[-6:] if len(address) > 14 else address,
                            "market_cap": latest_entry.get("market_cap", 0),
                            "price": latest_entry.get("price", 0),
                            "volume_24h": latest_entry.get("volume_24h", 0),
                            "latest_volume": latest_entry.get("latest_volume", 0),
                            "volume_change": latest_entry.get("volume_change_pct", 0),
                            "safety_score": latest_entry.get("safety_score", 50),
                            "latest_timestamp": latest_entry.get("timestamp", datetime.now(BEIJING_TZ).isoformat()),
                            "alerts": latest_entry.get("alerts", [])
                        }
                        
                        tokens.append(token_data)
            
            return {
                "summary": cache_data.get("summary", {}),
                "tokens": tokens,
                "alerts": cache_data.get("alerts", {}),
                "timestamp": datetime.now(BEIJING_TZ).isoformat()
            }
        
        except Exception as e:
            print(f"❌ 加载监控数据失败: {e}")
            return {"summary": {}, "tokens": [], "alerts": {}}
    
    def create_token_page(self, token_data: Dict) -> bool:
        """创建代币页面"""
        symbol = token_data.get("symbol", "UNKNOWN")
        chain = token_data.get("chain", "unknown").upper()
        
        # 构建属性（根据数据库实际属性调整）
        properties = {}
        
        # Name 属性
        properties["Name"] = {"title": [{"text": {"content": f"{symbol} ({chain})"}}]}
        
        # Symbol 属性（如果数据库有）
        properties["Symbol"] = {"rich_text": [{"text": {"content": symbol}}]}
        
        # Chain 属性（如果数据库有）
        properties["Chain"] = {"select": {"name": chain}}
        
        # Address 属性（如果数据库有）
        address = token_data.get("address", "")
        short_addr = token_data.get("short_address", address[:8] + "..." + address[-6:] if len(address) > 14 else address)
        properties["Address"] = {"rich_text": [{"text": {"content": short_addr}}]}
        
        # 数值属性（如果数据库有）
        market_cap = token_data.get("market_cap", 0)
        if market_cap:
            properties["MarketCap"] = {"number": market_cap}
        
        price = token_data.get("price", 0)
        if price:
            properties["Price"] = {"number": price}
        
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
                print(f"   ❌ 创建失败 {symbol}: {response.status_code}")
                # 不打印详细错误，避免输出太长
                return False
        except Exception as e:
            print(f"   ❌ 创建异常 {symbol}: {e}")
            return False
    
    def sync_data(self, max_tokens: int = 50):
        """同步数据到Notion"""
        print(f"\n🔄 开始同步数据到Notion...")
        
        # 测试数据库访问
        if not self.test_database_access():
            print(f"❌ 数据库访问测试失败，无法继续")
            return False
        
        # 加载监控数据
        monitor_data = self.load_monitor_data()
        tokens = monitor_data.get("tokens", [])
        
        if not tokens:
            print(f"⚠️ 没有代币数据可同步")
            return False
        
        print(f"📊 准备同步 {len(tokens)} 个代币")
        print(f"   （限制为前 {max_tokens} 个）")
        
        # 同步数据
        success_count = 0
        sync_tokens = tokens[:max_tokens]
        
        for i, token_data in enumerate(sync_tokens):
            symbol = token_data.get("symbol", f"TOKEN_{i}")
            chain = token_data.get("chain", "unknown")
            
            print(f"   [{i+1}/{len(sync_tokens)}] 同步 {symbol} ({chain})...")
            
            if self.create_token_page(token_data):
                success_count += 1
        
        print(f"\n📈 同步完成")
        print(f"   成功: {success_count}/{len(sync_tokens)}")
        print(f"   失败: {len(sync_tokens) - success_count}/{len(sync_tokens)}")
        
        return success_count > 0

def main():
    print("🚀 简单Notion同步系统")
    print("=" * 60)
    
    # 从环境变量获取数据库ID
    database_id = os.environ.get("NOTION_DATABASE_ID")
    
    if not database_id:
        print("❌ 未设置数据库ID")
        print()
        print("📋 使用指南:")
        print("1. 在Notion中手动创建数据库")
        print("2. 分享数据库给集成 '代币监控系统'")
        print("3. 获取数据库ID（从链接中提取）")
        print("4. 运行以下命令:")
        print()
        print("   export NOTION_DATABASE_ID='your_database_id'")
        print("   python3 simple_notion_sync.py")
        print()
        print("或一次性运行:")
        print("   NOTION_DATABASE_ID='your_database_id' python3 simple_notion_sync.py")
        print("=" * 60)
        return
    
    # 初始化同步器
    sync = SimpleNotionSync(database_id)
    
    # 同步数据（限制为前20个代币进行测试）
    sync.sync_data(max_tokens=20)
    
    print("=" * 60)
    print("🎉 同步完成！")
    print()
    print("📋 如果遇到属性错误，请确保数据库有以下列:")
    print("   - Name (Title类型)")
    print("   - Symbol (Text类型)")
    print("   - Chain (Select类型)")
    print("   - Address (Text类型)")
    print("   - MarketCap (Number类型)")
    print("   - Price (Number类型)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()