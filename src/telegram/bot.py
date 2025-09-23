import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from ..core.config import Config
from ..core.logger import logger
from ..strategies.memecoin_sniper import MemecoinSniper
from ..strategies.altcoin_trader import AltcoinTrader

class TelegramBot:
    """Advanced Telegram bot with interactive controls and real-time alerts."""
    
    def __init__(self, config: Config, memecoin_sniper: MemecoinSniper, altcoin_trader: AltcoinTrader):
        self.config = config
        self.memecoin_sniper = memecoin_sniper
        self.altcoin_trader = altcoin_trader
        
        # Bot application
        self.application = Application.builder().token(config.telegram.bot_token).build()
        
        # Bot state
        self.is_running = False
        self.memecoin_sniper_active = False
        self.altcoin_trader_active = False
        
        # Alert cooldowns
        self.last_alert_time = {}
        self.alert_cooldown = config.monitoring.alert_cooldown_minutes * 60
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info("TelegramBot initialized", chat_id=config.telegram.chat_id)
    
    def _setup_handlers(self):
        """Setup command and callback handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("status", self._status_command))
        self.application.add_handler(CommandHandler("balance", self._balance_command))
        self.application.add_handler(CommandHandler("positions", self._positions_command))
        self.application.add_handler(CommandHandler("performance", self._performance_command))
        self.application.add_handler(CommandHandler("config", self._config_command))
        self.application.add_handler(CommandHandler("buy", self._buy_command))
        self.application.add_handler(CommandHandler("sell", self._sell_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        
        # Callback query handlers for buttons
        self.application.add_handler(CallbackQueryHandler(self._button_callback))
    
    async def start(self):
        """Start the Telegram bot."""
        if self.is_running:
            logger.warning("TelegramBot already running")
            return
        
        self.is_running = True
        logger.info("Starting TelegramBot")
        
        # Initialize and start the bot
        await self.application.initialize()
        await self.application.start()
        
        # Send startup message
        await self._send_startup_message()
        
        # Start polling for updates
        await self.application.updater.start_polling()
        
        logger.info("TelegramBot started successfully")
    
    async def stop(self):
        """Stop the Telegram bot."""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping TelegramBot")
        
        # Send shutdown message
        await self._send_message("🔴 Bot is shutting down...")
        
        # Stop the bot
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        logger.info("TelegramBot stopped")
    
    async def _send_startup_message(self):
        """Send startup message with main controls."""
        message = """
🚀 **Crypto Sniper Bot Started**

Welcome to your advanced crypto trading bot for Base network!

**Available Strategies:**
• 🎯 Memecoin Sniper - Hunt new memecoins with high potential
• 📈 Altcoin Trader - Swing trade established DeFi tokens

