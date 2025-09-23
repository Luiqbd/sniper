import pytest
import os
from unittest.mock import patch
from src.core.config import Config, load_config

class TestConfig:
    """Test configuration loading and validation."""
    
    def test_config_creation(self):
        """Test basic config creation."""
        config = Config()
        assert config is not None
        assert hasattr(config, 'web3')
        assert hasattr(config, 'telegram')
        assert hasattr(config, 'trading')
    
    @patch.dict(os.environ, {
        'BASE_RPC_URL': 'https://test-rpc.base.org',
        'PRIVATE_KEY': '0x' + '1' * 64,
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': '123456789'
    })
    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        config = load_config()
        
        assert config.web3.base_rpc_url == 'https://test-rpc.base.org'
        assert config.web3.private_key == '0x' + '1' * 64
        assert config.telegram.bot_token == 'test_token'
        assert config.telegram.chat_id == '123456789'
    
    def test_config_validation(self):
        """Test config validation."""
        config = Config()
        
        # Test required fields
        assert config.web3.base_rpc_url is not None
        assert config.trading.max_memecoin_investment_usd > 0
        assert config.trading.memecoin_profit_target > 1.0
        assert config.trading.memecoin_stop_loss < 1.0
    
    def test_trading_config_defaults(self):
        """Test trading configuration defaults."""
        config = Config()
        
        assert config.trading.max_memecoin_investment_usd == 8.0
        assert config.trading.memecoin_profit_target == 2.0
        assert config.trading.memecoin_stop_loss == 0.7
        assert config.trading.min_liquidity_eth == 0.01
        assert config.trading.min_holders == 50
    
    def test_gas_config_defaults(self):
        """Test gas configuration defaults."""
        config = Config()
        
        assert config.gas.max_gas_price_gwei == 50
        assert config.gas.gas_limit_swap == 300000
        assert config.gas.slippage_tolerance == 0.05
    
    def test_security_config_defaults(self):
        """Test security configuration defaults."""
        config = Config()
        
        assert config.security.honeypot_check_enabled is True
        assert config.security.contract_verification_enabled is True
        assert config.security.max_risk_score == 0.3