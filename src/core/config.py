import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class NetworkConfig:
    rpc_url: str
    websocket_url: str
    chain_id: int = 8453  # Base mainnet

@dataclass
class TradingConfig:
    max_memecoin_investment_usd: float
    memecoin_profit_target: float
    memecoin_stop_loss: float
    min_liquidity_eth: float
    min_holders: int
    altcoin_max_investment_usd: float
    altcoin_profit_target: float
    altcoin_stop_loss: float
    portfolio_rebalance_hours: int

@dataclass
class DEXConfig:
    uniswap_v3_router: str
    baseswap_router: str
    camelot_router: str

@dataclass
class GasConfig:
    max_gas_price_gwei: int
    gas_limit_swap: int
    slippage_tolerance: float

@dataclass
class SecurityConfig:
    basescan_api_key: str
    honeypot_check_enabled: bool
    contract_verification_enabled: bool

@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str

@dataclass
class MonitoringConfig:
    log_level: str
    health_check_interval_seconds: int
    alert_cooldown_minutes: int

@dataclass
class Config:
    network: NetworkConfig
    trading: TradingConfig
    dex: DEXConfig
    gas: GasConfig
    security: SecurityConfig
    telegram: TelegramConfig
    monitoring: MonitoringConfig
    private_key: str
    wallet_address: str
    testnet_mode: bool = False
    dry_run_mode: bool = False

def load_config() -> Config:
    """Load configuration from environment variables."""
    
    # Validate required environment variables
    required_vars = [
        'BASE_RPC_URL', 'BASE_WEBSOCKET_URL', 'PRIVATE_KEY', 'WALLET_ADDRESS',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'BASESCAN_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return Config(
        network=NetworkConfig(
            rpc_url=os.getenv('BASE_RPC_URL'),
            websocket_url=os.getenv('BASE_WEBSOCKET_URL'),
            chain_id=int(os.getenv('CHAIN_ID', '8453'))
        ),
        trading=TradingConfig(
            max_memecoin_investment_usd=float(os.getenv('MAX_MEMECOIN_INVESTMENT_USD', '8')),
            memecoin_profit_target=float(os.getenv('MEMECOIN_PROFIT_TARGET', '2.0')),
            memecoin_stop_loss=float(os.getenv('MEMECOIN_STOP_LOSS', '0.7')),
            min_liquidity_eth=float(os.getenv('MIN_LIQUIDITY_ETH', '0.01')),
            min_holders=int(os.getenv('MIN_HOLDERS', '50')),
            altcoin_max_investment_usd=float(os.getenv('ALTCOIN_MAX_INVESTMENT_USD', '100')),
            altcoin_profit_target=float(os.getenv('ALTCOIN_PROFIT_TARGET', '1.5')),
            altcoin_stop_loss=float(os.getenv('ALTCOIN_STOP_LOSS', '0.85')),
            portfolio_rebalance_hours=int(os.getenv('PORTFOLIO_REBALANCE_HOURS', '24'))
        ),
        dex=DEXConfig(
            uniswap_v3_router=os.getenv('UNISWAP_V3_ROUTER', '0x2626664c2603336E57B271c5C0b26F421741e481'),
            baseswap_router=os.getenv('BASESWAP_ROUTER', '0x327Df1E6de05895d2ab08513aaDD9313Fe505d86'),
            camelot_router=os.getenv('CAMELOT_ROUTER', '0xc873fEcbd354f5A56E00E710B90EF4201db2448d')
        ),
        gas=GasConfig(
            max_gas_price_gwei=int(os.getenv('MAX_GAS_PRICE_GWEI', '50')),
            gas_limit_swap=int(os.getenv('GAS_LIMIT_SWAP', '300000')),
            slippage_tolerance=float(os.getenv('SLIPPAGE_TOLERANCE', '0.05'))
        ),
        security=SecurityConfig(
            basescan_api_key=os.getenv('BASESCAN_API_KEY'),
            honeypot_check_enabled=os.getenv('HONEYPOT_CHECK_ENABLED', 'true').lower() == 'true',
            contract_verification_enabled=os.getenv('CONTRACT_VERIFICATION_ENABLED', 'true').lower() == 'true'
        ),
        telegram=TelegramConfig(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            chat_id=os.getenv('TELEGRAM_CHAT_ID')
        ),
        monitoring=MonitoringConfig(
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            health_check_interval_seconds=int(os.getenv('HEALTH_CHECK_INTERVAL_SECONDS', '60')),
            alert_cooldown_minutes=int(os.getenv('ALERT_COOLDOWN_MINUTES', '5'))
        ),
        private_key=os.getenv('PRIVATE_KEY'),
        wallet_address=os.getenv('WALLET_ADDRESS'),
        testnet_mode=os.getenv('TESTNET_MODE', 'false').lower() == 'true',
        dry_run_mode=os.getenv('DRY_RUN_MODE', 'false').lower() == 'true'
    )