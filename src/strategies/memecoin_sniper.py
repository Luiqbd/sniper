import asyncio
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import aiohttp
from ..core.config import Config
from ..core.web3_client import Web3Client, Transaction, TokenInfo
from ..core.logger import logger
from ..security.contract_analyzer import ContractAnalyzer
from ..utils.price_calculator import PriceCalculator

@dataclass
class MemecoinPosition:
    token_address: str
    symbol: str
    entry_price: float
    amount: float
    entry_time: datetime
    target_price: float
    stop_loss_price: float
    investment_usd: float
    status: str = "active"  # active, sold_profit, sold_loss

@dataclass
class MemecoinOpportunity:
    token_address: str
    token_info: TokenInfo
    liquidity_eth: float
    holders_count: int
    social_score: float
    risk_score: float
    detected_at: datetime

class MemecoinSniper:
    """Advanced memecoin sniping strategy with social sentiment analysis."""
    
    def __init__(self, config: Config, web3_client: Web3Client, contract_analyzer: 'ContractAnalyzer'):
        self.config = config
        self.web3_client = web3_client
        self.contract_analyzer = contract_analyzer
        self.price_calculator = PriceCalculator(web3_client)
        
        # Active positions and tracking
        self.positions: Dict[str, MemecoinPosition] = {}
        self.monitored_tokens: Set[str] = set()
        self.blacklisted_tokens: Set[str] = set()
        self.opportunities: List[MemecoinOpportunity] = []
        
        # Performance tracking
        self.total_invested = 0.0
        self.total_profit = 0.0
        self.successful_trades = 0
        self.failed_trades = 0
        
        # Rate limiting and cooldowns
        self.last_purchase_time = {}
        self.purchase_cooldown = 30  # seconds between purchases of same token
        
        self.is_running = False
        logger.info("MemecoinSniper initialized")
    
    async def start(self):
        """Start the memecoin sniping strategy."""
        if self.is_running:
            logger.warning("MemecoinSniper already running")
            return
        
        self.is_running = True
        logger.info("Starting MemecoinSniper")
        
        # Start concurrent tasks
        tasks = [
            asyncio.create_task(self._monitor_mempool()),
            asyncio.create_task(self._monitor_positions()),
            asyncio.create_task(self._social_sentiment_monitor()),
            asyncio.create_task(self._cleanup_old_opportunities())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error("Error in MemecoinSniper", error=str(e))
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the memecoin sniping strategy."""
        self.is_running = False
        logger.info("MemecoinSniper stopped")
    
    async def _monitor_mempool(self):
        """Monitor mempool for new token launches and liquidity additions."""
        logger.info("Starting mempool monitoring for memecoins")
        
        async def process_transaction(tx: Transaction):
            if not self.is_running:
                return
            
            try:
                # Check if transaction is related to token creation or liquidity addition
                if await self._is_token_launch_tx(tx):
                    await self._analyze_new_token(tx)
                elif await self._is_liquidity_addition_tx(tx):
                    await self._analyze_liquidity_addition(tx)
                    
            except Exception as e:
                logger.debug("Error processing mempool transaction", 
                           tx_hash=tx.hash, error=str(e))
        
        await self.web3_client.monitor_mempool(process_transaction)
    
    async def _is_token_launch_tx(self, tx: Transaction) -> bool:
        """Check if transaction is a token launch."""
        # Check for common token factory patterns
        token_factory_signatures = [
            '0x60806040',  # Contract creation bytecode
            '0x608060405',  # Alternative contract creation
        ]
        
        return (
            tx.to_address == '' and  # Contract creation
            any(tx.input_data.startswith(sig) for sig in token_factory_signatures) and
            len(tx.input_data) > 1000  # Substantial contract code
        )
    
    async def _is_liquidity_addition_tx(self, tx: Transaction) -> bool:
        """Check if transaction is adding liquidity to a DEX."""
        # Common DEX router addresses and function signatures
        dex_routers = [
            self.config.dex.uniswap_v3_router.lower(),
            self.config.dex.baseswap_router.lower(),
            self.config.dex.camelot_router.lower()
        ]
        
        liquidity_signatures = [
            '0xe8e33700',  # addLiquidity
            '0xf305d719',  # addLiquidityETH
            '0x4515cef3',  # addLiquidityETHSupportingFeeOnTransferTokens
        ]
        
        return (
            tx.to_address.lower() in dex_routers and
            any(tx.input_data.startswith(sig) for sig in liquidity_signatures) and
            tx.value > self.web3_client.w3.to_wei(self.config.trading.min_liquidity_eth, 'ether')
        )
    
    async def _analyze_new_token(self, tx: Transaction):
        """Analyze a newly launched token for sniping opportunity."""
        try:
            # Wait for transaction to be mined
            receipt = self.web3_client.wait_for_transaction_receipt(tx.hash, timeout=30)
            
            if receipt['status'] != 1:
                return
            
            # Extract token address from contract creation
            token_address = receipt['contractAddress']
            
            if not token_address or token_address in self.blacklisted_tokens:
                return
            
            # Get token information
            token_info = await self.web3_client.get_token_info(token_address)
            if not token_info:
                return
            
            # Perform security analysis
            security_result = await self.contract_analyzer.analyze_contract(token_address)
            if security_result.is_honeypot or security_result.risk_score > 0.7:
                self.blacklisted_tokens.add(token_address)
                logger.warning("Token blacklisted due to security concerns", 
                             token_address=token_address,
                             risk_score=security_result.risk_score)
                return
            
            # Check basic criteria
            if (token_info.holders_count >= self.config.trading.min_holders and
                token_info.liquidity_eth >= self.config.trading.min_liquidity_eth):
                
                # Calculate social sentiment score
                social_score = await self._calculate_social_score(token_info)
                
                opportunity = MemecoinOpportunity(
                    token_address=token_address,
                    token_info=token_info,
                    liquidity_eth=token_info.liquidity_eth,
                    holders_count=token_info.holders_count,
                    social_score=social_score,
                    risk_score=security_result.risk_score,
                    detected_at=datetime.now()
                )
                
                self.opportunities.append(opportunity)
                
                # If opportunity meets criteria, execute snipe
                if await self._should_snipe_token(opportunity):
                    await self._execute_snipe(opportunity)
                    
        except Exception as e:
            logger.error("Error analyzing new token", tx_hash=tx.hash, error=str(e))
    
    async def _analyze_liquidity_addition(self, tx: Transaction):
        """Analyze liquidity addition for existing tokens."""
        try:
            # Decode transaction to extract token address
            # This would require ABI decoding - simplified for now
            # In practice, you'd decode the addLiquidity call parameters
            
            # For now, we'll skip this and focus on new token launches
            pass
            
        except Exception as e:
            logger.debug("Error analyzing liquidity addition", tx_hash=tx.hash, error=str(e))
    
    async def _calculate_social_score(self, token_info: TokenInfo) -> float:
        """Calculate social sentiment score for a token."""
        try:
            # This would integrate with Twitter API, Telegram channels, etc.
            # For now, return a placeholder score based on token characteristics
            
            score = 0.0
            
            # Name/symbol heuristics for memecoins
            memecoin_keywords = ['doge', 'shib', 'pepe', 'wojak', 'chad', 'moon', 'rocket', 'inu']
            name_lower = token_info.name.lower()
            symbol_lower = token_info.symbol.lower()
            
            if any(keyword in name_lower or keyword in symbol_lower for keyword in memecoin_keywords):
                score += 0.3
            
            # Holder count factor
            if token_info.holders_count > 100:
                score += 0.2
            if token_info.holders_count > 500:
                score += 0.2
            
            # Liquidity factor
            if token_info.liquidity_eth > 0.1:
                score += 0.2
            if token_info.liquidity_eth > 1.0:
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error("Error calculating social score", error=str(e))
            return 0.0
    
    async def _should_snipe_token(self, opportunity: MemecoinOpportunity) -> bool:
        """Determine if we should snipe this token."""
        # Check cooldown
        if opportunity.token_address in self.last_purchase_time:
            time_since_last = time.time() - self.last_purchase_time[opportunity.token_address]
            if time_since_last < self.purchase_cooldown:
                return False
        
        # Check if already holding this token
        if opportunity.token_address in self.positions:
            return False
        
        # Check investment limits
        if self.total_invested >= self.config.trading.max_memecoin_investment_usd * 10:  # Max 10 positions
            return False
        
        # Scoring criteria
        min_score = 0.6
        combined_score = (
            opportunity.social_score * 0.4 +
            (1 - opportunity.risk_score) * 0.3 +
            min(opportunity.liquidity_eth / 1.0, 1.0) * 0.2 +
            min(opportunity.holders_count / 200, 1.0) * 0.1
        )
        
        logger.info("Token scoring", 
                   token_address=opportunity.token_address,
                   symbol=opportunity.token_info.symbol,
                   combined_score=combined_score,
                   social_score=opportunity.social_score,
                   risk_score=opportunity.risk_score)
        
        return combined_score >= min_score
    
    async def _execute_snipe(self, opportunity: MemecoinOpportunity):
        """Execute a memecoin snipe."""
        try:
            token_address = opportunity.token_address
            investment_usd = self.config.trading.max_memecoin_investment_usd
            
            logger.info("Executing memecoin snipe", 
                       token_address=token_address,
                       symbol=opportunity.token_info.symbol,
                       investment_usd=investment_usd)
            
            if self.config.dry_run_mode:
                logger.info("DRY RUN: Would execute snipe", 
                           token_address=token_address,
                           investment_usd=investment_usd)
                return
            
            # Calculate ETH amount to spend
            eth_price_usd = await self.price_calculator.get_eth_price_usd()
            eth_amount = investment_usd / eth_price_usd
            
            # Get current token price
            token_price = await self.price_calculator.get_token_price_eth(token_address)
            if not token_price:
                logger.error("Could not get token price", token_address=token_address)
                return
            
            # Calculate token amount to buy
            token_amount = eth_amount / token_price
            
            # Execute buy transaction
            tx_hash = await self._buy_token(token_address, eth_amount, token_amount)
            
            if tx_hash:
                # Create position
                position = MemecoinPosition(
                    token_address=token_address,
                    symbol=opportunity.token_info.symbol,
                    entry_price=token_price,
                    amount=token_amount,
                    entry_time=datetime.now(),
                    target_price=token_price * self.config.trading.memecoin_profit_target,
                    stop_loss_price=token_price * self.config.trading.memecoin_stop_loss,
                    investment_usd=investment_usd
                )
                
                self.positions[token_address] = position
                self.total_invested += investment_usd
                self.last_purchase_time[token_address] = time.time()
                
                logger.info("Memecoin snipe executed successfully", 
                           token_address=token_address,
                           symbol=opportunity.token_info.symbol,
                           tx_hash=tx_hash,
                           amount=token_amount,
                           entry_price=token_price)
            
        except Exception as e:
            logger.error("Error executing snipe", 
                        token_address=opportunity.token_address, error=str(e))
    
    async def _buy_token(self, token_address: str, eth_amount: float, min_tokens: float) -> Optional[str]:
        """Execute token purchase via DEX."""
        try:
            # This would integrate with DEX routers
            # For now, return a placeholder
            logger.info("Buying token", 
                       token_address=token_address,
                       eth_amount=eth_amount,
                       min_tokens=min_tokens)
            
            # In real implementation, this would:
            # 1. Build swap transaction
            # 2. Sign and send transaction
            # 3. Return transaction hash
            
            return "0x" + "0" * 64  # Placeholder transaction hash
            
        except Exception as e:
            logger.error("Error buying token", token_address=token_address, error=str(e))
            return None
    
    async def _monitor_positions(self):
        """Monitor active positions for profit/loss targets."""
        while self.is_running:
            try:
                for token_address, position in list(self.positions.items()):
                    if position.status != "active":
                        continue
                    
                    # Get current price
                    current_price = await self.price_calculator.get_token_price_eth(token_address)
                    if not current_price:
                        continue
                    
                    # Check profit target
                    if current_price >= position.target_price:
                        await self._sell_position(position, "profit", current_price)
                    
                    # Check stop loss
                    elif current_price <= position.stop_loss_price:
                        await self._sell_position(position, "loss", current_price)
                    
                    # Check time-based exit (24 hours max hold)
                    elif datetime.now() - position.entry_time > timedelta(hours=24):
                        await self._sell_position(position, "timeout", current_price)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error("Error monitoring positions", error=str(e))
                await asyncio.sleep(30)
    
    async def _sell_position(self, position: MemecoinPosition, reason: str, current_price: float):
        """Sell a position."""
        try:
            logger.info("Selling position", 
                       token_address=position.token_address,
                       symbol=position.symbol,
                       reason=reason,
                       entry_price=position.entry_price,
                       current_price=current_price)
            
            if self.config.dry_run_mode:
                logger.info("DRY RUN: Would sell position", 
                           token_address=position.token_address,
                           reason=reason)
                return
            
            # Execute sell transaction
            tx_hash = await self._sell_token(position.token_address, position.amount)
            
            if tx_hash:
                # Calculate profit/loss
                price_change = (current_price - position.entry_price) / position.entry_price
                profit_usd = position.investment_usd * price_change
                
                # Update position
                position.status = f"sold_{reason}"
                self.total_profit += profit_usd
                
                if profit_usd > 0:
                    self.successful_trades += 1
                else:
                    self.failed_trades += 1
                
                logger.info("Position sold successfully", 
                           token_address=position.token_address,
                           symbol=position.symbol,
                           profit_usd=profit_usd,
                           price_change_percent=price_change * 100,
                           tx_hash=tx_hash)
            
        except Exception as e:
            logger.error("Error selling position", 
                        token_address=position.token_address, error=str(e))
    
    async def _sell_token(self, token_address: str, amount: float) -> Optional[str]:
        """Execute token sale via DEX."""
        try:
            # This would integrate with DEX routers
            logger.info("Selling token", token_address=token_address, amount=amount)
            
            # In real implementation, this would:
            # 1. Build swap transaction
            # 2. Sign and send transaction
            # 3. Return transaction hash
            
            return "0x" + "1" * 64  # Placeholder transaction hash
            
        except Exception as e:
            logger.error("Error selling token", token_address=token_address, error=str(e))
            return None
    
    async def _social_sentiment_monitor(self):
        """Monitor social media for memecoin sentiment."""
        while self.is_running:
            try:
                # This would integrate with Twitter API, Telegram channels, etc.
                # For now, just sleep
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error("Error in social sentiment monitoring", error=str(e))
                await asyncio.sleep(300)
    
    async def _cleanup_old_opportunities(self):
        """Clean up old opportunities to prevent memory leaks."""
        while self.is_running:
            try:
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.opportunities = [
                    opp for opp in self.opportunities 
                    if opp.detected_at > cutoff_time
                ]
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logger.error("Error cleaning up opportunities", error=str(e))
                await asyncio.sleep(3600)
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get performance statistics."""
        total_trades = self.successful_trades + self.failed_trades
        win_rate = (self.successful_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_invested": self.total_invested,
            "total_profit": self.total_profit,
            "roi_percent": (self.total_profit / self.total_invested * 100) if self.total_invested > 0 else 0,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "win_rate_percent": win_rate,
            "active_positions": len([p for p in self.positions.values() if p.status == "active"]),
            "opportunities_detected": len(self.opportunities)
        }