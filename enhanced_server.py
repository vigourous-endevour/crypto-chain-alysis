from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import sqlite3
import json
import asyncio
import aiohttp
import threading
import time
from datetime import datetime, timedelta
from web3 import Web3
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@dataclass
class TokenLaunch:
    chain: str
    contract_address: str
    name: str
    symbol: str
    creator_address: str
    creation_time: datetime
    risk_score: float
    risk_level: str
    risk_factors: List[str]

class TokenMonitor:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)
        self.db_path = self.config.get('db_path', 'token_launches.db')
        self.setup_database()
        self.web3_clients = self.setup_web3_clients()
        self.monitoring = False
        self.tokens_found = []
        
    def load_config(self, config_path):
        """Load configuration from JSON file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.error(f"Config file {config_path} not found!")
            return {}
    
    def setup_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_launches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain TEXT NOT NULL,
                contract_address TEXT NOT NULL,
                name TEXT,
                symbol TEXT,
                creator_address TEXT,
                creation_time TIMESTAMP,
                risk_score REAL,
                risk_level TEXT,
                risk_factors TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chain, contract_address)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_web3_clients(self):
        """Setup Web3 clients for different chains"""
        clients = {}
        
        for chain in ['ethereum', 'base']:
            rpc_url = self.config.get(chain, {}).get('rpc_url')
            if rpc_url and 'YOUR_' not in rpc_url:
                try:
                    clients[chain] = Web3(Web3.HTTPProvider(rpc_url))
                    logger.info(f"✅ Connected to {chain}: {clients[chain].is_connected()}")
                except Exception as e:
                    logger.error(f"❌ Failed to connect to {chain}: {e}")
            else:
                logger.warning(f"⚠️ No valid RPC URL for {chain}")
        
        return clients
    
    def analyze_contract_risk(self, chain: str, contract_address: str, creator_address: str) -> Tuple[float, str, List[str]]:
        """Analyze contract for risk factors"""
        risk_factors = []
        risk_score = 0.0
        
        try:
            if chain in self.web3_clients:
                web3 = self.web3_clients[chain]
                
                # Get contract code
                code = web3.eth.get_code(contract_address)
                code_hex = code.hex()
                
                # Check for dangerous functions
                if '40c10f19' in code_hex:  # mint function
                    risk_factors.append("Contract has mint function - inflation risk")
                    risk_score += 0.3
                
                if '8456cb59' in code_hex:  # pause function
                    risk_factors.append("Contract has pause function")
                    risk_score += 0.2
                
                # Check creator transaction count
                creator_tx_count = web3.eth.get_transaction_count(creator_address)
                if creator_tx_count < 5:
                    risk_factors.append("New/low-activity creator address")
                    risk_score += 0.3
                
                # Check creator balance
                creator_balance = web3.eth.get_balance(creator_address)
                if creator_balance < web3.to_wei(0.01, 'ether'):
                    risk_factors.append("Creator has very low ETH balance")
                    risk_score += 0.2
                
                # Check if contract is verified (simplified check)
                if len(code_hex) < 100:
                    risk_factors.append("Contract appears to be minimal/proxy")
                    risk_score += 0.1
        
        except Exception as e:
            logger.error(f"Error analyzing contract {contract_address}: {e}")
            risk_factors.append("Unable to analyze contract code")
            risk_score = 0.5
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "CRITICAL"
        elif risk_score >= 0.6:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return min(risk_score, 1.0), risk_level, risk_factors
    
    async def monitor_new_tokens(self):
        """Monitor for new token deployments"""
        logger.info("🔍 Starting token monitoring...")
        
        while self.monitoring:
            try:
                for chain, web3 in self.web3_clients.items():
                    if not web3.is_connected():
                        continue
                    
                    # Get latest block
                    latest_block = web3.eth.get_block('latest', full_transactions=True)
                    
                    # Check transactions for contract creations
                    for tx in latest_block.transactions:
                        if tx.to is None:  # Contract creation
                            receipt = web3.eth.get_transaction_receipt(tx.hash)
                            if receipt.contractAddress:
                                await self.analyze_new_token(chain, receipt.contractAddress, tx['from'])
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def analyze_new_token(self, chain: str, contract_address: str, creator_address: str):
        """Analyze a newly detected token"""
        try:
            web3 = self.web3_clients[chain]
            
            # Try to get token info (name, symbol)
            try:
                # Standard ERC20 function signatures
                name_sig = web3.keccak(text="name()")[:4].hex()
                symbol_sig = web3.keccak(text="symbol()")[:4].hex()
                
                # This is simplified - in practice you'd need proper ABI calls
                name = f"Token_{contract_address[:8]}"
                symbol = f"TKN_{contract_address[:6]}"
                
            except:
                name = f"Unknown_{contract_address[:8]}"
                symbol = "UNK"
            
            # Analyze risk
            risk_score, risk_level, risk_factors = self.analyze_contract_risk(
                chain, contract_address, creator_address
            )
            
            # Create token launch object
            token_launch = TokenLaunch(
                chain=chain,
                contract_address=contract_address,
                name=name,
                symbol=symbol,
                creator_address=creator_address,
                creation_time=datetime.now(),
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors
            )
            
            # Store in database
            self.store_token_launch(token_launch)
            
            # Add to recent tokens list
            self.tokens_found.append(token_launch)
            if len(self.tokens_found) > 100:  # Keep only last 100
                self.tokens_found.pop(0)
            
            logger.info(f"🆕 New token detected: {name} ({symbol}) - Risk: {risk_level}")
            
        except Exception as e:
            logger.error(f"Error analyzing token {contract_address}: {e}")
    
    def store_token_launch(self, token_launch: TokenLaunch):
        """Store token launch in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO token_launches 
                (chain, contract_address, name, symbol, creator_address, creation_time, 
                 risk_score, risk_level, risk_factors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token_launch.chain,
                token_launch.contract_address,
                token_launch.name,
                token_launch.symbol,
                token_launch.creator_address,
                token_launch.creation_time,
                token_launch.risk_score,
                token_launch.risk_level,
                json.dumps(token_launch.risk_factors)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing token launch: {e}")
    
    def get_recent_tokens(self, hours=24, limit=50):
        """Get recently detected tokens"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT * FROM token_launches 
                WHERE creation_time > ? 
                ORDER BY creation_time DESC 
                LIMIT ?
            ''', (since, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            tokens = []
            for row in rows:
                tokens.append({
                    'id': row[0],
                    'chain': row[1],
                    'contract_address': row[2],
                    'name': row[3],
                    'symbol': row[4],
                    'creator_address': row[5],
                    'creation_time': row[6],
                    'risk_score': row[7],
                    'risk_level': row[8],
                    'risk_factors': json.loads(row[9]) if row[9] else []
                })
            
            return tokens
            
        except Exception as e:
            logger.error(f"Error getting recent tokens: {e}")
            return []

# Global monitor instance
monitor = TokenMonitor()

# Dashboard HTML template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 Live Token Launch Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .status-panel {
            background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px;
            margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .controls { text-align: center; margin: 20px 0; }
        .btn {
            background: #667eea; color: white; border: none; padding: 12px 24px;
            border-radius: 8px; cursor: pointer; font-size: 16px; margin: 10px;
            transition: background 0.3s ease;
        }
        .btn:hover { background: #5a67d8; }
        .btn.danger { background: #e53e3e; }
        .btn.danger:hover { background: #c53030; }
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px; margin: 20px 0;
        }
        .stat-card {
            background: white; padding: 20px; border-radius: 10px; text-align: center;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 5px; }
        .tokens-list {
            background: white; border-radius: 15px; padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .token-item {
            border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 10px 0;
            transition: transform 0.2s ease;
        }
        .token-item:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
        .token-header { display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }
        .token-name { font-weight: bold; font-size: 1.1em; }
        .risk-badge {
            padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold;
        }
        .risk-LOW { background: #c6f6d5; color: #22543d; }
        .risk-MEDIUM { background: #fed7d7; color: #742a2a; }
        .risk-HIGH { background: #fbb6ce; color: #702459; }
        .risk-CRITICAL { background: #feb2b2; color: #822727; }
        .token-details { color: #666; font-size: 0.9em; }
        .status-indicator {
            width: 12px; height: 12px; border-radius: 50%; margin-right: 10px;
            display: inline-block;
        }
        .status-running { background: #28a745; }
        .status-stopped { background: #dc3545; }
        .auto-refresh { color: #666; font-size: 0.9em; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Live Token Launch Monitor</h1>
            <p>Real-time cryptocurrency token detection and risk analysis</p>
        </div>

        <div class="status-panel">
            <h3>🎛️ Monitor Status</h3>
            <div style="display: flex; align-items: center; margin: 15px 0;">
                <div class="status-indicator" id="statusIndicator"></div>
                <span id="statusText">Checking status...</span>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="startMonitoring()">▶️ Start Monitoring</button>
                <button class="btn danger" onclick="stopMonitoring()">⏹️ Stop Monitoring</button>
                <button class="btn" onclick="refreshData()">🔄 Refresh Data</button>
            </div>
        </div>

        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-value" id="totalTokens">-</div>
                <div class="stat-label">Tokens Detected (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="highRiskTokens">-</div>
                <div class="stat-label">High Risk Tokens</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="activeChains">-</div>
                <div class="stat-label">Active Chains</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avgRiskScore">-</div>
                <div class="stat-label">Avg Risk Score</div>
            </div>
        </div>

        <div class="tokens-list">
            <h3>🆕 Recently Detected Tokens</h3>
            <div class="auto-refresh">Auto-refreshing every 30 seconds...</div>
            <div id="tokensList">
                <p style="text-align: center; color: #666; margin: 40px 0;">
                    No tokens detected yet. Start monitoring to see real-time results!
                </p>
            </div>
        </div>
    </div>

    <script>
        let isMonitoring = false;
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const indicator = document.getElementById('statusIndicator');
                const statusText = document.getElementById('statusText');
                
                if (data.monitoring) {
                    indicator.className = 'status-indicator status-running';
                    statusText.textContent = 'Monitoring active - Scanning for new tokens';
                    isMonitoring = true;
                } else {
                    indicator.className = 'status-indicator status-stopped';
                    statusText.textContent = 'Monitoring stopped';
                    isMonitoring = false;
                }
            } catch (error) {
                console.error('Error checking status:', error);
            }
        }
        
        async function startMonitoring() {
            try {
                const response = await fetch('/api/monitoring/start', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                checkStatus();
            } catch (error) {
                alert('Error starting monitoring: ' + error.message);
            }
        }
        
        async function stopMonitoring() {
            try {
                const response = await fetch('/api/monitoring/stop', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                checkStatus();
            } catch (error) {
                alert('Error stopping monitoring: ' + error.message);
            }
        }
        
        async function loadTokens() {
            try {
                const response = await fetch('/api/tokens/recent');
                const data = await response.json();
                
                const tokensList = document.getElementById('tokensList');
                
                if (data.tokens && data.tokens.length > 0) {
                    tokensList.innerHTML = data.tokens.map(token => `
                        <div class="token-item">
                            <div class="token-header">
                                <div class="token-name">${token.name} (${token.symbol})</div>
                                <div class="risk-badge risk-${token.risk_level}">${token.risk_level}</div>
                            </div>
                            <div class="token-details">
                                <div><strong>Chain:</strong> ${token.chain.toUpperCase()}</div>
                                <div><strong>Contract:</strong> ${token.contract_address}</div>
                                <div><strong>Risk Score:</strong> ${(token.risk_score * 100).toFixed(1)}%</div>
                                <div><strong>Created:</strong> ${new Date(token.creation_time).toLocaleString()}</div>
                                ${token.risk_factors.length > 0 ? `
                                    <div style="margin-top: 10px;"><strong>Risk Factors:</strong></div>
                                    <ul style="margin-left: 20px;">
                                        ${token.risk_factors.map(factor => `<li>${factor}</li>`).join('')}
                                    </ul>
                                ` : ''}
                            </div>
                        </div>
                    `).join('');
                    
                    // Update stats
                    const totalTokens = data.tokens.length;
                    const highRiskTokens = data.tokens.filter(t => t.risk_level === 'HIGH' || t.risk_level === 'CRITICAL').length;
                    const activeChains = [...new Set(data.tokens.map(t => t.chain))].length;
                    const avgRiskScore = totalTokens > 0 ? 
                        (data.tokens.reduce((sum, t) => sum + t.risk_score, 0) / totalTokens * 100).toFixed(1) + '%' : '0%';
                    
                    document.getElementById('totalTokens').textContent = totalTokens;
                    document.getElementById('highRiskTokens').textContent = highRiskTokens;
                    document.getElementById('activeChains').textContent = activeChains;
                    document.getElementById('avgRiskScore').textContent = avgRiskScore;
                    
                } else {
                    tokensList.innerHTML = `
                        <p style="text-align: center; color: #666; margin: 40px 0;">
                            No tokens detected yet. ${isMonitoring ? 'Monitoring is active...' : 'Start monitoring to see results!'}
                        </p>
                    `;
                }
            } catch (error) {
                console.error('Error loading tokens:', error);
            }
        }
        
        function refreshData() {
            checkStatus();
            loadTokens();
        }
        
        // Initial load
        checkStatus();
        loadTokens();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def get_status():
    return jsonify({
        'status': 'success',
        'monitoring': monitor.monitoring,
        'connected_chains': list(monitor.web3_clients.keys()),
        'database': os.path.exists(monitor.db_path),
        'version': '2.0.0'
    })

@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    if monitor.monitoring:
        return jsonify({
            'status': 'error',
            'message': 'Monitoring is already running'
        }), 400
    
    monitor.monitoring = True
    
    # Start monitoring in background thread
    def run_monitor():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.monitor_new_tokens())
    
    thread = threading.Thread(target=run_monitor, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': 'Token monitoring started! 🔍 Scanning for new tokens...',
        'connected_chains': list(monitor.web3_clients.keys())
    })

@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    if not monitor.monitoring:
        return jsonify({
            'status': 'error',
            'message': 'Monitoring is not running'
        }), 400
    
    monitor.monitoring = False
    
    return jsonify({
        'status': 'success',
        'message': 'Token monitoring stopped'
    })

@app.route('/api/tokens/recent')
def get_recent_tokens():
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    tokens = monitor.get_recent_tokens(hours=hours, limit=limit)
    
    return jsonify({
        'status': 'success',
        'tokens': tokens,
        'count': len(tokens)
    })

@app.route('/api/tokens/analyze/<chain>/<address>')
def analyze_token(chain, address):
    try:
        # Simulate analysis for demo
        risk_score, risk_level, risk_factors = monitor.analyze_contract_risk(
            chain, address, "0x0000000000000000000000000000000000000000"
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'contract_address': address,
                'chain': chain,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'analysis_time': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Enhanced Token Launch Monitor...")
    print("🔗 Connected chains:", list(monitor.web3_clients.keys()))
    print("📊 Dashboard: http://localhost:5000")
    print("🔧 API: http://localhost:5000/api/*")
    print()
    print("✨ Features:")
    print("  • Real-time token detection")
    print("  • Risk analysis and scoring")
    print("  • Multi-chain support (Ethereum, Base)")
    print("  • Live dashboard with auto-refresh")
    print("  • Historical data storage")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
