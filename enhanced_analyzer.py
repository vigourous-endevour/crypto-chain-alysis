import asyncio
import aiohttp
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import logging
from web3 import Web3

logger = logging.getLogger(__name__)

@dataclass
class ContractAnalysis:
    """Detailed contract analysis results"""
    has_mint_function: bool
    has_burn_function: bool
    has_pause_function: bool
    ownership_renounced: bool
    liquidity_locked: bool
    max_transaction_limit: Optional[int]
    max_wallet_limit: Optional[int]
    honeypot_risk: float
    contract_verified: bool
    proxy_contract: bool

class AdvancedRiskAnalyzer:
    """Enhanced risk analysis with additional checks"""
    
    def __init__(self, web3_client: Web3):
        self.web3 = web3_client
        self.honeypot_patterns = [
            b'\x8d\xa5\xcb[\x00\x00\x00\x00',  # Common honeypot bytecode pattern
            b'\x63\x91\x3d\x29\x14',           # Transfer restriction pattern
        ]
        
        # Known scammer addresses (this would be populated from threat intel)
        self.known_scammer_addresses = set([
            "0x0000000000000000000000000000000000000000",  # Example addresses
        ])
        
        # Legitimate project patterns
        self.legitimate_patterns = [
            r'(?i)(uniswap|sushiswap|pancakeswap)',
            r'(?i)(compound|aave|maker)',
            r'(?i)(chainlink|polygon|avalanche)',
        ]

    async def analyze_contract_code(self, contract_address: str) -> ContractAnalysis:
        """Perform deep contract code analysis"""
        try:
            code = self.web3.eth.get_code(contract_address)
            code_hex = code.hex()
            
            # Check for common function signatures
            has_mint = '40c10f19' in code_hex  # mint(address,uint256)
            has_burn = '42966c68' in code_hex  # burn(uint256)
            has_pause = '8456cb59' in code_hex  # pause()
            
            # Check for ownership patterns
            ownership_renounced = self._check_ownership_renounced(code_hex)
            
            # Check for honeypot patterns
            honeypot_risk = self._analyze_honeypot_risk(code)
            
            # Check if contract is verified (would need etherscan API)
            contract_verified = await self._check_contract_verification(contract_address)
            
            # Check if it's a proxy contract
            proxy_contract = self._check_proxy_pattern(code_hex)
            
            return ContractAnalysis(
                has_mint_function=has_mint,
                has_burn_function=has_burn,
                has_pause_function=has_pause,
                ownership_renounced=ownership_renounced,
                liquidity_locked=False,  # Would need DEX analysis
                max_transaction_limit=None,  # Would need to parse contract
                max_wallet_limit=None,  # Would need to parse contract
                honeypot_risk=honeypot_risk,
                contract_verified=contract_verified,
                proxy_contract=proxy_contract
            )
            
        except Exception as e:
            logger.error(f"Error analyzing contract code: {e}")
            return ContractAnalysis(
                has_mint_function=False,
                has_burn_function=False,
                has_pause_function=False,
                ownership_renounced=False,
                liquidity_locked=False,
                max_transaction_limit=None,
                max_wallet_limit=None,
                honeypot_risk=0.0,
                contract_verified=False,
                proxy_contract=False
            )

    def _check_ownership_renounced(self, code_hex: str) -> bool:
        """Check if ownership has been renounced"""
        # Look for renounceOwnership function and zero address transfer
        renounce_pattern = '715018a6'  # renounceOwnership()
        return renounce_pattern in code_hex

    def _analyze_honeypot_risk(self, code: bytes) -> float:
        """Analyze code for honeypot patterns"""
        risk_score = 0.0
        
        for pattern in self.honeypot_patterns:
            if pattern in code:
                risk_score += 0.3
        
        # Check for unusual gas usage patterns
        if len(code) > 50000:  # Very large contracts can hide malicious code
            risk_score += 0.2
            
        return min(risk_score, 1.0)

    async def _check_contract_verification(self, contract_address: str) -> bool:
        """Check if contract is verified on Etherscan"""
        try:
            # This would require Etherscan API key
            etherscan_api_key = "YOUR_ETHERSCAN_API_KEY"
            url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={contract_address}&apikey={etherscan_api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    if data['status'] == '1' and data['result'][0]['SourceCode']:
                        return True
            return False
        except:
            return False

    def _check_proxy_pattern(self, code_hex: str) -> bool:
        """Check if contract follows proxy pattern"""
        proxy_patterns = [
            '3660008037',  # Common proxy delegatecall pattern
            '36103d601c',  # EIP-1167 minimal proxy pattern
        ]
        
        return any(pattern in code_hex for pattern in proxy_patterns)

    async def analyze_liquidity_pools(self, token_address: str) -> Dict:
        """Analyze DEX liquidity pools for the token"""
        try:
            # Check Uniswap V2/V3 pools
            uniswap_data = await self._check_uniswap_pools(token_address)
            
            # Check other DEXes
            sushiswap_data = await self._check_sushiswap_pools(token_address)
            
            return {
                'uniswap': uniswap_data,
                'sushiswap': sushiswap_data,
                'total_liquidity_usd': 0,  # Would calculate from pool data
                'pool_count': 0,
                'largest_pool': None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing liquidity pools: {e}")
            return {}

    async def _check_uniswap_pools(self, token_address: str) -> Dict:
        """Check Uniswap pools for the token"""
        # This would integrate with Uniswap subgraph or direct contract calls
        return {}

    async def _check_sushiswap_pools(self, token_address: str) -> Dict:
        """Check SushiSwap pools for the token"""
        return {}

    async def analyze_holder_distribution(self, token_address: str) -> Dict:
        """Analyze token holder distribution"""
        try:
            # Get transfer events to analyze holder distribution
            transfer_signature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            
            latest_block = self.web3.eth.get_block('latest')
            from_block = max(0, latest_block['number'] - 10000)
            
            logs = self.web3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': 'latest',
                'address': token_address,
                'topics': [transfer_signature]
            })
            
            holders = {}
            total_transfers = len(logs)
            
            for log in logs:
                if len(log['topics']) >= 3:
                    to_address = '0x' + log['topics'][2].hex()[26:]
                    holders[to_address] = holders.get(to_address, 0) + 1
            
            # Calculate distribution metrics
            unique_holders = len(holders)
            if unique_holders > 0:
                avg_transactions_per_holder = total_transfers / unique_holders
                top_holders = sorted(holders.values(), reverse=True)[:10]
                concentration_ratio = sum(top_holders[:5]) / total_transfers if total_transfers > 0 else 0
            else:
                avg_transactions_per_holder = 0
                concentration_ratio = 0
            
            return {
                'unique_holders': unique_holders,
                'total_transfers': total_transfers,
                'avg_transactions_per_holder': avg_transactions_per_holder,
                'concentration_ratio': concentration_ratio,
                'holder_growth_rate': 0  # Would need historical data
            }
            
        except Exception as e:
            logger.error(f"Error analyzing holder distribution: {e}")
            return {}

    async def check_social_signals(self, token_name: str, token_symbol: str) -> Dict:
        """Check social media signals and online presence"""
        try:
            signals = {
                'twitter_followers': 0,
                'telegram_members': 0,
                'discord_members': 0,
                'reddit_subscribers': 0,
                'website_exists': False,
                'whitepaper_exists': False,
                'github_activity': 0,
                'social_sentiment': 0.0
            }
            
            # This would integrate with social media APIs
            # For now, return placeholder data
            return signals
            
        except Exception as e:
            logger.error(f"Error checking social signals: {e}")
            return {}

    async def analyze_trading_patterns(self, token_address: str) -> Dict:
        """Analyze trading patterns for suspicious activity"""
        try:
            # Get recent transactions
            latest_block = self.web3.eth.get_block('latest')
            from_block = max(0, latest_block['number'] - 1000)
            
            # Analyze transaction patterns
            transfer_logs = self.web3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': 'latest',
                'address': token_address,
                'topics': ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
            })
            
            # Calculate metrics
            transaction_count = len(transfer_logs)
            unique_addresses = set()
            
            for log in transfer_logs:
                if len(log['topics']) >= 3:
                    from_addr = '0x' + log['topics'][1].hex()[26:]
                    to_addr = '0x' + log['topics'][2].hex()[26:]
                    unique_addresses.add(from_addr)
                    unique_addresses.add(to_addr)
            
            return {
                'transaction_count': transaction_count,
                'unique_traders': len(unique_addresses),
                'trading_velocity': transaction_count / 1000,  # transactions per block
                'wash_trading_risk': 0.0,  # Would need more sophisticated analysis
                'pump_dump_risk': 0.0,     # Would analyze price movements
                'bot_activity_detected': False
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trading patterns: {e}")
            return {}

class EnhancedTokenAnalyzer:
    """Enhanced token analyzer with comprehensive risk assessment"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.web3_eth = Web3(Web3.HTTPProvider(config['ethereum']['rpc_url']))
        self.risk_analyzer = AdvancedRiskAnalyzer(self.web3_eth)

    async def comprehensive_analysis(self, contract_address: str, 
                                   creator_address: str, name: str, 
                                   symbol: str, total_supply: int) -> Tuple[float, List[str], Dict]:
        """Perform comprehensive risk analysis"""
        
        risk_factors = []
        risk_score = 0.0
        analysis_data = {}
        
        # 1. Contract code analysis
        contract_analysis = await self.risk_analyzer.analyze_contract_code(contract_address)
        analysis_data['contract_analysis'] = contract_analysis
        
        if contract_analysis.has_mint_function:
            risk_factors.append("Contract has mint function - inflation risk")
            risk_score += 0.2
            
        if not contract_analysis.ownership_renounced:
            risk_factors.append("Ownership not renounced - centralization risk")
            risk_score += 0.3
            
        if contract_analysis.honeypot_risk > 0.5:
            risk_factors.append("High honeypot risk detected")
            risk_score += 0.4
            
        if not contract_analysis.contract_verified:
            risk_factors.append("Contract not verified")
            risk_score += 0.2
        
        # 2. Liquidity analysis
        liquidity_data = await self.risk_analyzer.analyze_liquidity_pools(contract_address)
        analysis_data['liquidity_analysis'] = liquidity_data
        
        # 3. Holder distribution analysis
        holder_data = await self.risk_analyzer.analyze_holder_distribution(contract_address)
        analysis_data['holder_analysis'] = holder_data
        
        if holder_data.get('concentration_ratio', 0) > 0.8:
            risk_factors.append("High holder concentration")
            risk_score += 0.3
            
        if holder_data.get('unique_holders', 0) < 10:
            risk_factors.append("Very few holders")
            risk_score += 0.2
        
        # 4. Social signals analysis
        social_data = await self.risk_analyzer.check_social_signals(name, symbol)
        analysis_data['social_analysis'] = social_data
        
        if not social_data.get('website_exists', False):
            risk_factors.append("No official website found")
            risk_score += 0.1
            
        if social_data.get('twitter_followers', 0) < 100:
            risk_factors.append("Low social media presence")
            risk_score += 0.1
        
        # 5. Trading pattern analysis
        trading_data = await self.risk_analyzer.analyze_trading_patterns(contract_address)
        analysis_data['trading_analysis'] = trading_data
        
        if trading_data.get('wash_trading_risk', 0) > 0.7:
            risk_factors.append("Suspected wash trading")
            risk_score += 0.3
            
        if trading_data.get('bot_activity_detected', False):
            risk_factors.append("Bot trading activity detected")
            risk_score += 0.2
        
        # 6. Creator address analysis
        creator_tx_count = self.web3_eth.eth.get_transaction_count(creator_address)
        creator_balance = self.web3_eth.eth.get_balance(creator_address)
        
        if creator_tx_count < 5:
            risk_factors.append("New/low-activity creator address")
            risk_score += 0.3
            
        if creator_balance < self.web3_eth.to_wei(0.01, 'ether'):
            risk_factors.append("Creator has very low ETH balance")
            risk_score += 0.2
        
        # Check if creator is a known scammer
        if creator_address.lower() in self.risk_analyzer.known_scammer_addresses:
            risk_factors.append("Creator address flagged as scammer")
            risk_score += 0.8
        
        # 7. Name and symbol analysis
        suspicious_patterns = [
            r'(?i)(elon|musk|tesla|doge|shib|inu)',
            r'(?i)(moon|rocket|pump|safe|secure)',
            r'(?i)(x100|1000x|lambo|gem)',
            r'(?i)(pepe|wojak|chad)',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, name) or re.search(pattern, symbol):
                risk_factors.append("Suspicious name/symbol pattern")
                risk_score += 0.2
                break
        
        # Check for legitimate patterns
        for pattern in self.risk_analyzer.legitimate_patterns:
            if re.search(pattern, name) or re.search(pattern, symbol):
                risk_score -= 0.2  # Reduce risk for legitimate-sounding names
                break
        
        # 8. Supply analysis
        if total_supply > 10**21:  # Extremely high supply
            risk_factors.append("Extremely high token supply")
            risk_score += 0.3
        elif total_supply > 10**18:  # Very high supply
            risk_factors.append("Very high token supply")
            risk_score += 0.1
        
        # 9. Timeline analysis
        current_time = datetime.now()
        # If token was created very recently (< 1 hour), add risk
        # This would need creation timestamp
        
        return min(risk_score, 1.0), risk_factors, analysis_data

    def generate_risk_report(self, token_launch, analysis_data: Dict) -> str:
        """Generate detailed risk assessment report"""
        
        report = f"""
=== TOKEN RISK ASSESSMENT REPORT ===

Token: {token_launch.name} ({token_launch.symbol})
Chain: {token_launch.chain.upper()}
Contract: {token_launch.contract_address}
Creator: {token_launch.creator_address}

RISK LEVEL: {token_launch.risk_level.value}
RISK SCORE: {token_launch.risk_score:.2f}/1.0

=== CONTRACT ANALYSIS ===
"""
        
        if 'contract_analysis' in analysis_data:
            ca = analysis_data['contract_analysis']
            report += f"""
- Mint Function: {"Yes" if ca.has_mint_function else "No"}
- Burn Function: {"Yes" if ca.has_burn_function else "No"}
- Pause Function: {"Yes" if ca.has_pause_function else "No"}
- Ownership Renounced: {"Yes" if ca.ownership_renounced else "No"}
- Contract Verified: {"Yes" if ca.contract_verified else "No"}
- Proxy Contract: {"Yes" if ca.proxy_contract else "No"}
- Honeypot Risk: {ca.honeypot_risk:.2f}/1.0
"""
        
        if 'holder_analysis' in analysis_data:
            ha = analysis_data['holder_analysis']
            report += f"""
=== HOLDER ANALYSIS ===
- Unique Holders: {ha.get('unique_holders', 'Unknown')}
- Total Transfers: {ha.get('total_transfers', 'Unknown')}
- Concentration Ratio: {ha.get('concentration_ratio', 0):.2f}
- Avg Transactions/Holder: {ha.get('avg_transactions_per_holder', 0):.1f}
"""
        
        if 'trading_analysis' in analysis_data:
            ta = analysis_data['trading_analysis']
            report += f"""
=== TRADING ANALYSIS ===
- Transaction Count: {ta.get('transaction_count', 'Unknown')}
- Unique Traders: {ta.get('unique_traders', 'Unknown')}
- Trading Velocity: {ta.get('trading_velocity', 0):.3f} tx/block
- Wash Trading Risk: {ta.get('wash_trading_risk', 0):.2f}/1.0
- Bot Activity: {"Detected" if ta.get('bot_activity_detected', False) else "Not Detected"}
"""
        
        if token_launch.risk_factors:
            report += f"""
=== RISK FACTORS ===
"""
            for i, factor in enumerate(token_launch.risk_factors, 1):
                report += f"{i}. {factor}\n"
        
        report += f"""
=== RECOMMENDATION ===
"""
        
        if token_launch.risk_level.value == 'CRITICAL':
            report += "🚨 AVOID - This token shows multiple critical risk factors indicating a high probability of being a scam or rug pull."
        elif token_launch.risk_level.value == 'HIGH':
            report += "⚠️ HIGH CAUTION - This token shows significant risk factors. Thorough research recommended before considering."
        elif token_launch.risk_level.value == 'MEDIUM':
            report += "⚡ MODERATE RISK - Some risk factors present. Due diligence recommended."
        else:
            report += "✅ LOWER RISK - Fewer risk factors detected, but always DYOR (Do Your Own Research)."
        
        report += f"""

Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Disclaimer: This analysis is for informational purposes only. Always conduct your own research.
"""
        
        return report