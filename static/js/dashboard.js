// ClawAlert 监控面板交互脚本

class Dashboard {
    constructor() {
        this.apiBase = '/api';
        this.updateInterval = 30000; // 30秒更新一次
        this.chart = null;
        
        this.init();
    }
    
    init() {
        // 初始化图表
        this.initChart();
        
        // 加载初始数据
        this.loadDashboardData();
        
        // 设置定时更新
        setInterval(() => this.loadDashboardData(), this.updateInterval);
        
        // 添加事件监听器
        this.bindEvents();
    }
    
    initChart() {
        const ctx = document.getElementById('chainChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['BSC', 'Ethereum', 'Solana', 'Base'],
                datasets: [{
                    label: '监控代币数',
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        'rgba(240, 185, 11, 0.7)',
                        'rgba(98, 126, 234, 0.7)',
                        'rgba(0, 255, 163, 0.7)',
                        'rgba(0, 82, 255, 0.7)'
                    ],
                    borderColor: [
                        '#f0b90b',
                        '#627eea',
                        '#00ffa3',
                        '#0052ff'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.6)'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.6)'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    async loadDashboardData() {
        try {
            // 并行加载所有数据
            const [status, tokens, alerts] = await Promise.all([
                this.fetchData('/status'),
                this.fetchData('/tokens?limit=50'),
                this.fetchData('/alerts?limit=10')
            ]);
            
            // 更新状态概览
            this.updateStatusOverview(status);
            
            // 更新图表
            this.updateChart(status);
            
            // 更新警报列表
            this.updateAlertsList(alerts.alerts || []);
            
            // 更新代币列表
            this.updateTokensTable(tokens.tokens || []);
            
            // 更新最后更新时间
            document.getElementById('last-update').textContent = 
                new Date().toLocaleString('zh-CN');
                
        } catch (error) {
            console.error('加载数据失败:', error);
            this.showError('数据加载失败，请检查API连接');
        }
    }
    
    async fetchData(endpoint) {
        const response = await fetch(`${this.apiBase}${endpoint}`);
        if (!response.ok) {
            throw new Error(`API请求失败: ${response.status}`);
        }
        return await response.json();
    }
    
    updateStatusOverview(status) {
        // 更新总代币数
        document.getElementById('total-tokens').textContent = 
            status.total_tokens || 0;
        
        // 更新今日警报数
        const todayAlerts = status.today_alerts || 0;
        document.getElementById('today-alerts').textContent = todayAlerts;
        
        // 更新活跃链
        this.updateActiveChains(status.active_chains || []);
    }
    
    updateActiveChains(activeChains) {
        const chainTags = document.querySelectorAll('.chain-tag');
        chainTags.forEach(tag => {
            const chain = tag.classList[1]; // bsc, eth, sol, base
            const isActive = activeChains.some(active => 
                active.toLowerCase().includes(chain));
            
            tag.style.opacity = isActive ? '1' : '0.3';
        });
    }
    
    updateChart(status) {
        const chainData = status.chain_stats || {};
        const chainOrder = ['bsc', 'ethereum', 'solana', 'base'];
        
        const data = chainOrder.map(chain => 
            chainData[chain]?.token_count || 0
        );
        
        this.chart.data.datasets[0].data = data;
        this.chart.update();
    }
    
    updateAlertsList(alerts) {
        const alertsList = document.getElementById('alerts-list');
        
        if (alerts.length === 0) {
            alertsList.innerHTML = `
                <div class="alert-item info">
                    <div class="alert-header">
                        <div class="alert-title">
                            <i class="fas fa-check-circle"></i>
                            暂无警报
                        </div>
                    </div>
                    <div class="alert-message">
                        当前没有检测到异常交易活动，一切正常。
                    </div>
                </div>
            `;
            return;
        }
        
        alertsList.innerHTML = alerts.map(alert => {
            const alertClass = this.getAlertClass(alert.alert_type);
            const alertIcon = this.getAlertIcon(alert.alert_type);
            const time = new Date(alert.timestamp).toLocaleString('zh-CN');
            
            return `
                <div class="alert-item ${alertClass}">
                    <div class="alert-header">
                        <div class="alert-title">
                            <i class="${alertIcon}"></i>
                            ${this.getAlertTitle(alert.alert_type)}
                        </div>
                        <div class="alert-time">${time}</div>
                    </div>
                    <div class="alert-message">
                        ${alert.message || '检测到异常交易活动'}
                        ${alert.volume_change ? 
                            ` (变化率: ${(alert.volume_change * 100).toFixed(1)}%)` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updateTokensTable(tokens) {
        const tbody = document.getElementById('tokens-body');
        
        if (tokens.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="loading-cell">
                        <i class="fas fa-info-circle"></i> 暂无代币数据
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = tokens.map(token => {
            const changeClass = token.volume_change_30min >= 0 ? 'positive-change' : 'negative-change';
            const changeSymbol = token.volume_change_30min >= 0 ? '+' : '';
            const changeText = token.volume_change_30min !== undefined ? 
                `${changeSymbol}${(token.volume_change_30min * 100).toFixed(1)}%` : 'N/A';
            
            const marketCap = token.market_cap ? 
                `$${(token.market_cap / 1000000).toFixed(1)}M` : 'N/A';
            
            const price = token.price ? 
                `$${token.price.toFixed(4)}` : 'N/A';
            
            const volume = token.volume_30min ? 
                `$${(token.volume_30min).toFixed(0)}` : 'N/A';
            
            return `
                <tr>
                    <td>
                        <div class="token-symbol">${token.symbol || 'UNKNOWN'}</div>
                        <div class="token-address">${token.address?.substring(0, 8)}...${token.address?.substring(token.address.length - 6)}</div>
                    </td>
                    <td>
                        <span class="token-chain ${token.chain?.toLowerCase()}">
                            ${token.chain || 'UNKNOWN'}
                        </span>
                    </td>
                    <td>${marketCap}</td>
                    <td>${price}</td>
                    <td>${volume}</td>
                    <td class="${changeClass}">${changeText}</td>
                    <td>
                        <span class="token-status status-${token.status?.toLowerCase() || 'active'}">
                            ${token.status || 'Active'}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    getAlertClass(alertType) {
        const type = alertType?.toLowerCase() || 'info';
        if (type.includes('critical') || type.includes('risk')) return 'critical';
        if (type.includes('warning') || type.includes('surge')) return 'warning';
        return 'info';
    }
    
    getAlertIcon(alertType) {
        const type = alertType?.toLowerCase() || 'info';
        if (type.includes('critical') || type.includes('risk')) return 'fas fa-radiation';
        if (type.includes('warning') || type.includes('surge')) return 'fas fa-exclamation-triangle';
        return 'fas fa-info-circle';
    }
    
    getAlertTitle(alertType) {
        const type = alertType?.toLowerCase() || 'info';
        if (type.includes('volume_surge')) return '交易量激增';
        if (type.includes('large_trade')) return '大额交易';
        if (type.includes('high_risk')) return '高风险代币';
        if (type.includes('api_error')) return 'API异常';
        return '系统通知';
    }
    
    showError(message) {
        // 简单错误提示
        const alertsList = document.getElementById('alerts-list');
        alertsList.innerHTML = `
            <div class="alert-item critical">
                <div class="alert-header">
                    <div class="alert-title">
                        <i class="fas fa-exclamation-circle"></i>
                        系统错误
                    </div>
                </div>
                <div class="alert-message">
                    ${message}，请检查控制台获取详细信息。
                </div>
            </div>
        `;
    }
    
    bindEvents() {
        // 可以添加更多交互事件
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('refresh-btn')) {
                this.loadDashboardData();
            }
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});