#!/usr/bin/env python3
"""
多链代币监控数据展示网站
后端API服务
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 数据文件路径
WORKSPACE_DIR = "/root/.openclaw/workspace"
CACHE_FILES = {
    "optimized": "optimized_chain_cache.json",
    "multi_chain": "multi_chain_cache.json",
    "bsc_okx": "bsc_okx_cache.json",
    "bsc_realtime": "bsc_realtime_cache.json"
}

ALERT_FILES = {
    "bsc_okx": "bsc_okx_alerts.json"
}

LOG_FILES = {
    "optimized_monitor": "logs/optimized_chain_monitor.log",
    "multi_chain_monitor": "logs/multi_chain_monitor.log",
    "bsc_okx_monitor": "logs/bsc_okx_monitor.log"
}

def load_json_file(file_path):
    """加载JSON文件"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载文件 {file_path} 失败: {e}")
    return {}

def parse_cache_data(cache_data):
    """解析缓存数据（支持volume30min和volume_5m格式）"""
    result = {
        "chains": {},
        "tokens": [],
        "last_update": cache_data.get("last_update")
    }
    
    volume_history = cache_data.get("volume_history", {})
    
    for token_key, history in volume_history.items():
        if not history:
            continue
            
        # 解析token_key格式: chain_address
        parts = token_key.split("_", 1)
        if len(parts) != 2:
            continue
            
        chain, address = parts
        
        for record in history:
            # 标准化交易量字段
            if "volume30min" in record:
                record["volume"] = record["volume30min"]
            elif "volume_5m" in record:
                record["volume"] = record["volume_5m"] * 6  # 转换为30分钟交易量估算
            else:
                record["volume"] = 0
        
        latest_record = history[-1] if history else {}
        
        # 计算链统计
        if chain not in result["chains"]:
            result["chains"][chain] = {
                "token_count": 0,
                "total_volume": 0
            }
        
        result["chains"][chain]["token_count"] += 1
        result["chains"][chain]["total_volume"] += latest_record.get("volume", 0)
        
        # 添加代币信息
        token_info = {
            "chain": chain,
            "address": address,
            "short_address": address[:8] + "..." + address[-6:] if len(address) > 14 else address,
            "latest_volume": latest_record.get("volume", 0),
            "history_count": len(history),
            "latest_timestamp": latest_record.get("timestamp"),
            "history": history[-5:]  # 只保留最近5条记录
        }
        result["tokens"].append(token_info)
    
    # 按交易量排序代币
    result["tokens"].sort(key=lambda x: x["latest_volume"], reverse=True)
    
    return result

def parse_alert_data(alert_data):
    """解析警报数据"""
    result = {
        "alerts": [],
        "last_alert_time": alert_data.get("last_alert_time", {})
    }
    
    for alert_key, alert_time in alert_data.get("last_alert_time", {}).items():
        # 解析alert_key格式: alerttype_chain_address
        parts = alert_key.split("_", 2)
        if len(parts) >= 2:
            alert_type = parts[0]
            chain = parts[1] if len(parts) > 1 else ""
            address = parts[2] if len(parts) > 2 else ""
            
            result["alerts"].append({
                "type": alert_type,
                "chain": chain,
                "address": address,
                "short_address": address[:8] + "..." + address[-6:] if len(address) > 14 else address,
                "time": alert_time,
                "time_ago": get_time_ago(alert_time)
            })
    
    # 按时间排序（最新的在前）
    result["alerts"].sort(key=lambda x: x["time"], reverse=True)
    
    return result

def get_time_ago(timestamp_str):
    """计算相对时间"""
    try:
        alert_time = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        diff = now - alert_time
        
        if diff.days > 0:
            return f"{diff.days}天前"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}小时前"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}分钟前"
        else:
            return f"{diff.seconds}秒前"
    except:
        return "未知时间"

