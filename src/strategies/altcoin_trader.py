import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ..core.config import Config
from ..core.web3_client import Web3Client, TokenInfo
from ..core.logger import logger
from ..utils.price_calculator import PriceCalculator
from ..utils.technical_analysis import TechnicalAnalyzer

@dataclass
class AltcoinPosition:
    token_address: str
    symbol: str
    entry_price: float
    amount: float
    entry_time: datetime
    target_price: float
    stop_loss_price: float
    investment_usd: float
    position_type: str = "long"  # long, short
    status: str = "active"  # active, sold_profit, sold_loss

@dataclass
class AltcoinSignal:
    token_address: str
    symbol: str
    signal_type: str  # buy, sell, hold
    strength: float  # 0.0 to 1.0
    price: float
    timestamp: datetime
    indicators: Dict[str, float] = field(default_factory=dict)

class AltcoinTrader:
    """Advanced altcoin trading strategy with technical analysis and portfolio management."""
    
    def __init__(self, config: Config, web3_client: Web3Client):
        self.config = config
        self.web3_client = web3_client
        self.price_calculator = PriceCalculator(web3_client)
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Portfolio management
        self.positions: Dict[str, AltcoinPosition] = {}
        self.portfolio_value_usd = 0.0
        self.available_balance_usd = 1000.0  # Starting balance
        self.max_position_size_percent = 0.2  # Max 20% per position
        
        # Supported altcoins (DeFi tokens with good liquidity)
        self.supported_tokens = {
            "0x4200000000000000000000000000000000000006": "WETH",  # Wrapped ETH on Base
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "USDC",  # USD Coin
            "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb": "DAI",   # Dai Stablecoin
            # Add more Base network DeFi tokens here
        }
        
        # Price history for technical analysis
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.signals_history: Dict[str, List[AltcoinSignal]] = {}
        
        # Performance tracking
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit_usd = 0.0
        self.max_drawdown = 0.0
        self.peak_portfolio_value = 0.0
        
        # Rebalancing
        self.last_rebalance_time = datetime.now()
        self.rebalance_interval = timedelta(hours=config.trading.portfolio_rebalance_hours)
        
        self.is_running = False
        logger.info("AltcoinTrader initialized", supported_tokens=len(self.supported_tokens))
    
    async def start(self):
        """Start the altcoin trading strategy."""
        if self.is_running:
            logger.warning("AltcoinTrader already running")
            return
        
        self.is_running = True
        logger.info("Starting AltcoinTrader")
        
        # Initialize price history
        await self._initialize_price_history()
        
        # Start concurrent tasks
        tasks = [
            asyncio.create_task(self._price_monitoring_loop()),
            asyncio.create_task(self._signal_generation_loop()),
            asyncio.create_task(self._position_management_loop()),
            asyncio.create_task(self._portfolio_rebalancing_loop()),
            asyncio.create_task(self._performance_tracking_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error("Error in AltcoinTrader", error=str(e))
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the altcoin trading strategy."""
        self.is_running = False
        logger.info("AltcoinTrader stopped")
    
    async def _initialize_price_history(self):
        """Initialize price history for all supported tokens."""
        logger.info("Initializing price history for supported tokens")
        
        for token_address, symbol in self.supported_tokens.items():
            try:
                # Get recent price data (last 24 hours)
                prices = await self._get_historical_prices(token_address, hours=24)
                self.price_history[token_address] = prices
                self.signals_history[token_address] = []
                
                logger.debug("Initialized price history", 
                           symbol=symbol, data_points=len(prices))
                
            except Exception as e:
                logger.error("Error initializing price history", 
                           symbol=symbol, error=str(e))
    
    async def _get_historical_prices(self, token_address: str, hours: int = 24) -> List[Tuple[datetime, float]]:
        """Get historical price data for a token."""
        try:
            # In a real implementation, this would fetch from a price API
            # For now, generate some sample data
            prices = []
            current_time = datetime.now()
            base_price = 100.0  # Starting price
            
            for i in range(hours * 4):  # 15-minute intervals
                timestamp = current_time - timedelta(minutes=15 * i)
                # Add some random price movement
                price_change = np.random.normal(0, 0.02)  # 2% volatility
                price = base_price * (1 + price_change)
                prices.append((timestamp, price))
                base_price = price
            
            return list(reversed(prices))  # Chronological order
            
        except Exception as e:
            logger.error("Error getting historical prices", 
                        token_address=token_address, error=str(e))
            return []
    
    async def _price_monitoring_loop(self):
        """Monitor prices and update price history."""
        while self.is_running:
            try:
                for token_address, symbol in self.supported_tokens.items():
                    # Get current price
                    current_price = await self.price_calculator.get_token_price_usd(token_address)
                    
                    if current_price:
                        # Update price history
                        current_time = datetime.now()
                        self.price_history[token_address].append((current_time, current_price))
                        
                        # Keep only last 48 hours of data
                        cutoff_time = current_time - timedelta(hours=48)
                        self.price_history[token_address] = [
                            (ts, price) for ts, price in self.price_history[token_address]
                            if ts > cutoff_time
                        ]
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error("Error in price monitoring loop", error=str(e))
                await asyncio.sleep(60)
    
    async def _signal_generation_loop(self):
        """Generate trading signals based on technical analysis."""
        while self.is_running:
            try:
                for token_address, symbol in self.supported_tokens.items():
                    if len(self.price_history[token_address]) < 50:  # Need enough data
                        continue
                    
                    # Generate trading signal
                    signal = await self._generate_trading_signal(token_address, symbol)
                    
                    if signal:
                        self.signals_history[token_address].append(signal)
                        
                        # Keep only recent signals
                        cutoff_time = datetime.now() - timedelta(hours=24)
                        self.signals_history[token_address] = [
                            s for s in self.signals_history[token_address]
                            if s.timestamp > cutoff_time
                        ]
                        
                        # Execute signal if strong enough
                        if signal.strength >= 0.7:
                            await self._execute_signal(signal)
                
                await asyncio.sleep(300)  # Generate signals every 5 minutes
                
            except Exception as e:
                logger.error("Error in signal generation loop", error=str(e))
                await asyncio.sleep(300)
    
    async def _generate_trading_signal(self, token_address: str, symbol: str) -> Optional[AltcoinSignal]:
        """Generate a trading signal for a token using technical analysis."""
        try:
            prices = self.price_history[token_address]
            if len(prices) < 50:
                return None
            
            # Convert to pandas DataFrame for analysis
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df.set_index('timestamp', inplace=True)
            
            # Calculate technical indicators
            indicators = self.technical_analyzer.calculate_indicators(df['price'])
            
            # Generate signal based on multiple indicators
            signal_strength = 0.0
            signal_type = "hold"
            
            # RSI signal
            rsi = indicators.get('rsi', 50)
            if rsi < 30:  # Oversold
                signal_strength += 0.3
                signal_type = "buy"
            elif rsi > 70:  # Overbought
                signal_strength += 0.3
                signal_type = "sell"
            
            # MACD signal
            macd_signal = indicators.get('macd_signal', 0)
            if macd_signal > 0:  # Bullish crossover
                signal_strength += 0.2
                if signal_type != "sell":
                    signal_type = "buy"
            elif macd_signal < 0:  # Bearish crossover
                signal_strength += 0.2
                if signal_type != "buy":
                    signal_type = "sell"
            
            # Moving average signal
            ma_signal = indicators.get('ma_signal', 0)
            if ma_signal > 0:  # Price above MA
                signal_strength += 0.2
                if signal_type != "sell":
                    signal_type = "buy"
            elif ma_signal < 0:  # Price below MA
                signal_strength += 0.2
                if signal_type != "buy":
                    signal_type = "sell"
            
            # Bollinger Bands signal
            bb_signal = indicators.get('bb_signal', 0)
            if bb_signal > 0:  # Price near lower band
                signal_strength += 0.2
                if signal_type != "sell":
                    signal_type = "buy"
            elif bb_signal < 0:  # Price near upper band
                signal_strength += 0.2
                if signal_type != "buy":
                    signal_type = "sell"
            
            # Volume confirmation
            volume_signal = indicators.get('volume_signal', 0)
            if volume_signal > 0:
                signal_strength += 0.1
            
            current_price = prices[-1][1]
            
            return AltcoinSignal(
                token_address=token_address,
                symbol=symbol,
                signal_type=signal_type,
                strength=min(signal_strength, 1.0),
                price=current_price,
                timestamp=datetime.now(),
                indicators=indicators
            )
            
        except Exception as e:
            logger.error("Error generating trading signal", 
                        symbol=symbol, error=str(e))
            return None
    
    async def _execute_signal(self, signal: AltcoinSignal):
        """Execute a trading signal."""
        try:
            logger.info("Executing trading signal", 
                       symbol=signal.symbol,
                       signal_type=signal.signal_type,
                       strength=signal.strength,
                       price=signal.price)
            
            if signal.signal_type == "buy":
                await self._execute_buy_signal(signal)
            elif signal.signal_type == "sell":
                await self._execute_sell_signal(signal)
            
        except Exception as e:
            logger.error("Error executing signal", 
                        symbol=signal.symbol, error=str(e))
    
    async def _execute_buy_signal(self, signal: AltcoinSignal):
        """Execute a buy signal."""
        try:
            # Check if we already have a position
            if signal.token_address in self.positions:
                existing_position = self.positions[signal.token_address]
                if existing_position.status == "active":
                    logger.debug("Already have active position", symbol=signal.symbol)
                    return
            
            # Calculate position size
            max_investment = self.available_balance_usd * self.max_position_size_percent
            investment_amount = min(
                max_investment,
                self.config.trading.altcoin_max_investment_usd
            )
            
            if investment_amount < 10:  # Minimum investment
                logger.debug("Insufficient balance for position", 
                           symbol=signal.symbol, available=self.available_balance_usd)
                return
            
            if self.config.dry_run_mode:
                logger.info("DRY RUN: Would buy altcoin", 
                           symbol=signal.symbol,
                           investment_amount=investment_amount,
                           price=signal.price)
                return
            
            # Calculate token amount
            token_amount = investment_amount / signal.price
            
            # Execute buy order
            tx_hash = await self._buy_altcoin(signal.token_address, investment_amount, token_amount)
            
            if tx_hash:
                # Create position
                position = AltcoinPosition(
                    token_address=signal.token_address,
                    symbol=signal.symbol,
                    entry_price=signal.price,
                    amount=token_amount,
                    entry_time=datetime.now(),
                    target_price=signal.price * self.config.trading.altcoin_profit_target,
                    stop_loss_price=signal.price * self.config.trading.altcoin_stop_loss,
                    investment_usd=investment_amount
                )
                
                self.positions[signal.token_address] = position
                self.available_balance_usd -= investment_amount
                self.total_trades += 1
                
                logger.info("Altcoin buy executed", 
                           symbol=signal.symbol,
                           amount=token_amount,
                           price=signal.price,
                           investment=investment_amount,
                           tx_hash=tx_hash)
            
        except Exception as e:
            logger.error("Error executing buy signal", 
                        symbol=signal.symbol, error=str(e))
    
    async def _execute_sell_signal(self, signal: AltcoinSignal):
        """Execute a sell signal."""
        try:
            if signal.token_address not in self.positions:
                logger.debug("No position to sell", symbol=signal.symbol)
                return
            
            position = self.positions[signal.token_address]
            if position.status != "active":
                return
            
            await self._sell_position(position, "signal", signal.price)
            
        except Exception as e:
            logger.error("Error executing sell signal", 
                        symbol=signal.symbol, error=str(e))
    
    async def _buy_altcoin(self, token_address: str, investment_usd: float, token_amount: float) -> Optional[str]:
        """Execute altcoin purchase."""
        try:
            # This would integrate with DEX routers
            logger.info("Buying altcoin", 
                       token_address=token_address,
                       investment_usd=investment_usd,
                       token_amount=token_amount)
            
            # In real implementation, this would:
            # 1. Build swap transaction
            # 2. Sign and send transaction
            # 3. Return transaction hash
            
            return "0x" + "2" * 64  # Placeholder transaction hash
            
        except Exception as e:
            logger.error("Error buying altcoin", token_address=token_address, error=str(e))
            return None
    
    async def _sell_altcoin(self, token_address: str, token_amount: float) -> Optional[str]:
        """Execute altcoin sale."""
        try:
            # This would integrate with DEX routers
            logger.info("Selling altcoin", 
                       token_address=token_address,
                       token_amount=token_amount)
            
            # In real implementation, this would:
            # 1. Build swap transaction
            # 2. Sign and send transaction
            # 3. Return transaction hash
            
            return "0x" + "3" * 64  # Placeholder transaction hash
            
        except Exception as e:
            logger.error("Error selling altcoin", token_address=token_address, error=str(e))
            return None
    
    async def _position_management_loop(self):
        """Monitor and manage active positions."""
        while self.is_running:
            try:
                for token_address, position in list(self.positions.items()):
                    if position.status != "active":
                        continue
                    
                    # Get current price
                    current_price = await self.price_calculator.get_token_price_usd(token_address)
                    if not current_price:
                        continue
                    
                    # Check profit target
                    if current_price >= position.target_price:
                        await self._sell_position(position, "profit", current_price)
                    
                    # Check stop loss
                    elif current_price <= position.stop_loss_price:
                        await self._sell_position(position, "loss", current_price)
                    
                    # Check time-based exit (7 days max hold for swing trading)
                    elif datetime.now() - position.entry_time > timedelta(days=7):
                        await self._sell_position(position, "timeout", current_price)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error("Error in position management loop", error=str(e))
                await asyncio.sleep(30)
    
    async def _sell_position(self, position: AltcoinPosition, reason: str, current_price: float):
        """Sell a position."""
        try:
            logger.info("Selling altcoin position", 
                       symbol=position.symbol,
                       reason=reason,
                       entry_price=position.entry_price,
                       current_price=current_price)
            
            if self.config.dry_run_mode:
                logger.info("DRY RUN: Would sell altcoin position", 
                           symbol=position.symbol,
                           reason=reason)
                return
            
            # Execute sell transaction
            tx_hash = await self._sell_altcoin(position.token_address, position.amount)
            
            if tx_hash:
                # Calculate profit/loss
                price_change = (current_price - position.entry_price) / position.entry_price
                profit_usd = position.investment_usd * price_change
                final_value = position.investment_usd + profit_usd
                
                # Update position and portfolio
                position.status = f"sold_{reason}"
                self.available_balance_usd += final_value
                self.total_profit_usd += profit_usd
                
                if profit_usd > 0:
                    self.profitable_trades += 1
                
                logger.info("Altcoin position sold", 
                           symbol=position.symbol,
                           profit_usd=profit_usd,
                           price_change_percent=price_change * 100,
                           final_value=final_value,
                           tx_hash=tx_hash)
            
        except Exception as e:
            logger.error("Error selling position", 
                        symbol=position.symbol, error=str(e))
    
    async def _portfolio_rebalancing_loop(self):
        """Rebalance portfolio periodically."""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                if current_time - self.last_rebalance_time >= self.rebalance_interval:
                    await self._rebalance_portfolio()
                    self.last_rebalance_time = current_time
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error("Error in portfolio rebalancing loop", error=str(e))
                await asyncio.sleep(3600)
    
    async def _rebalance_portfolio(self):
        """Rebalance the portfolio by adjusting position sizes."""
        try:
            logger.info("Starting portfolio rebalancing")
            
            # Calculate current portfolio value
            total_value = self.available_balance_usd
            
            for position in self.positions.values():
                if position.status == "active":
                    current_price = await self.price_calculator.get_token_price_usd(position.token_address)
                    if current_price:
                        position_value = position.amount * current_price
                        total_value += position_value
            
            self.portfolio_value_usd = total_value
            
            # Update peak value and calculate drawdown
            if total_value > self.peak_portfolio_value:
                self.peak_portfolio_value = total_value
            
            current_drawdown = (self.peak_portfolio_value - total_value) / self.peak_portfolio_value
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
            
            # Reinvest profits if available
            if self.total_profit_usd > 100:  # Reinvest if profit > $100
                reinvestment_amount = self.total_profit_usd * 0.5  # Reinvest 50% of profits
                self.available_balance_usd += reinvestment_amount
                self.total_profit_usd -= reinvestment_amount
                
                logger.info("Reinvesting profits", 
                           reinvestment_amount=reinvestment_amount,
                           remaining_profit=self.total_profit_usd)
            
            logger.info("Portfolio rebalancing completed", 
                       total_value=total_value,
                       available_balance=self.available_balance_usd,
                       active_positions=len([p for p in self.positions.values() if p.status == "active"]))
            
        except Exception as e:
            logger.error("Error rebalancing portfolio", error=str(e))
    
    async def _performance_tracking_loop(self):
        """Track and log performance metrics."""
        while self.is_running:
            try:
                stats = self.get_performance_stats()
                
                logger.info("Performance update", 
                           portfolio_value=stats["portfolio_value_usd"],
                           total_profit=stats["total_profit_usd"],
                           roi_percent=stats["roi_percent"],
                           win_rate=stats["win_rate_percent"])
                
                await asyncio.sleep(1800)  # Update every 30 minutes
                
            except Exception as e:
                logger.error("Error in performance tracking loop", error=str(e))
                await asyncio.sleep(1800)
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get comprehensive performance statistics."""
        win_rate = (self.profitable_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        roi = (self.total_profit_usd / 1000 * 100) if self.total_profit_usd != 0 else 0  # Assuming $1000 starting capital
        
        active_positions = [p for p in self.positions.values() if p.status == "active"]
        
        return {
            "portfolio_value_usd": self.portfolio_value_usd,
            "available_balance_usd": self.available_balance_usd,
            "total_profit_usd": self.total_profit_usd,
            "roi_percent": roi,
            "total_trades": self.total_trades,
            "profitable_trades": self.profitable_trades,
            "win_rate_percent": win_rate,
            "max_drawdown_percent": self.max_drawdown * 100,
            "active_positions": len(active_positions),
            "active_positions_value": sum([
                p.amount * self.price_calculator.get_token_price_usd(p.token_address) or 0
                for p in active_positions
            ])
        }