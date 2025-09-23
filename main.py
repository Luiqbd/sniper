#!/usr/bin/env python3
"""
Crypto Sniper Bot for Base Network
Advanced memecoin sniping and altcoin trading bot with Telegram integration.
"""

import asyncio
import signal
import sys
from typing import Optional

from src.core.config import load_config
from src.core.logger import setup_logging, logger
from src.core.web3_client import Web3Client
from src.core.dex_integration import DEXIntegration
from src.security.contract_analyzer import ContractAnalyzer
from src.strategies.memecoin_sniper import MemecoinSniper
from src.strategies.altcoin_trader import AltcoinTrader
from src.telegram.bot import TelegramBot

class CryptoSniperBot:
    """Main bot orchestrator."""
    
    def __init__(self):
        self.config = None
        self.web3_client = None
        self.dex_integration = None
        self.contract_analyzer = None
        self.memecoin_sniper = None
        self.altcoin_trader = None
        self.telegram_bot = None
        self.is_running = False
    
    async def initialize(self):
        """Initialize all bot components."""
        try:
            logger.info("Initializing Crypto Sniper Bot...")
            
            # Load configuration
            self.config = load_config()
            logger.info("Configuration loaded successfully")
            
            # Setup logging with configured level
            setup_logging(self.config.monitoring.log_level)
            
            # Initialize Web3 client
            self.web3_client = Web3Client(self.config)
            logger.info("Web3 client initialized")
            
            # Initialize DEX integration
            self.dex_integration = DEXIntegration(self.config, self.web3_client)
            logger.info("DEX integration initialized")
            
            # Initialize contract analyzer
            self.contract_analyzer = ContractAnalyzer(self.config, self.web3_client)
            logger.info("Contract analyzer initialized")
            
            # Initialize trading strategies
            self.memecoin_sniper = MemecoinSniper(
                self.config, 
                self.web3_client, 
                self.contract_analyzer
            )
            logger.info("Memecoin sniper initialized")
            
            self.altcoin_trader = AltcoinTrader(self.config, self.web3_client)
            logger.info("Altcoin trader initialized")
            
            # Initialize Telegram bot
            self.telegram_bot = TelegramBot(
                self.config,
                self.memecoin_sniper,
                self.altcoin_trader
            )
            logger.info("Telegram bot initialized")
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error("Error during initialization", error=str(e))
            raise
    
    async def start(self):
        """Start the bot."""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        try:
            self.is_running = True
            logger.info("Starting Crypto Sniper Bot...")
            
            # Start Telegram bot first
            await self.telegram_bot.start()
            
            # Send startup notification
            await self.telegram_bot.send_alert(
                "info",
                "🚀 Crypto Sniper Bot started successfully!\n\n"
                "All systems are online and ready for trading."
            )
            
            logger.info("Crypto Sniper Bot started successfully")
            
            # Keep the bot running
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error("Error starting bot", error=str(e))
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the bot gracefully."""
        if not self.is_running:
            return
        
        logger.info("Stopping Crypto Sniper Bot...")
        self.is_running = False
        
        try:
            # Stop all components
            if self.memecoin_sniper:
                await self.memecoin_sniper.stop()
            
            if self.altcoin_trader:
                await self.altcoin_trader.stop()
            
            if self.telegram_bot:
                await self.telegram_bot.stop()
            
            if self.web3_client:
                await self.web3_client.close()
            
            logger.info("Crypto Sniper Bot stopped successfully")
            
        except Exception as e:
            logger.error("Error stopping bot", error=str(e))
    
    async def health_check(self):
        """Perform health check and send alerts if needed."""
        try:
            # Check Web3 connection
            if not self.web3_client.w3.is_connected():
                await self.telegram_bot.send_alert(
                    "error",
                    "❌ Web3 connection lost! Attempting to reconnect..."
                )
                return False
            
            # Check wallet balance
            eth_balance = self.web3_client.get_eth_balance()
            if eth_balance < 0.001:  # Less than 0.001 ETH
                await self.telegram_bot.send_alert(
                    "warning",
                    f"⚠️ Low ETH balance: {eth_balance:.4f} ETH\n"
                    "Please add more ETH for gas fees."
                )
            
            # Check if strategies are responsive
            # This would include more detailed health checks
            
            return True
            
        except Exception as e:
            logger.error("Error during health check", error=str(e))
            await self.telegram_bot.send_alert(
                "error",
                f"❌ Health check failed: {str(e)}"
            )
            return False

async def main():
    """Main entry point."""
    bot = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        if bot:
            asyncio.create_task(bot.stop())
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and initialize bot
        bot = CryptoSniperBot()
        await bot.initialize()
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)
    finally:
        if bot:
            await bot.stop()

if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error in main", error=str(e))
        sys.exit(1)