def read_recent_logs(file_path, lines=50):
    """读取最近的日志"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
    except Exception as e:
        print(f"读取日志 {file_path} 失败: {e}")
    return ""

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """API状态"""
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "service": "Multi-Chain Token Monitor Dashboard"
    })

@app.route('/api/cache/<cache_type>')
def api_cache(cache_type):
    """获取缓存数据"""
    cache_file = CACHE_FILES.get(cache_type)
    if not cache_file:
        return jsonify({"error": "无效的缓存类型"}), 404
    
    file_path = os.path.join(WORKSPACE_DIR, cache_file)
    cache_data = load_json_file(file_path)
    
    if cache_type == "optimized":
        parsed_data = parse_cache_data(cache_data)
    else:
        parsed_data = parse_cache_data(cache_data)
    
    return jsonify(parsed_data)

@app.route('/api/alerts')
def api_alerts():
    """获取警报数据"""
    alerts_data = {}
    
    for alert_type, alert_file in ALERT_FILES.items():
        file_path = os.path.join(WORKSPACE_DIR, alert_file)
        alert_data = load_json_file(file_path)
        alerts_data[alert_type] = parse_alert_data(alert_data)
    
    return jsonify(alerts_data)

@app.route('/api/logs/<log_type>')
def api_logs(log_type):
    """获取日志数据"""
    log_file = LOG_FILES.get(log_type)
    if not log_file:
        return jsonify({"error": "无效的日志类型"}), 404
    
    file_path = os.path.join(WORKSPACE_DIR, log_file)
    logs = read_recent_logs(file_path, 100)
    
    return jsonify({
        "log_type": log_type,
        "content": logs,
        "file_path": file_path
    })

@app.route('/api/summary')
def api_summary():
    """获取汇总数据"""
    summary = {
        "total_tokens": 0,
        "active_chains": [],
        "recent_alerts": 0,
        "last_update": None
    }
    
    # 加载优化版缓存数据
    optimized_cache_file = os.path.join(WORKSPACE_DIR, CACHE_FILES["optimized"])
    optimized_data = load_json_file(optimized_cache_file)
    
    if optimized_data:
        parsed_data = parse_cache_data(optimized_data)
        summary["total_tokens"] = len(parsed_data["tokens"])
        summary["active_chains"] = list(parsed_data["chains"].keys())
        summary["last_update"] = parsed_data.get("last_update")
    
    # 加载警报数据
    bsc_alert_file = os.path.join(WORKSPACE_DIR, ALERT_FILES["bsc_okx"])
    alert_data = load_json_file(bsc_alert_file)
    
    if alert_data and "last_alert_time" in alert_data:
        summary["recent_alerts"] = len(alert_data["last_alert_time"])
    
    return jsonify(summary)

@app.route('/api/chains')
def api_chains():
    """获取链统计信息"""
    chains_data = {}
    
    # 加载所有缓存文件
    for cache_type, cache_file in CACHE_FILES.items():
        file_path = os.path.join(WORKSPACE_DIR, cache_file)
        cache_data = load_json_file(file_path)
        
        if cache_data and "volume_history" in cache_data:
            volume_history = cache_data.get("volume_history", {})
            
            for token_key in volume_history.keys():
                parts = token_key.split("_", 1)
                if len(parts) == 2:
                    chain = parts[0]
                    
                    if chain not in chains_data:
                        chains_data[chain] = {
                            "name": chain.upper(),
                            "token_count": 0,
                            "total_volume": 0,
                            "sources": set()
                        }
                    
                    chains_data[chain]["token_count"] += 1
                    chains_data[chain]["sources"].add(cache_type)
                    
                    # 计算总交易量
                    history = volume_history[token_key]
                    if history:
                        latest_record = history[-1]
                        # 支持不同格式的交易量字段
                        if "volume30min" in latest_record:
                            latest_volume = latest_record.get("volume30min", 0)
                        elif "volume_5m" in latest_record:
                            latest_volume = latest_record.get("volume_5m", 0) * 6  # 转换为30分钟估算
                        else:
                            latest_volume = 0
                        chains_data[chain]["total_volume"] += latest_volume
    
    # 转换set为list
    for chain in chains_data:
        chains_data[chain]["sources"] = list(chains_data[chain]["sources"])
    
    return jsonify(chains_data)

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs(os.path.join(WORKSPACE_DIR, 'static'), exist_ok=True)
    os.makedirs(os.path.join(WORKSPACE_DIR, 'templates'), exist_ok=True)
    
    # 生产模式运行
    print(f"🚀 启动监控数据展示网站: http://0.0.0.0:5000")
    print(f"📊 数据目录: {WORKSPACE_DIR}")
    print(f"🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    app.run(host='0.0.0.0', port=80, debug=False)