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
import random

# Add this right after your imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add this line to see more details
print("🔍 Starting with detailed logging enabled...")


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
    etherscan_verified: bool = False
    source_code_available: bool = False

class EnhancedTokenMonitor:
    def __init__(self, config_path='config_etherscan.json'):
        self.config = self.load_config(config_path)
        self.db_path = self.config.get('db_path', 'token_launches_enhanced.db')
        self.setup_database()
        self.web3_clients = self.setup_web3_clients()
        self.monitoring = False
        self.tokens_found = []
       
        # Automatically disable demo mode if real API keys are configured
        etherscan_config = self.config.get('etherscan', {}).get('networks', {})
        has_real_keys = any(
            config.get('api_key') and 'YOUR_' not in config['api_key'] 
            for config in etherscan_config.values()
        )
        
        self.demo_mode = not has_real_keys  # Only use demo mode if no real keys
        
        if self.demo_mode:
            logger.info("🎭 Demo mode enabled - generating test tokens")
        else:
            logger.info("🔍 Production mode - monitoring real blockchain activity only")
        
    def load_config(self, config_path):
        """Load configuration from JSON file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.error(f"Config file {config_path} not found!")
            return {}
    
    def setup_database(self):
        """Initialize SQLite database with enhanced schema"""
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
                etherscan_verified BOOLEAN DEFAULT FALSE,
                source_code_available BOOLEAN DEFAULT FALSE,
                creator_reputation_score REAL DEFAULT 0,
                security_score REAL DEFAULT 0,
                transfer_pattern TEXT DEFAULT 'unknown',
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
                    is_connected = clients[chain].is_connected()
                    logger.info(f"✅ {chain.title()}: Connected = {is_connected}")
                except Exception as e:
                    logger.error(f"❌ Failed to connect to {chain}: {e}")
            else:
                logger.warning(f"⚠️ No valid RPC URL for {chain}")
        
        return clients
    
    async def check_etherscan_verification(self, chain: str, address: str) -> Dict:
        """Check if contract is verified on Etherscan"""
        try:
            etherscan_config = self.config.get('etherscan', {}).get('networks', {}).get(chain, {})
            api_key = etherscan_config.get('api_key')
            base_url = etherscan_config.get('base_url')
            
            if not api_key or not base_url:
                return {'verified': False, 'error': 'API not configured'}
            
            url = f"{base_url}?module=contract&action=getsourcecode&address={address}&apikey={api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    
                    if data['status'] == '1' and data['result'][0]['SourceCode']:
                        return {
                            'verified': True,
                            'contract_name': data['result'][0].get('ContractName', 'Unknown'),
                            'compiler_version': data['result'][0].get('CompilerVersion', 'Unknown'),
                            'optimization_used': data['result'][0].get('OptimizationUsed', 'Unknown'),
                            'source_code_available': True
                        }
                    else:
                        return {'verified': False, 'source_code_available': False}
                        
        except Exception as e:
            logger.error(f"Etherscan verification error: {e}")
            return {'verified': False, 'error': str(e)}
    
    def analyze_contract_risk_enhanced(self, chain: str, contract_address: str, creator_address: str, etherscan_data: Dict) -> Tuple[float, str, List[str]]:
        """Enhanced risk analysis with Etherscan data"""
        risk_factors = []
        risk_score = 0.0
        
        try:
            # Etherscan verification bonus
            if etherscan_data.get('verified', False):
                risk_factors.append("✅ Contract verified on Etherscan")
                risk_score -= 0.2  # Reduce risk for verified contracts
            else:
                risk_factors.append("❌ Contract not verified")
                risk_score += 0.3
            
            # Source code analysis
            if etherscan_data.get('source_code_available', False):
                risk_factors.append("✅ Source code publicly available")
                risk_score -= 0.1
            else:
                risk_factors.append("⚠️ Source code not available")
                risk_score += 0.2
            
            # Web3 analysis if available
            if chain in self.web3_clients:
                web3 = self.web3_clients[chain]
                
                try:
                    # Get contract code
                    code = web3.eth.get_code(contract_address)
                    code_hex = code.hex()
                    
                    # Check for dangerous functions
                    if '40c10f19' in code_hex:  # mint function
                        risk_factors.append("⚠️ Contract has mint function")
                        risk_score += 0.3
                    
                    if '8456cb59' in code_hex:  # pause function
                        risk_factors.append("⚠️ Contract has pause function")
                        risk_score += 0.2
                    
                    # Creator analysis
                    creator_tx_count = web3.eth.get_transaction_count(creator_address)
                    if creator_tx_count < 5:
                        risk_factors.append("🆕 New/low-activity creator")
                        risk_score += 0.3
                    elif creator_tx_count > 100:
                        risk_factors.append("✅ Experienced creator")
                        risk_score -= 0.1
                    
                    # Creator balance
                    creator_balance = web3.eth.get_balance(creator_address)
                    eth_balance = web3.from_wei(creator_balance, 'ether')
                    
                    if eth_balance < 0.01:
                        risk_factors.append("💸 Creator has very low ETH balance")
                        risk_score += 0.2
                    elif eth_balance > 1:
                        risk_factors.append("💰 Creator has significant ETH balance")
                        risk_score -= 0.1
                    
                except Exception as e:
                    logger.error(f"Web3 analysis error: {e}")
                    risk_factors.append("⚠️ Unable to analyze contract code")
                    risk_score += 0.1
        
        except Exception as e:
            logger.error(f"Risk analysis error: {e}")
            risk_factors.append("❌ Analysis failed")
            risk_score = 0.5
        
        # Ensure risk score is between 0 and 1
        risk_score = max(0.0, min(1.0, risk_score))
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "CRITICAL"
        elif risk_score >= 0.6:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return risk_score, risk_level, risk_factors
    
    async def generate_demo_token(self):
        """Generate demo tokens for testing"""
        chains = ['ethereum', 'base']
        chain = random.choice(chains)
        
        # Generate realistic-looking addresses
        contract_address = f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
        creator_address = f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
        
        # Demo token names and symbols
        demo_tokens = [
            ("SafeMoonV2", "SAFEV2"),
            ("ElonMarsCoin", "ELON"),
            ("PumpRocket", "PUMP"),
            ("DiamondHands", "DIAMOND"),
            ("ToTheMoon", "MOON"),
            ("CryptoGem", "GEM"),
            ("DeFiMaster", "DEFI"),
            ("YieldFarm", "YIELD")
        ]
        
        name, symbol = random.choice(demo_tokens)
        
        # Get Etherscan verification data
        etherscan_data = await self.check_etherscan_verification(chain, contract_address)
        
        # Analyze risk
        risk_score, risk_level, risk_factors = self.analyze_contract_risk_enhanced(
            chain, contract_address, creator_address, etherscan_data
        )
        
        # Create token launch
        token_launch = TokenLaunch(
            chain=chain,
            contract_address=contract_address,
            name=name,
            symbol=symbol,
            creator_address=creator_address,
            creation_time=datetime.now(),
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            etherscan_verified=etherscan_data.get('verified', False),
            source_code_available=etherscan_data.get('source_code_available', False)
        )
        
        return token_launch
    
    async def monitor_enhanced(self):
        """Enhanced monitoring with visible debug output"""
        print("🔍 MONITORING THREAD STARTED!")
        logger.info("🚀 Enhanced token monitoring initialized")
    
        loop_count = 0
    
        while self.monitoring:
            try:
                loop_count += 1
                print(f"\n⏰ Monitoring Loop #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"Starting monitoring loop #{loop_count}")
            
                # Real blockchain monitoring
                for chain, web3 in self.web3_clients.items():
                    if web3.is_connected():
                        try:
                            latest_block = web3.eth.get_block('latest', full_transactions=True)
                            tx_count = len(latest_block.transactions)
                        
                            print(f"📦 {chain.upper()}: Block {latest_block.number} - {tx_count} transactions")
                            logger.info(f"Scanning {chain} block {latest_block.number} with {tx_count} transactions")
                        
                            # Check for contract creations
                            contracts_found = 0
                            for tx in latest_block.transactions:
                                if tx.to is None:  # Contract creation
                                    contracts_found += 1
                                    try:
                                        receipt = web3.eth.get_transaction_receipt(tx.hash)
                                        if receipt.contractAddress:
                                            print(f"🆕 NEW CONTRACT: {receipt.contractAddress} on {chain}")
                                            logger.info(f"New contract detected: {receipt.contractAddress} on {chain}")
                                            await self.analyze_real_token(chain, receipt.contractAddress, tx['from'])
                                    except Exception as e:
                                        logger.error(f"Error processing contract creation: {e}")
                        
                            if contracts_found > 0:
                                print(f"✅ Found {contracts_found} new contracts in this block")
                            else:
                                print(f"ℹ️  No new contracts in this block")
                            
                        except Exception as e:
                            print(f"❌ Error monitoring {chain}: {e}")
                            logger.error(f"Error monitoring {chain}: {e}")
                    else:
                        print(f"⚠️  {chain} not connected")
            
                # Demo tokens (if enabled and no real activity)
                if self.demo_mode and loop_count % 5 == 0:  # Every 5th loop
                    print("🎭 Generating demo token...")
                    demo_token = await self.generate_demo_token()
                    self.store_token_launch(demo_token)
                    self.tokens_found.append(demo_token)
                    print(f"✨ Demo: {demo_token.name} ({demo_token.symbol}) - {demo_token.risk_level}")
            
                print(f"💤 Sleeping 15 seconds... (Total tokens found: {len(self.tokens_found)})\n")
                await asyncio.sleep(15)
            
            except Exception as e:
                print(f"❌ MONITORING ERROR: {e}")
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
                
                
    
    async def analyze_real_token(self, chain: str, contract_address: str, creator_address: str):
        """Analyze only actual tokens, not all contracts"""
        try:
            web3 = self.web3_clients[chain]
            
            # FIRST: Check if this is actually a token
            is_token, reason = await self.is_actual_token(web3, contract_address)
            
            if not is_token:
                logger.info(f"⏭️  Skipping {contract_address} - {reason}")
                return  # Skip non-tokens
            
            logger.info(f"✅ Confirmed token: {contract_address} - {reason}")
            
            # Get actual token information
            name, symbol, decimals = await self.get_token_info(web3, contract_address)
            
            # Get Etherscan verification
            etherscan_data = await self.check_etherscan_verification(chain, contract_address)
            
            # Enhanced risk analysis
            risk_score, risk_level, risk_factors = self.analyze_contract_risk_enhanced(
                chain, contract_address, creator_address, etherscan_data
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
                risk_factors=risk_factors,
                etherscan_verified=etherscan_data.get('verified', False),
                source_code_available=etherscan_data.get('source_code_available', False)
            )
            
            # Store and track
            self.store_token_launch(token_launch)
            self.tokens_found.append(token_launch)
            
            print(f"🎯 REAL TOKEN FOUND: {name} ({symbol}) - {decimals} decimals - Risk: {risk_level}")
            logger.info(f"Token analyzed: {name} ({symbol}) - Risk: {risk_level} - Verified: {etherscan_data.get('verified', False)}")
            
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
                 risk_score, risk_level, risk_factors, etherscan_verified, source_code_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token_launch.chain,
                token_launch.contract_address,
                token_launch.name,
                token_launch.symbol,
                token_launch.creator_address,
                token_launch.creation_time,
                token_launch.risk_score,
                token_launch.risk_level,
                json.dumps(token_launch.risk_factors),
                token_launch.etherscan_verified,
                token_launch.source_code_available
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
                    'risk_factors': json.loads(row[9]) if row[9] else [],
                    'etherscan_verified': bool(row[11]) if len(row) > 11 else False,
                    'source_code_available': bool(row[12]) if len(row) > 12 else False
                })
            
            return tokens
            
        except Exception as e:
            logger.error(f"Error getting recent tokens: {e}")
            return []
    
    async def is_actual_token(self, web3, contract_address):
        """
        Check if a contract is actually a tradeable token (not just any contract)
        """
        try:
            # Get contract code
            code = web3.eth.get_code(contract_address)
            code_hex = code.hex()
            
            # Check for ERC20 function signatures
            erc20_signatures = {
                '0x70a08231': 'balanceOf(address)',
                '0xa9059cbb': 'transfer(address,uint256)', 
                '0x095ea7b3': 'approve(address,uint256)',
                '0xdd62ed3e': 'allowance(address,address)',
                '0x18160ddd': 'totalSupply()',
                '0x06fdde03': 'name()',
                '0x95d89b41': 'symbol()',
                '0x313ce567': 'decimals()'
            }
            
            # Count how many ERC20 functions are present
            erc20_functions_found = 0
            for sig in erc20_signatures.keys():
                if sig[2:] in code_hex:  # Remove '0x' prefix
                    erc20_functions_found += 1
            
            # Must have at least 6 core ERC20 functions to be considered a token
            if erc20_functions_found < 6:
                return False, f"Only {erc20_functions_found}/8 ERC20 functions found"
            
            # Try to call basic ERC20 functions to verify they work
            try:
                # Try to get total supply
                total_supply_call = web3.eth.call({
                    'to': contract_address,
                    'data': '0x18160ddd'  # totalSupply()
                })
                
                # Try to get decimals
                decimals_call = web3.eth.call({
                    'to': contract_address,
                    'data': '0x313ce567'  # decimals()
                })
                
                # If both calls succeed, likely a real token
                if len(total_supply_call) > 0 and len(decimals_call) > 0:
                    return True, f"Valid ERC20 token ({erc20_functions_found}/8 functions)"
                
            except Exception as e:
                return False, f"ERC20 function calls failed: {str(e)[:50]}"
            
            return False, "Failed ERC20 function verification"
            
        except Exception as e:
            return False, f"Contract analysis failed: {str(e)[:50]}"

    async def get_token_info(self, web3, contract_address):
        """
        Get actual token name, symbol, and decimals
        """
        try:
            # Try to get name
            name = "Unknown"
            try:
                name_call = web3.eth.call({
                    'to': contract_address,
                    'data': '0x06fdde03'  # name()
                })
                if len(name_call) > 32:
                    # Decode string (simplified)
                    name_bytes = name_call[64:]  # Skip length data
                    name = name_bytes.decode('utf-8', errors='ignore').strip('\x00')
                    if not name or len(name) < 2:
                        name = f"Token_{contract_address[2:8]}"
            except:
                name = f"Token_{contract_address[2:8]}"
            
            # Try to get symbol
            symbol = "UNK"
            try:
                symbol_call = web3.eth.call({
                    'to': contract_address,
                    'data': '0x95d89b41'  # symbol()
                })
                if len(symbol_call) > 32:
                    # Decode string (simplified)
                    symbol_bytes = symbol_call[64:]  # Skip length data
                    symbol = symbol_bytes.decode('utf-8', errors='ignore').strip('\x00')
                    if not symbol or len(symbol) < 1:
                        symbol = f"T{contract_address[2:6].upper()}"
            except:
                symbol = f"T{contract_address[2:6].upper()}"
            
            # Try to get decimals
            decimals = 18  # Default
            try:
                decimals_call = web3.eth.call({
                    'to': contract_address,
                    'data': '0x313ce567'  # decimals()
                })
                if len(decimals_call) == 32:
                    decimals = int.from_bytes(decimals_call, byteorder='big')
                    if decimals > 50:  # Sanity check
                        decimals = 18
            except:
                decimals = 18
            
            return name, symbol, decimals
            
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return f"Token_{contract_address[2:8]}", f"T{contract_address[2:6].upper()}", 18


# Global monitor instance
monitor = EnhancedTokenMonitor()

# Enhanced Dashboard HTML
ENHANCED_DASHBOARD = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 Enhanced Token Launch Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
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
        .token-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
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
        .verified-badge {
            background: #d4edda; color: #155724; padding: 2px 8px;
            border-radius: 12px; font-size: 0.8em; margin-left: 10px;
        }
        .risk-factors { margin-top: 10px; }
        .risk-factors ul { margin-left: 20px; }
        .risk-factors li { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Enhanced Token Launch Monitor</h1>
            <p>Real-time token detection with Etherscan verification</p>
        </div>

        <div class="status-panel">
            <h3>🎛️ Monitor Status</h3>
            <div style="display: flex; align-items: center; margin: 15px 0;">
                <div class="status-indicator" id="statusIndicator"></div>
                <span id="statusText">Checking status...</span>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="startMonitoring()">▶️ Start Enhanced Monitoring</button>
                <button class="btn danger" onclick="stopMonitoring()">⏹️ Stop Monitoring</button>
                <button class="btn" onclick="testEtherscan()">🔍 Test Etherscan API</button>
                <button class="btn" onclick="refreshData()">🔄 Refresh Data</button>
            </div>
        </div>

        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-value" id="totalTokens">-</div>
                <div class="stat-label">Tokens Detected (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="verifiedTokens">-</div>
                <div class="stat-label">Verified Contracts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="highRiskTokens">-</div>
                <div class="stat-label">High Risk Tokens</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avgRiskScore">-</div>
                <div class="stat-label">Avg Risk Score</div>
            </div>
        </div>

        <div class="tokens-list">
            <h3>🆕 Recently Detected Tokens</h3>
            <div style="color: #666; font-size: 0.9em; margin: 10px 0;">
                Auto-refreshing every 20 seconds | Demo mode active for testing
            </div>
            <div id="tokensList">
                <p style="text-align: center; color: #666; margin: 40px 0;">
                    No tokens detected yet. Start monitoring to see results!
                </p>
            </div>
        </div>
    </div>

    <script>
        let isMonitoring = false;
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/enhanced/status');
                const data = await response.json();
                
                const indicator = document.getElementById('statusIndicator');
                const statusText = document.getElementById('statusText');
                
                if (data.monitoring) {
                    indicator.className = 'status-indicator status-running';
                    statusText.textContent = `Enhanced monitoring active - Connected to ${data.connected_chains.join(', ')}`;
                    isMonitoring = true;
                } else {
                    indicator.className = 'status-indicator status-stopped';
                    statusText.textContent = 'Enhanced monitoring stopped';
                    isMonitoring = false;
                }
            } catch (error) {
                console.error('Error checking status:', error);
            }
        }
        
        async function startMonitoring() {
            try {
                const response = await fetch('/api/enhanced/monitoring/start', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                checkStatus();
            } catch (error) {
                alert('Error starting monitoring: ' + error.message);
            }
        }
        
        async function stopMonitoring() {
            try {
                const response = await fetch('/api/enhanced/monitoring/stop', { method: 'POST' });
                const data = await response.json();
                alert(data.message);
                checkStatus();
            } catch (error) {
                alert('Error stopping monitoring: ' + error.message);
            }
        }
        
        async function testEtherscan() {
            try {
                const response = await fetch('/api/enhanced/etherscan/test');
                const data = await response.json();
                alert('Etherscan API Test: ' + data.message);
            } catch (error) {
                alert('Error testing Etherscan API: ' + error.message);
            }
        }
        
        async function loadTokens() {
            try {
                const response = await fetch('/api/enhanced/tokens/recent');
                const data = await response.json();
                
                const tokensList = document.getElementById('tokensList');
                
                if (data.tokens && data.tokens.length > 0) {
                    tokensList.innerHTML = data.tokens.map(token => `
                        <div class="token-item">
                            <div class="token-header">
                                <div class="token-name">
                                    ${token.name} (${token.symbol})
                                    ${token.etherscan_verified ? '<span class="verified-badge">✅ Verified</span>' : ''}
                                </div>
                                <div class="risk-badge risk-${token.risk_level}">${token.risk_level}</div>
                            </div>
                            <div class="token-details">
                                <div><strong>Chain:</strong> ${token.chain.toUpperCase()}</div>
                                <div><strong>Contract:</strong> ${token.contract_address}</div>
                                <div><strong>Creator:</strong> ${token.creator_address}</div>
                                <div><strong>Risk Score:</strong> ${(token.risk_score * 100).toFixed(1)}%</div>
                                <div><strong>Created:</strong> ${new Date(token.creation_time).toLocaleString()}</div>
                                <div><strong>Source Code:</strong> ${token.source_code_available ? '✅ Available' : '❌ Not Available'}</div>
                                ${token.risk_factors.length > 0 ? `
                                    <div class="risk-factors">
                                        <strong>Risk Analysis:</strong>
                                        <ul>
                                            ${token.risk_factors.map(factor => `<li>${factor}</li>`).join('')}
                                        </ul>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `).join('');
                    
                    // Update stats
                    const totalTokens = data.tokens.length;
                    const verifiedTokens = data.tokens.filter(t => t.etherscan_verified).length;
                    const highRiskTokens = data.tokens.filter(t => t.risk_level === 'HIGH' || t.risk_level === 'CRITICAL').length;
                    const avgRiskScore = totalTokens > 0 ? 
                        (data.tokens.reduce((sum, t) => sum + t.risk_score, 0) / totalTokens * 100).toFixed(1) + '%' : '0%';
                    
                    document.getElementById('totalTokens').textContent = totalTokens;
                    document.getElementById('verifiedTokens').textContent = verifiedTokens;
                    document.getElementById('highRiskTokens').textContent = highRiskTokens;
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
        
        // Auto-refresh every 20 seconds
        setInterval(refreshData, 20000);
    </script>
</body>
</html>
'''

@app.route('/')
def enhanced_dashboard():
    return render_template_string(ENHANCED_DASHBOARD)

@app.route('/api/enhanced/status')
def get_enhanced_status():
    return jsonify({
        'status': 'success',
        'monitoring': monitor.monitoring,
        'connected_chains': list(monitor.web3_clients.keys()),
        'etherscan_enabled': monitor.config.get('etherscan', {}).get('enabled', False),
        'database': os.path.exists(monitor.db_path),
        'demo_mode': monitor.demo_mode,
        'version': '2.1.0-enhanced'
    })

@app.route('/api/enhanced/monitoring/start', methods=['POST'])
def start_enhanced_monitoring():
    if monitor.monitoring:
        return jsonify({
            'status': 'error',
            'message': 'Enhanced monitoring is already running'
        }), 400
    
    monitor.monitoring = True
    
    # Start enhanced monitoring in background thread
    def run_enhanced_monitor():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.monitor_enhanced())
    
    thread = threading.Thread(target=run_enhanced_monitor, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': '🔍 Enhanced monitoring started with Etherscan integration!',
        'features': {
            'real_time_detection': True,
            'etherscan_verification': True,
            'enhanced_risk_analysis': True,
            'demo_mode': monitor.demo_mode
        }
    })

@app.route('/api/enhanced/monitoring/stop', methods=['POST'])
def stop_enhanced_monitoring():
    if not monitor.monitoring:
        return jsonify({
            'status': 'error',
            'message': 'Enhanced monitoring is not running'
        }), 400
    
    monitor.monitoring = False
    
    return jsonify({
        'status': 'success',
        'message': 'Enhanced monitoring stopped'
    })

@app.route('/api/enhanced/etherscan/test')
def test_etherscan():
    try:
        etherscan_config = monitor.config.get('etherscan', {})
        if not etherscan_config.get('enabled', False):
            return jsonify({
                'status': 'error',
                'message': 'Etherscan integration is disabled in config'
            })
        
        networks = etherscan_config.get('networks', {})
        configured_networks = []
        
        for network, config in networks.items():
            if config.get('api_key') and 'YOUR_' not in config['api_key']:
                configured_networks.append(network)
        
        if not configured_networks:
            return jsonify({
                'status': 'error',
                'message': 'No Etherscan API keys configured. Please update your config with real API keys.'
            })
        
        return jsonify({
            'status': 'success',
            'message': f'Etherscan API configured for: {", ".join(configured_networks)}',
            'networks': configured_networks,
            'features': {
                'contract_verification': True,
                'source_code_analysis': True,
                'enhanced_risk_scoring': True
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/enhanced/tokens/recent')
def get_enhanced_recent_tokens():
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    tokens = monitor.get_recent_tokens(hours=hours, limit=limit)
    
    return jsonify({
        'status': 'success',
        'tokens': tokens,
        'count': len(tokens),
        'enhanced_features': {
            'etherscan_verification': True,
            'source_code_analysis': True,
            'creator_reputation': True
        }
    })

@app.route('/api/enhanced/analyze/<chain>/<address>')
def analyze_enhanced_token(chain, address):
    try:
        async def run_analysis():
            # Get Etherscan verification
            etherscan_data = await monitor.check_etherscan_verification(chain, address)
            
            # Enhanced risk analysis
            risk_score, risk_level, risk_factors = monitor.analyze_contract_risk_enhanced(
                chain, address, "0x0000000000000000000000000000000000000000", etherscan_data
            )
            
            return {
                'contract_address': address,
                'chain': chain,
                'etherscan_verification': etherscan_data,
                'risk_analysis': {
                    'risk_score': risk_score,
                    'risk_level': risk_level,
                    'risk_factors': risk_factors
                },
                'analysis_time': datetime.now().isoformat(),
                'enhanced_features': True
            }
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_analysis())
        
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Enhanced Token Launch Monitor with Etherscan Integration...")
    print("🔗 Connected chains:", list(monitor.web3_clients.keys()))
    print("🔍 Etherscan enabled:", monitor.config.get('etherscan', {}).get('enabled', False))
    print("📊 Enhanced Dashboard: http://localhost:5000")
    print("🔧 Enhanced API: http://localhost:5000/api/enhanced/*")
    print()
    print("✨ Enhanced Features:")
    print("  • Real-time token detection with demo mode")
    print("  • Etherscan contract verification")
    print("  • Enhanced risk analysis with multiple factors")
    print("  • Source code availability checking")
    print("  • Creator reputation analysis")
    print("  • Live dashboard with detailed token information")
    print()
    print("🎯 Demo Mode: Enabled (generates test tokens for demonstration)")
    print("🔑 API Keys: Configure in config_etherscan.json")
    print()
    
    app.run(host='0.0.0.0', port=5001, debug=True)  # Using port 5001 to avoid conflicts