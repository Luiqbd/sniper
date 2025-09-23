import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from src.strategies.memecoin_sniper import MemecoinSniper, MemecoinPosition
from src.security.contract_analyzer import SecurityResult
from src.core.config import Config
from src.core.web3_client import Web3Client, TokenInfo

class TestMemecoinSniper:
    """Test memecoin sniping strategy."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.dry_run_mode = True  # Enable dry run for testing
        return config
    
    @pytest.fixture
    def web3_client(self):
        """Create mock Web3 client."""
        mock_client = Mock(spec=Web3Client)
        mock_client.get_eth_balance.return_value = 1.0
        return mock_client
    
    @pytest.fixture
    def contract_analyzer(self):
        """Create mock contract analyzer."""
        mock_analyzer = Mock()
        return mock_analyzer
    
    @pytest.fixture
    def sniper(self, config, web3_client, contract_analyzer):
        """Create memecoin sniper instance."""
        return MemecoinSniper(config, web3_client, contract_analyzer)
    
    def test_sniper_initialization(self, sniper):
        """Test sniper initialization."""
        assert sniper is not None
        assert sniper.positions == {}
        assert sniper.total_invested == 0.0
        assert sniper.successful_trades == 0
        assert sniper.failed_trades == 0
        assert not sniper.is_running
    
    @pytest.mark.asyncio
    async def test_evaluate_memecoin_opportunity_good_token(self, sniper):
        """Test evaluation of a good memecoin opportunity."""
        token_info = TokenInfo(
            address="0x1234567890123456789012345678901234567890",
            symbol="TESTCOIN",
            name="Test Coin",
            decimals=18,
            total_supply=1000000,
            liquidity_eth=1.0,  # Good liquidity
            holder_count=100,   # Good holder count
            creation_time=datetime.now()
        )
        
        security_result = SecurityResult(
            token_address=token_info.address,
            is_honeypot=False,
            is_verified=True,
            risk_score=0.1,  # Low risk
            warnings=[],
            analysis_timestamp=datetime.now()
        )
        
        with patch.object(sniper.contract_analyzer, 'analyze_contract', return_value=security_result):
            opportunity = await sniper._evaluate_memecoin_opportunity(token_info)
            
            assert opportunity is not None
            assert opportunity.token_info == token_info
            assert opportunity.security_result == security_result
            assert opportunity.score > 0.5  # Should have good score
    
    @pytest.mark.asyncio
    async def test_evaluate_memecoin_opportunity_bad_token(self, sniper):
        """Test evaluation of a bad memecoin opportunity."""
        token_info = TokenInfo(
            address="0x1234567890123456789012345678901234567890",
            symbol="SCAMCOIN",
            name="Scam Coin",
            decimals=18,
            total_supply=1000000,
            liquidity_eth=0.005,  # Low liquidity
            holder_count=10,      # Low holder count
            creation_time=datetime.now()
        )
        
        security_result = SecurityResult(
            token_address=token_info.address,
            is_honeypot=True,     # Honeypot detected
            is_verified=False,
            risk_score=0.9,       # High risk
            warnings=["Detected as honeypot"],
            analysis_timestamp=datetime.now()
        )
        
        with patch.object(sniper.contract_analyzer, 'analyze_contract', return_value=security_result):
            opportunity = await sniper._evaluate_memecoin_opportunity(token_info)
            
            assert opportunity is None  # Should reject bad token
    
    @pytest.mark.asyncio
    async def test_execute_snipe_dry_run(self, sniper):
        """Test snipe execution in dry run mode."""
        token_info = TokenInfo(
            address="0x1234567890123456789012345678901234567890",
            symbol="TESTCOIN",
            name="Test Coin",
            decimals=18,
            total_supply=1000000,
            liquidity_eth=1.0,
            holder_count=100,
            creation_time=datetime.now()
        )
        
        investment_eth = 0.01
        
        # Should succeed in dry run mode
        success = await sniper._execute_snipe(token_info, investment_eth)
        assert success is True
        
        # Check that position was created
        assert token_info.address in sniper.positions
        position = sniper.positions[token_info.address]
        assert position.token_address == token_info.address
        assert position.investment_eth == investment_eth
        assert position.status == "active"
    
    def test_calculate_position_size(self, sniper):
        """Test position size calculation."""
        # Test with good opportunity
        size = sniper._calculate_position_size(score=0.8, liquidity_eth=1.0)
        assert size > 0
        assert size <= sniper.config.trading.max_memecoin_investment_usd / 2000  # Assuming ETH price
        
        # Test with poor opportunity
        size = sniper._calculate_position_size(score=0.3, liquidity_eth=0.1)
        assert size == 0  # Should not invest in poor opportunity
    
    @pytest.mark.asyncio
    async def test_position_management(self, sniper):
        """Test position management logic."""
        # Create a test position
        position = MemecoinPosition(
            token_address="0x1234567890123456789012345678901234567890",
            symbol="TESTCOIN",
            entry_price=0.001,
            amount=1000,
            entry_time=datetime.now(),
            target_price=0.002,  # 2x target
            stop_loss_price=0.0007,  # 30% stop loss
            investment_eth=0.01
        )
        
        sniper.positions[position.token_address] = position
        
        # Test profit target hit
        with patch.object(sniper, '_get_current_token_price', return_value=0.002):
            await sniper._check_position_exit(position)
            # Position should be marked for exit (in real implementation)
        
        # Test stop loss hit
        position.status = "active"  # Reset status
        with patch.object(sniper, '_get_current_token_price', return_value=0.0006):
            await sniper._check_position_exit(position)
            # Position should be marked for exit (in real implementation)
    
    def test_performance_stats(self, sniper):
        """Test performance statistics calculation."""
        # Add some test data
        sniper.successful_trades = 5
        sniper.failed_trades = 2
        sniper.total_profit = 0.05
        sniper.total_invested = 0.1
        
        stats = sniper.get_performance_stats()
        
        assert stats['successful_trades'] == 5
        assert stats['failed_trades'] == 2
        assert stats['total_trades'] == 7
        assert stats['win_rate_percent'] == (5/7) * 100
        assert stats['total_profit'] == 0.05
        assert stats['roi_percent'] == (0.05/0.1) * 100
    
    @pytest.mark.asyncio
    async def test_social_sentiment_analysis(self, sniper):
        """Test social sentiment analysis."""
        token_info = TokenInfo(
            address="0x1234567890123456789012345678901234567890",
            symbol="TESTCOIN",
            name="Test Coin",
            decimals=18,
            total_supply=1000000,
            liquidity_eth=1.0,
            holder_count=100,
            creation_time=datetime.now()
        )
        
        # Mock social sentiment data
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'sentiment_score': 0.8,
                'mention_count': 50,
                'trending': True
            })
            mock_get.return_value.__aenter__.return_value = mock_response
            
            sentiment = await sniper._analyze_social_sentiment(token_info)
            
            assert sentiment is not None
            assert sentiment.get('sentiment_score', 0) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sniper):
        """Test error handling in various scenarios."""
        # Test with invalid token info
        invalid_token = TokenInfo(
            address="invalid_address",
            symbol="INVALID",
            name="Invalid Token",
            decimals=18,
            total_supply=0,
            liquidity_eth=0,
            holder_count=0,
            creation_time=datetime.now()
        )
        
        # Should handle gracefully
        opportunity = await sniper._evaluate_memecoin_opportunity(invalid_token)
        assert opportunity is None
    
    def test_risk_management(self, sniper):
        """Test risk management features."""
        # Test maximum investment limit
        large_score = 1.0
        large_liquidity = 100.0
        
        position_size = sniper._calculate_position_size(large_score, large_liquidity)
        max_investment_eth = sniper.config.trading.max_memecoin_investment_usd / 2000  # Assuming ETH price
        
        assert position_size <= max_investment_eth
        
        # Test total exposure limit
        sniper.total_invested = 0.5  # Already invested 0.5 ETH
        
        # Should reduce position size or reject if too much exposure
        position_size = sniper._calculate_position_size(large_score, large_liquidity)
        assert position_size <= max_investment_eth