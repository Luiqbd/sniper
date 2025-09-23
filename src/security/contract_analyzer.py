import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..core.config import Config
from ..core.web3_client import Web3Client
from ..core.logger import logger

@dataclass
class SecurityResult:
    token_address: str
    is_honeypot: bool
    is_verified: bool
    risk_score: float  # 0.0 (safe) to 1.0 (very risky)
    warnings: List[str]
    analysis_timestamp: datetime
    contract_age_hours: Optional[float] = None
    liquidity_locked: Optional[bool] = None
    owner_renounced: Optional[bool] = None
    max_transaction_percent: Optional[float] = None
    buy_tax_percent: Optional[float] = None
    sell_tax_percent: Optional[float] = None

class ContractAnalyzer:
    """Advanced contract security analyzer with honeypot detection and risk assessment."""
    
    def __init__(self, config: Config, web3_client: Web3Client):
        self.config = config
        self.web3_client = web3_client
        
        # Cache for analysis results
        self.analysis_cache: Dict[str, SecurityResult] = {}
        self.cache_duration = timedelta(hours=1)  # Cache results for 1 hour
        
        # Blacklisted addresses (known scams/honeypots)
        self.blacklisted_addresses: Set[str] = set()
        
        # Rate limiting for API calls
        self.last_api_call = {}
        self.api_cooldown = 2  # seconds between API calls
        
        logger.info("ContractAnalyzer initialized")
    
    async def analyze_contract(self, token_address: str) -> SecurityResult:
        """Perform comprehensive security analysis of a token contract."""
        try:
            token_address = token_address.lower()
            
            # Check cache first
            if token_address in self.analysis_cache:
                cached_result = self.analysis_cache[token_address]
                if datetime.now() - cached_result.analysis_timestamp < self.cache_duration:
                    logger.debug("Using cached security analysis", token_address=token_address)
                    return cached_result
            
            # Check blacklist
            if token_address in self.blacklisted_addresses:
                return SecurityResult(
                    token_address=token_address,
                    is_honeypot=True,
                    is_verified=False,
                    risk_score=1.0,
                    warnings=["Token is blacklisted"],
                    analysis_timestamp=datetime.now()
                )
            
            logger.info("Analyzing contract security", token_address=token_address)
            
            # Perform multiple security checks in parallel
            tasks = [
                self._check_honeypot_api(token_address),
                self._analyze_contract_code(token_address),
                self._check_basescan_verification(token_address),
                self._analyze_transaction_patterns(token_address),
                self._check_liquidity_locks(token_address)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            security_result = await self._combine_analysis_results(token_address, results)
            
            # Cache the result
            self.analysis_cache[token_address] = security_result
            
            logger.info("Contract analysis completed", 
                       token_address=token_address,
                       risk_score=security_result.risk_score,
                       is_honeypot=security_result.is_honeypot,
                       warnings_count=len(security_result.warnings))
            
            return security_result
            
        except Exception as e:
            logger.error("Error analyzing contract", token_address=token_address, error=str(e))
            
            # Return high-risk result on error
            return SecurityResult(
                token_address=token_address,
                is_honeypot=True,
                is_verified=False,
                risk_score=1.0,
                warnings=[f"Analysis failed: {str(e)}"],
                analysis_timestamp=datetime.now()
            )
    
    async def _check_honeypot_api(self, token_address: str) -> Dict[str, any]:
        """Check token against honeypot detection APIs."""
        try:
            # Rate limiting
            if token_address in self.last_api_call:
                time_since_last = time.time() - self.last_api_call[token_address]
                if time_since_last < self.api_cooldown:
                    await asyncio.sleep(self.api_cooldown - time_since_last)
            
            self.last_api_call[token_address] = time.time()
            
            # Check multiple honeypot detection services
            results = {}
            
            # Honeypot.is API
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.honeypot.is/v2/IsHoneypot?address={token_address}&chainID=8453"
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            results['honeypot_is'] = {
                                'is_honeypot': data.get('IsHoneypot', False),
                                'buy_tax': data.get('BuyTax', 0),
                                'sell_tax': data.get('SellTax', 0),
                                'max_tx_amount': data.get('MaxTxAmount', 0),
                                'max_tx_amount_percent': data.get('MaxTxAmountPercent', 0)
                            }
            except Exception as e:
                logger.debug("Error checking honeypot.is", error=str(e))
            
            # Token Sniffer API (if available)
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://tokensniffer.com/api/v2/tokens/{token_address}?chainId=8453"
                    headers = {'User-Agent': 'Mozilla/5.0 (compatible; TokenAnalyzer/1.0)'}
                    async with session.get(url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            results['token_sniffer'] = {
                                'score': data.get('score', 0),
                                'is_scam': data.get('is_scam', False),
                                'exploits': data.get('exploits', [])
                            }
            except Exception as e:
                logger.debug("Error checking TokenSniffer", error=str(e))
            
            return results
            
        except Exception as e:
            logger.error("Error in honeypot API check", token_address=token_address, error=str(e))
            return {}
    
    async def _analyze_contract_code(self, token_address: str) -> Dict[str, any]:
        """Analyze contract bytecode for suspicious patterns."""
        try:
            # Get contract code
            code = self.web3_client.w3.eth.get_code(token_address)
            code_hex = code.hex()
            
            warnings = []
            risk_factors = []
            
            # Check for common honeypot patterns
            suspicious_patterns = {
                # Transfer restrictions
                'transfer_restriction': ['a9059cbb', '23b872dd'],  # transfer, transferFrom
                # Ownership patterns
                'ownership_functions': ['8da5cb5b', 'f2fde38b'],  # owner, transferOwnership
                # Pause functionality
                'pause_functions': ['8456cb59', '3f4ba83a'],  # pause, unpause
                # Blacklist functionality
                'blacklist_functions': ['f9f92be4', '608060405'],  # blacklist patterns
                # Mint functions
                'mint_functions': ['40c10f19', 'a0712d68'],  # mint, mintTo
            }
            
            for pattern_name, patterns in suspicious_patterns.items():
                for pattern in patterns:
                    if pattern in code_hex:
                        risk_factors.append(pattern_name)
                        break
            
            # Check contract size (very small contracts are suspicious)
            if len(code_hex) < 1000:
                warnings.append("Contract is unusually small")
                risk_factors.append("small_contract")
            
            # Check for proxy patterns
            proxy_patterns = ['363d3d373d3d3d363d73', '5155f3363d3d373d3d3d']
            is_proxy = any(pattern in code_hex for pattern in proxy_patterns)
            
            return {
                'code_size': len(code_hex),
                'is_proxy': is_proxy,
                'risk_factors': risk_factors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error("Error analyzing contract code", token_address=token_address, error=str(e))
            return {'warnings': ['Failed to analyze contract code']}
    
    async def _check_basescan_verification(self, token_address: str) -> Dict[str, any]:
        """Check if contract is verified on BaseScan."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.basescan.org/api"
                params = {
                    'module': 'contract',
                    'action': 'getsourcecode',
                    'address': token_address,
                    'apikey': self.config.security.basescan_api_key
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == '1' and data.get('result'):
                            result = data['result'][0]
                            
                            is_verified = result.get('SourceCode') != ''
                            contract_name = result.get('ContractName', '')
                            compiler_version = result.get('CompilerVersion', '')
                            
                            return {
                                'is_verified': is_verified,
                                'contract_name': contract_name,
                                'compiler_version': compiler_version,
                                'abi': result.get('ABI', '')
                            }
            
            return {'is_verified': False}
            
        except Exception as e:
            logger.error("Error checking BaseScan verification", token_address=token_address, error=str(e))
            return {'is_verified': False, 'warnings': ['Failed to check verification']}
    
    async def _analyze_transaction_patterns(self, token_address: str) -> Dict[str, any]:
        """Analyze recent transaction patterns for suspicious activity."""
        try:
            # Get recent transactions
            async with aiohttp.ClientSession() as session:
                url = f"https://api.basescan.org/api"
                params = {
                    'module': 'account',
                    'action': 'tokentx',
                    'contractaddress': token_address,
                    'page': 1,
                    'offset': 100,
                    'sort': 'desc',
                    'apikey': self.config.security.basescan_api_key
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == '1' and data.get('result'):
                            transactions = data['result']
                            
                            # Analyze transaction patterns
                            total_txs = len(transactions)
                            failed_txs = sum(1 for tx in transactions if tx.get('isError') == '1')
                            unique_addresses = len(set(tx.get('from') for tx in transactions))
                            
                            # Calculate failure rate
                            failure_rate = failed_txs / total_txs if total_txs > 0 else 0
                            
                            # Check for bot-like activity (many txs from few addresses)
                            bot_activity_score = 1 - (unique_addresses / total_txs) if total_txs > 0 else 0
                            
                            warnings = []
                            if failure_rate > 0.3:
                                warnings.append(f"High transaction failure rate: {failure_rate:.1%}")
                            
                            if bot_activity_score > 0.7:
                                warnings.append("Possible bot activity detected")
                            
                            return {
                                'total_transactions': total_txs,
                                'failed_transactions': failed_txs,
                                'failure_rate': failure_rate,
                                'unique_addresses': unique_addresses,
                                'bot_activity_score': bot_activity_score,
                                'warnings': warnings
                            }
            
            return {'warnings': ['No transaction data available']}
            
        except Exception as e:
            logger.error("Error analyzing transaction patterns", token_address=token_address, error=str(e))
            return {'warnings': ['Failed to analyze transactions']}
    
    async def _check_liquidity_locks(self, token_address: str) -> Dict[str, any]:
        """Check if liquidity is locked."""
        try:
            # This would check popular liquidity locker contracts
            # For now, return placeholder data
            
            # Common liquidity locker addresses on Base
            locker_addresses = [
                '0x663A5C229c09b049E36dCc11a9B0d4a8Eb9db214',  # Unicrypt
                '0x71B5759d73262FBb223956913ecF4ecC51057641',  # Team Finance
                # Add more locker addresses
            ]
            
            # Check if token has locked liquidity
            # This would require checking LP token balances in locker contracts
            
            return {
                'liquidity_locked': None,  # Would be True/False in real implementation
                'lock_duration': None,
                'locked_percentage': None
            }
            
        except Exception as e:
            logger.error("Error checking liquidity locks", token_address=token_address, error=str(e))
            return {}
    
    async def _combine_analysis_results(self, token_address: str, results: List) -> SecurityResult:
        """Combine all analysis results into a final security assessment."""
        try:
            warnings = []
            risk_score = 0.0
            is_honeypot = False
            is_verified = False
            
            # Process honeypot API results
            if len(results) > 0 and isinstance(results[0], dict):
                honeypot_data = results[0]
                
                if 'honeypot_is' in honeypot_data:
                    hp_data = honeypot_data['honeypot_is']
                    if hp_data.get('is_honeypot', False):
                        is_honeypot = True
                        risk_score += 0.8
                        warnings.append("Detected as honeypot by API")
                    
                    # Check taxes
                    buy_tax = hp_data.get('buy_tax', 0)
                    sell_tax = hp_data.get('sell_tax', 0)
                    
                    if buy_tax > 10:
                        risk_score += 0.2
                        warnings.append(f"High buy tax: {buy_tax}%")
                    
                    if sell_tax > 10:
                        risk_score += 0.3
                        warnings.append(f"High sell tax: {sell_tax}%")
                    
                    if sell_tax > 50:
                        is_honeypot = True
                        warnings.append("Extremely high sell tax - likely honeypot")
                
                if 'token_sniffer' in honeypot_data:
                    ts_data = honeypot_data['token_sniffer']
                    if ts_data.get('is_scam', False):
                        is_honeypot = True
                        risk_score += 0.7
                        warnings.append("Flagged as scam by TokenSniffer")
            
            # Process contract code analysis
            if len(results) > 1 and isinstance(results[1], dict):
                code_data = results[1]
                
                risk_factors = code_data.get('risk_factors', [])
                code_warnings = code_data.get('warnings', [])
                
                warnings.extend(code_warnings)
                
                # Add risk based on suspicious patterns
                if 'transfer_restriction' in risk_factors:
                    risk_score += 0.3
                    warnings.append("Contract has transfer restrictions")
                
                if 'blacklist_functions' in risk_factors:
                    risk_score += 0.4
                    warnings.append("Contract can blacklist addresses")
                
                if 'pause_functions' in risk_factors:
                    risk_score += 0.2
                    warnings.append("Contract can be paused")
                
                if 'mint_functions' in risk_factors:
                    risk_score += 0.1
                    warnings.append("Contract can mint new tokens")
            
            # Process verification results
            if len(results) > 2 and isinstance(results[2], dict):
                verification_data = results[2]
                is_verified = verification_data.get('is_verified', False)
                
                if not is_verified:
                    risk_score += 0.2
                    warnings.append("Contract is not verified")
            
            # Process transaction analysis
            if len(results) > 3 and isinstance(results[3], dict):
                tx_data = results[3]
                tx_warnings = tx_data.get('warnings', [])
                warnings.extend(tx_warnings)
                
                failure_rate = tx_data.get('failure_rate', 0)
                if failure_rate > 0.3:
                    risk_score += 0.3
                
                bot_score = tx_data.get('bot_activity_score', 0)
                if bot_score > 0.7:
                    risk_score += 0.2
            
            # Cap risk score at 1.0
            risk_score = min(risk_score, 1.0)
            
            # If risk score is very high, mark as honeypot
            if risk_score >= 0.8:
                is_honeypot = True
            
            return SecurityResult(
                token_address=token_address,
                is_honeypot=is_honeypot,
                is_verified=is_verified,
                risk_score=risk_score,
                warnings=warnings,
                analysis_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error("Error combining analysis results", token_address=token_address, error=str(e))
            
            return SecurityResult(
                token_address=token_address,
                is_honeypot=True,
                is_verified=False,
                risk_score=1.0,
                warnings=[f"Analysis combination failed: {str(e)}"],
                analysis_timestamp=datetime.now()
            )
    
    def add_to_blacklist(self, token_address: str):
        """Add a token to the blacklist."""
        self.blacklisted_addresses.add(token_address.lower())
        logger.info("Token added to blacklist", token_address=token_address)
    
    def remove_from_blacklist(self, token_address: str):
        """Remove a token from the blacklist."""
        self.blacklisted_addresses.discard(token_address.lower())
        logger.info("Token removed from blacklist", token_address=token_address)
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self.analysis_cache.clear()
        logger.info("Analysis cache cleared")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        return {
            "cached_analyses": len(self.analysis_cache),
            "blacklisted_tokens": len(self.blacklisted_addresses),
            "cache_duration_hours": self.cache_duration.total_seconds() / 3600
        }