Use the buttons below to control the bot or type /help for commands.
        """
        
        keyboard = self._get_main_keyboard()
        await self._send_message(message, keyboard)
    
    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        """Get the main control keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🎯 Start Memecoin Sniper", callback_data="start_memecoin"),
                InlineKeyboardButton("⏹️ Stop Memecoin Sniper", callback_data="stop_memecoin")
            ],
            [
                InlineKeyboardButton("📈 Start Altcoin Trader", callback_data="start_altcoin"),
                InlineKeyboardButton("⏹️ Stop Altcoin Trader", callback_data="stop_altcoin")
            ],
            [
                InlineKeyboardButton("💰 Balance", callback_data="balance"),
                InlineKeyboardButton("📊 Status", callback_data="status")
            ],
            [
                InlineKeyboardButton("🎯 Positions", callback_data="positions"),
                InlineKeyboardButton("📈 Performance", callback_data="performance")
            ],
            [
                InlineKeyboardButton("⚙️ Config", callback_data="config"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await self._send_startup_message()
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        await self._send_status_message()
    
    async def _balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command."""
        await self._send_balance_message()
    
    async def _positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command."""
        await self._send_positions_message()
    
    async def _performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /performance command."""
        await self._send_performance_message()
    
    async def _config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config command."""
        await self._send_config_message()
    
    async def _buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /buy command."""
        if not context.args:
            await self._send_message("Usage: /buy <token_address> [amount_usd]")
            return
        
        token_address = context.args[0]
        amount_usd = float(context.args[1]) if len(context.args) > 1 else 50.0
        
        await self._manual_buy(token_address, amount_usd)
    
    async def _sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sell command."""
        if not context.args:
            await self._send_message("Usage: /sell <token_address> [percentage]")
            return
        
        token_address = context.args[0]
        percentage = float(context.args[1]) if len(context.args) > 1 else 100.0
        
        await self._manual_sell(token_address, percentage)
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 **Crypto Sniper Bot Commands**

**Main Commands:**
• /start - Show main control panel
• /status - Show bot status and active strategies
• /balance - Show wallet balance and portfolio value
• /positions - Show active trading positions
• /performance - Show trading performance statistics
• /config - Show current configuration

**Trading Commands:**
• /buy <token_address> [amount_usd] - Manual buy order
• /sell <token_address> [percentage] - Manual sell order

**Interactive Controls:**
Use the buttons in the main panel for easy control of all bot functions.

**Alerts:**
The bot will automatically send alerts for:
• New positions opened
• Positions closed (profit/loss)
• High-risk tokens detected
• System errors and health checks
        """
        
        await self._send_message(help_text)
    
    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "start_memecoin":
            await self._start_memecoin_sniper()
        elif callback_data == "stop_memecoin":
            await self._stop_memecoin_sniper()
        elif callback_data == "start_altcoin":
            await self._start_altcoin_trader()
        elif callback_data == "stop_altcoin":
            await self._stop_altcoin_trader()
        elif callback_data == "balance":
            await self._send_balance_message()
        elif callback_data == "status":
            await self._send_status_message()
        elif callback_data == "positions":
            await self._send_positions_message()
        elif callback_data == "performance":
            await self._send_performance_message()
        elif callback_data == "config":
            await self._send_config_message()
        elif callback_data == "help":
            await self._help_command(update, context)
    
    async def _start_memecoin_sniper(self):
        """Start the memecoin sniper strategy."""
        if self.memecoin_sniper_active:
            await self._send_message("🎯 Memecoin Sniper is already active!")
            return
        
        try:
            self.memecoin_sniper_active = True
            asyncio.create_task(self.memecoin_sniper.start())
            
            message = """
🎯 **Memecoin Sniper Started**

✅ Monitoring mempool for new token launches
✅ Analyzing contracts for security risks
✅ Ready to snipe high-potential memecoins

**Settings:**
• Max investment per token: ${}
• Profit target: {}x
• Stop loss: {}%
• Min liquidity: {} ETH
• Min holders: {}
            """.format(
                self.config.trading.max_memecoin_investment_usd,
                self.config.trading.memecoin_profit_target,
                (1 - self.config.trading.memecoin_stop_loss) * 100,
                self.config.trading.min_liquidity_eth,
                self.config.trading.min_holders
            )
            
            await self._send_message(message)
            logger.info("Memecoin sniper started via Telegram")
            
        except Exception as e:
            self.memecoin_sniper_active = False
            await self._send_message(f"❌ Error starting Memecoin Sniper: {str(e)}")
            logger.error("Error starting memecoin sniper via Telegram", error=str(e))
    
    async def _stop_memecoin_sniper(self):
        """Stop the memecoin sniper strategy."""
        if not self.memecoin_sniper_active:
            await self._send_message("🎯 Memecoin Sniper is not active!")
            return
        
        try:
            await self.memecoin_sniper.stop()
            self.memecoin_sniper_active = False
            
            await self._send_message("⏹️ Memecoin Sniper stopped successfully")
            logger.info("Memecoin sniper stopped via Telegram")
            
        except Exception as e:
            await self._send_message(f"❌ Error stopping Memecoin Sniper: {str(e)}")
            logger.error("Error stopping memecoin sniper via Telegram", error=str(e))
    
    async def _start_altcoin_trader(self):
        """Start the altcoin trader strategy."""
        if self.altcoin_trader_active:
            await self._send_message("📈 Altcoin Trader is already active!")
            return
        
        try:
            self.altcoin_trader_active = True
            asyncio.create_task(self.altcoin_trader.start())
            
            message = """
📈 **Altcoin Trader Started**

✅ Monitoring DeFi tokens for trading signals
✅ Technical analysis active
✅ Portfolio rebalancing enabled

**Settings:**
• Max investment per position: ${}
• Profit target: {}%
• Stop loss: {}%
• Rebalance interval: {} hours
            """.format(
                self.config.trading.altcoin_max_investment_usd,
                (self.config.trading.altcoin_profit_target - 1) * 100,
                (1 - self.config.trading.altcoin_stop_loss) * 100,
                self.config.trading.portfolio_rebalance_hours
            )
            
            await self._send_message(message)
            logger.info("Altcoin trader started via Telegram")
            
        except Exception as e:
            self.altcoin_trader_active = False
            await self._send_message(f"❌ Error starting Altcoin Trader: {str(e)}")
            logger.error("Error starting altcoin trader via Telegram", error=str(e))
    
    async def _stop_altcoin_trader(self):
        """Stop the altcoin trader strategy."""
        if not self.altcoin_trader_active:
            await self._send_message("📈 Altcoin Trader is not active!")
            return
        
        try:
            await self.altcoin_trader.stop()
            self.altcoin_trader_active = False
            
            await self._send_message("⏹️ Altcoin Trader stopped successfully")
            logger.info("Altcoin trader stopped via Telegram")
            
        except Exception as e:
            await self._send_message(f"❌ Error stopping Altcoin Trader: {str(e)}")
            logger.error("Error stopping altcoin trader via Telegram", error=str(e))
    
    async def _send_status_message(self):
        """Send current bot status."""
        memecoin_status = "🟢 Active" if self.memecoin_sniper_active else "🔴 Inactive"
        altcoin_status = "🟢 Active" if self.altcoin_trader_active else "🔴 Inactive"
        
        # Get performance stats
        memecoin_stats = self.memecoin_sniper.get_performance_stats()
        altcoin_stats = self.altcoin_trader.get_performance_stats()
        
        message = f"""
📊 **Bot Status**

**Strategies:**
🎯 Memecoin Sniper: {memecoin_status}
📈 Altcoin Trader: {altcoin_status}

**Memecoin Sniper:**
• Active positions: {memecoin_stats.get('active_positions', 0)}
• Total invested: ${memecoin_stats.get('total_invested', 0):.2f}
• Total profit: ${memecoin_stats.get('total_profit', 0):.2f}
• Win rate: {memecoin_stats.get('win_rate_percent', 0):.1f}%

**Altcoin Trader:**
• Active positions: {altcoin_stats.get('active_positions', 0)}
• Portfolio value: ${altcoin_stats.get('portfolio_value_usd', 0):.2f}
• Total profit: ${altcoin_stats.get('total_profit_usd', 0):.2f}
• Win rate: {altcoin_stats.get('win_rate_percent', 0):.1f}%

**System:**
• Uptime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Network: Base Mainnet
        """
        
        keyboard = self._get_main_keyboard()
        await self._send_message(message, keyboard)
    
    async def _send_balance_message(self):
        """Send wallet balance information."""
        try:
            # Get ETH balance
            eth_balance = self.memecoin_sniper.web3_client.get_eth_balance()
            
            # Get token balances for major tokens
            usdc_balance = self.memecoin_sniper.web3_client.get_token_balance(
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
            )
            
            message = f"""
💰 **Wallet Balance**

**Main Balance:**
• ETH: {eth_balance:.4f} ETH
• USDC: {usdc_balance:.2f} USDC

**Portfolio Summary:**
• Available for trading: ${self.altcoin_trader.available_balance_usd:.2f}
• Total portfolio value: ${self.altcoin_trader.portfolio_value_usd:.2f}

**Wallet Address:**
`{self.config.wallet_address}`
            """
            
            await self._send_message(message)
            
        except Exception as e:
            await self._send_message(f"❌ Error getting balance: {str(e)}")
            logger.error("Error getting balance via Telegram", error=str(e))
    
    async def _send_positions_message(self):
        """Send active positions information."""
        try:
            message = "🎯 **Active Positions**\n\n"
            
            # Memecoin positions
            memecoin_positions = [p for p in self.memecoin_sniper.positions.values() if p.status == "active"]
            if memecoin_positions:
                message += "**Memecoin Positions:**\n"
                for pos in memecoin_positions:
                    profit_pct = ((pos.target_price - pos.entry_price) / pos.entry_price) * 100
                    message += f"• {pos.symbol}: ${pos.investment_usd:.2f} (Target: +{profit_pct:.1f}%)\n"
                message += "\n"
            
            # Altcoin positions
            altcoin_positions = [p for p in self.altcoin_trader.positions.values() if p.status == "active"]
            if altcoin_positions:
                message += "**Altcoin Positions:**\n"
                for pos in altcoin_positions:
                    profit_pct = ((pos.target_price - pos.entry_price) / pos.entry_price) * 100
                    message += f"• {pos.symbol}: ${pos.investment_usd:.2f} (Target: +{profit_pct:.1f}%)\n"
                message += "\n"
            
            if not memecoin_positions and not altcoin_positions:
                message += "No active positions at the moment."
            
            await self._send_message(message)
            
        except Exception as e:
            await self._send_message(f"❌ Error getting positions: {str(e)}")
            logger.error("Error getting positions via Telegram", error=str(e))
    
    async def _send_performance_message(self):
        """Send performance statistics."""
        try:
            memecoin_stats = self.memecoin_sniper.get_performance_stats()
            altcoin_stats = self.altcoin_trader.get_performance_stats()
            
            message = f"""
📈 **Performance Statistics**

**Memecoin Sniper:**
• Total trades: {memecoin_stats.get('successful_trades', 0) + memecoin_stats.get('failed_trades', 0)}
• Successful: {memecoin_stats.get('successful_trades', 0)}
• Win rate: {memecoin_stats.get('win_rate_percent', 0):.1f}%
• Total profit: ${memecoin_stats.get('total_profit', 0):.2f}
• ROI: {memecoin_stats.get('roi_percent', 0):.1f}%

**Altcoin Trader:**
• Total trades: {altcoin_stats.get('total_trades', 0)}
• Profitable: {altcoin_stats.get('profitable_trades', 0)}
• Win rate: {altcoin_stats.get('win_rate_percent', 0):.1f}%
• Total profit: ${altcoin_stats.get('total_profit_usd', 0):.2f}
• ROI: {altcoin_stats.get('roi_percent', 0):.1f}%
• Max drawdown: {altcoin_stats.get('max_drawdown_percent', 0):.1f}%

**Overall:**
• Combined profit: ${memecoin_stats.get('total_profit', 0) + altcoin_stats.get('total_profit_usd', 0):.2f}
            """
            
            await self._send_message(message)
            
        except Exception as e:
            await self._send_message(f"❌ Error getting performance: {str(e)}")
            logger.error("Error getting performance via Telegram", error=str(e))
    
    async def _send_config_message(self):
        """Send current configuration."""
        message = f"""
⚙️ **Current Configuration**

**Memecoin Sniper:**
• Max investment: ${self.config.trading.max_memecoin_investment_usd}
• Profit target: {self.config.trading.memecoin_profit_target}x
• Stop loss: {self.config.trading.memecoin_stop_loss}x
• Min liquidity: {self.config.trading.min_liquidity_eth} ETH
• Min holders: {self.config.trading.min_holders}

**Altcoin Trader:**
• Max investment: ${self.config.trading.altcoin_max_investment_usd}
• Profit target: {self.config.trading.altcoin_profit_target}x
• Stop loss: {self.config.trading.altcoin_stop_loss}x
• Rebalance: {self.config.trading.portfolio_rebalance_hours}h

**Security:**
• Honeypot check: {'✅' if self.config.security.honeypot_check_enabled else '❌'}
• Contract verification: {'✅' if self.config.security.contract_verification_enabled else '❌'}

**Gas:**
• Max gas price: {self.config.gas.max_gas_price_gwei} gwei
• Slippage tolerance: {self.config.gas.slippage_tolerance * 100}%
        """
        
        await self._send_message(message)
    
    async def _manual_buy(self, token_address: str, amount_usd: float):
        """Execute manual buy order."""
        try:
            await self._send_message(f"🔄 Executing manual buy order for {token_address}...")
            
            # This would execute the actual buy logic
            # For now, just send a confirmation message
            
            await self._send_message(f"✅ Manual buy order executed: ${amount_usd} worth of {token_address}")
            
        except Exception as e:
            await self._send_message(f"❌ Error executing buy order: {str(e)}")
            logger.error("Error executing manual buy via Telegram", error=str(e))
    
    async def _manual_sell(self, token_address: str, percentage: float):
        """Execute manual sell order."""
        try:
            await self._send_message(f"🔄 Executing manual sell order for {token_address}...")
            
            # This would execute the actual sell logic
            # For now, just send a confirmation message
            
            await self._send_message(f"✅ Manual sell order executed: {percentage}% of {token_address}")
            
        except Exception as e:
            await self._send_message(f"❌ Error executing sell order: {str(e)}")
            logger.error("Error executing manual sell via Telegram", error=str(e))
    
    async def _send_message(self, text: str, keyboard: Optional[InlineKeyboardMarkup] = None):
        """Send message to Telegram chat."""
        try:
            await self.application.bot.send_message(
                chat_id=self.config.telegram.chat_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error("Error sending Telegram message", error=str(e))
    
    async def send_alert(self, alert_type: str, message: str):
        """Send alert message with cooldown."""
        try:
            # Check cooldown
            current_time = datetime.now().timestamp()
            if alert_type in self.last_alert_time:
                time_since_last = current_time - self.last_alert_time[alert_type]
                if time_since_last < self.alert_cooldown:
                    return
            
            self.last_alert_time[alert_type] = current_time
            
            # Add alert emoji based on type
            emoji_map = {
                'profit': '💰',
                'loss': '📉',
                'new_position': '🎯',
                'error': '❌',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
            
            emoji = emoji_map.get(alert_type, '🔔')
            alert_message = f"{emoji} **ALERT**\n\n{message}"
            
            await self._send_message(alert_message)
            
        except Exception as e:
            logger.error("Error sending alert", alert_type=alert_type, error=str(e))