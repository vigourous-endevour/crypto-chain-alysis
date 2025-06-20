# Save this as: etherscan_analyzer.py

import aiohttp
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EtherscanContractInfo:
    """Etherscan contract verification and source code info"""
    is_verified: bool
    source_code: str
    contract_name: str
    compiler_version: str
    optimization_used: bool
    runs: int
    constructor_arguments: str
    evm_version: str
    library: str
    license_type: str
    proxy: bool
    implementation: str
    swarm_source: str

@dataclass
class EtherscanTokenInfo:
    """Token information from Etherscan"""
    name: str
    symbol: str
    decimals: int
    total_supply: str
    contract_address: str
    holders_count: int
    transfers_count: int
    is_verified: bool
    creation_block: int
    creation_tx: str
    creator_address: str

class EtherscanAPI:
    """Enhanced Etherscan API client for comprehensive token analysis"""
    
    def __init__(self, api_key: str, network: str = "mainnet"):
        self.api_key = api_key
        self.network = network
        self.base_urls = {
            "mainnet": "https://api.etherscan.io/api",
            "goerli": "https://api-goerli.etherscan.io/api",
            "sepolia": "https://api-sepolia.etherscan.io/api",
            "base": "https://api.basescan.org/api",
            "base-goerli": "https://api-goerli.basescan.org/api"
        }
        self.base_url = self.base_urls.get(network, self.base_urls["mainnet"])
        self.rate_limit_delay = 0.2  # 5 requests per second max
        self.last_request_time = 0
        
    async def _make_request(self, params: Dict) -> Dict:
        """Make rate-limited request to Etherscan API"""
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        params['apikey'] = self.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    self.last_request_time = time.time()
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            return data
                        else:
                            logger.warning(f"Etherscan API error: {data.get('message', 'Unknown error')}")
                            return {}
                    else:
                        logger.error(f"HTTP error {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {}
    
    async def get_contract_source_code(self, contract_address: str) -> EtherscanContractInfo:
        """Get contract source code and verification status"""
        params = {
            'module': 'contract',
            'action': 'getsourcecode',
            'address': contract_address
        }
        
        data = await self._make_request(params)
        
        if data and 'result' in data and data['result']:
            result = data['result'][0]
            return EtherscanContractInfo(
                is_verified=bool(result.get('SourceCode')),
                source_code=result.get('SourceCode', ''),
                contract_name=result.get('ContractName', ''),
                compiler_version=result.get('CompilerVersion', ''),
                optimization_used=result.get('OptimizationUsed') == '1',
                runs=int(result.get('Runs', 0)) if result.get('Runs') else 0,
                constructor_arguments=result.get('ConstructorArguments', ''),
                evm_version=result.get('EVMVersion', ''),
                library=result.get('Library', ''),
                license_type=result.get('LicenseType', ''),
                proxy=result.get('Proxy') == '1',
                implementation=result.get('Implementation', ''),
                swarm_source=result.get('SwarmSource', '')
            )
        
        return EtherscanContractInfo(
            is_verified=False, source_code='', contract_name='', 
            compiler_version='', optimization_used=False, runs=0,
            constructor_arguments='', evm_version='', library='',
            license_type='', proxy=False, implementation='', swarm_source=''
        )
    
    async def analyze_contract_security(self, contract_address: str) -> Dict:
        """Analyze contract for security issues using Etherscan data"""
        contract_info = await self.get_contract_source_code(contract_address)
        
        security_analysis = {
            'verified': contract_info.is_verified,
            'proxy_contract': contract_info.proxy,
            'has_source_code': bool(contract_info.source_code),
            'optimization_enabled': contract_info.optimization_used,
            'license_specified': bool(contract_info.license_type),
            'risk_factors': [],
            'security_score': 0.0
        }
        
        # Calculate security score
        score = 0.0
        max_score = 100.0
        
        if contract_info.is_verified:
            score += 30
        else:
            security_analysis['risk_factors'].append('Contract not verified')
        
        if contract_info.source_code:
            score += 20
            # Analyze source code for common patterns
            source_lower = contract_info.source_code.lower()
            
            # Check for suspicious patterns
            if 'selfdestruct' in source_lower:
                security_analysis['risk_factors'].append('Contains selfdestruct function')
                score -= 15
            
            if 'onlyowner' in source_lower or 'owner' in source_lower:
                if 'renounceownership' not in source_lower:
                    security_analysis['risk_factors'].append('Owner privileges without renouncement')
                    score -= 10
            
            if 'mint' in source_lower and 'function mint' in source_lower:
                security_analysis['risk_factors'].append('Has mint function - inflation risk')
                score -= 10
            
            if 'pause' in source_lower:
                security_analysis['risk_factors'].append('Has pause functionality')
                score -= 5
            
            # Check for common security features
            if 'reentrancyguard' in source_lower or 'nonreentrant' in source_lower:
                score += 10
            
            if 'safemath' in source_lower or 'pragma solidity ^0.8' in source_lower:
                score += 5
        
        if contract_info.proxy:
            security_analysis['risk_factors'].append('Proxy contract - implementation can change')
            score -= 15
        
        if not contract_info.license_type:
            security_analysis['risk_factors'].append('No license specified')
            score -= 5
        
        security_analysis['security_score'] = max(0, min(100, score))
        
        return security_analysis
    
    async def check_address_reputation(self, address: str) -> Dict:
        """Check address reputation based on transaction history"""
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 999999999,
            'page': 1,
            'offset': 100,
            'sort': 'desc'
        }
        
        data = await self._make_request(params)
        transactions = data.get('result', []) if data else []
        
        analysis = {
            'transaction_count': len(transactions),
            'is_new_address': len(transactions) < 5,
            'avg_gas_price': 0,
            'contract_interactions': 0,
            'unique_counterparts': set(),
            'suspicious_patterns': [],
            'reputation_score': 50  # Default neutral score
        }
        
        if not transactions:
            analysis['suspicious_patterns'].append('No transaction history')
            analysis['reputation_score'] = 10
            return analysis
        
        total_gas = 0
        for tx in transactions:
            gas_price = int(tx.get('gasPrice', 0))
            total_gas += gas_price
            
            # Check for contract interactions
            if tx.get('input', '0x') != '0x':
                analysis['contract_interactions'] += 1
            
            # Track unique addresses
            analysis['unique_counterparts'].add(tx.get('to', '').lower())
            analysis['unique_counterparts'].add(tx.get('from', '').lower())
        
        if transactions:
            analysis['avg_gas_price'] = total_gas / len(transactions)
        
        # Convert set to count
        analysis['unique_counterparts'] = len(analysis['unique_counterparts'])
        
        # Reputation scoring
        if len(transactions) < 5:
            analysis['suspicious_patterns'].append('Very low transaction count')
            analysis['reputation_score'] -= 20
        
        if analysis['contract_interactions'] == 0:
            analysis['suspicious_patterns'].append('No smart contract interactions')
            analysis['reputation_score'] -= 10
        
        if analysis['unique_counterparts'] < 3:
            analysis['suspicious_patterns'].append('Limited interaction with other addresses')
            analysis['reputation_score'] -= 15
        
        # Positive indicators
        if len(transactions) > 50:
            analysis['reputation_score'] += 20
        
        if analysis['contract_interactions'] > len(transactions) * 0.5:
            analysis['reputation_score'] += 10
        
        analysis['reputation_score'] = max(0, min(100, analysis['reputation_score']))
        
        return analysis