import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from src.security.contract_analyzer import ContractAnalyzer, SecurityResult
from src.core.config import Config
from src.core.web3_client import Web3Client

class TestContractAnalyzer:
    """Test contract security analysis functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.security.basescan_api_key = "test_api_key"
        return config
    
    @pytest.fixture
    def web3_client(self):
        """Create mock Web3 client."""
        mock_client = Mock(spec=Web3Client)
        mock_client.w3 = Mock()
        mock_client.w3.eth = Mock()
        return mock_client
    
    @pytest.fixture
    def analyzer(self, config, web3_client):
        """Create contract analyzer instance."""
        return ContractAnalyzer(config, web3_client)
    
    @pytest.mark.asyncio
    async def test_analyze_contract_basic(self, analyzer):
        """Test basic contract analysis."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        with patch.object(analyzer, '_check_honeypot_api', return_value={}), \
             patch.object(analyzer, '_analyze_contract_code', return_value={}), \
             patch.object(analyzer, '_check_basescan_verification', return_value={'is_verified': True}), \
             patch.object(analyzer, '_analyze_transaction_patterns', return_value={}), \
             patch.object(analyzer, '_check_liquidity_locks', return_value={}):
            
            result = await analyzer.analyze_contract(token_address)
            
            assert isinstance(result, SecurityResult)
            assert result.token_address == token_address.lower()
            assert isinstance(result.is_honeypot, bool)
            assert isinstance(result.risk_score, float)
            assert 0.0 <= result.risk_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_honeypot_detection(self, analyzer):
        """Test honeypot detection logic."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        # Mock honeypot API response
        honeypot_response = {
            'honeypot_is': {
                'is_honeypot': True,
                'buy_tax': 5,
                'sell_tax': 99,  # Very high sell tax
                'max_tx_amount': 0,
                'max_tx_amount_percent': 0
            }
        }
        
        with patch.object(analyzer, '_check_honeypot_api', return_value=honeypot_response), \
             patch.object(analyzer, '_analyze_contract_code', return_value={}), \
             patch.object(analyzer, '_check_basescan_verification', return_value={'is_verified': False}), \
             patch.object(analyzer, '_analyze_transaction_patterns', return_value={}), \
             patch.object(analyzer, '_check_liquidity_locks', return_value={}):
            
            result = await analyzer.analyze_contract(token_address)
            
            assert result.is_honeypot is True
            assert result.risk_score >= 0.8  # High risk score for honeypot
            assert any("honeypot" in warning.lower() for warning in result.warnings)
    
    @pytest.mark.asyncio
    async def test_contract_verification_check(self, analyzer):
        """Test contract verification checking."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        with patch.object(analyzer, '_check_honeypot_api', return_value={}), \
             patch.object(analyzer, '_analyze_contract_code', return_value={}), \
             patch.object(analyzer, '_check_basescan_verification', return_value={'is_verified': False}), \
             patch.object(analyzer, '_analyze_transaction_patterns', return_value={}), \
             patch.object(analyzer, '_check_liquidity_locks', return_value={}):
            
            result = await analyzer.analyze_contract(token_address)
            
            assert result.is_verified is False
            assert any("not verified" in warning.lower() for warning in result.warnings)
    
    @pytest.mark.asyncio
    async def test_suspicious_contract_patterns(self, analyzer):
        """Test detection of suspicious contract patterns."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        # Mock contract code analysis with suspicious patterns
        code_analysis = {
            'risk_factors': ['transfer_restriction', 'blacklist_functions', 'pause_functions'],
            'warnings': ['Contract has transfer restrictions']
        }
        
        with patch.object(analyzer, '_check_honeypot_api', return_value={}), \
             patch.object(analyzer, '_analyze_contract_code', return_value=code_analysis), \
             patch.object(analyzer, '_check_basescan_verification', return_value={'is_verified': True}), \
             patch.object(analyzer, '_analyze_transaction_patterns', return_value={}), \
             patch.object(analyzer, '_check_liquidity_locks', return_value={}):
            
            result = await analyzer.analyze_contract(token_address)
            
            assert result.risk_score > 0.5  # Should have elevated risk score
            assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_transaction_pattern_analysis(self, analyzer):
        """Test transaction pattern analysis."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        # Mock suspicious transaction patterns
        tx_analysis = {
            'total_transactions': 100,
            'failed_transactions': 40,  # High failure rate
            'failure_rate': 0.4,
            'unique_addresses': 10,  # Low unique addresses
            'bot_activity_score': 0.9,  # High bot activity
            'warnings': ['High transaction failure rate: 40.0%', 'Possible bot activity detected']
        }
        
        with patch.object(analyzer, '_check_honeypot_api', return_value={}), \
             patch.object(analyzer, '_analyze_contract_code', return_value={}), \
             patch.object(analyzer, '_check_basescan_verification', return_value={'is_verified': True}), \
             patch.object(analyzer, '_analyze_transaction_patterns', return_value=tx_analysis), \
             patch.object(analyzer, '_check_liquidity_locks', return_value={}):
            
            result = await analyzer.analyze_contract(token_address)
            
            assert result.risk_score > 0.3  # Should have elevated risk score
            assert any("failure rate" in warning.lower() for warning in result.warnings)
    
    def test_blacklist_functionality(self, analyzer):
        """Test blacklist functionality."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        # Add to blacklist
        analyzer.add_to_blacklist(token_address)
        assert token_address.lower() in analyzer.blacklisted_addresses
        
        # Remove from blacklist
        analyzer.remove_from_blacklist(token_address)
        assert token_address.lower() not in analyzer.blacklisted_addresses
    
    @pytest.mark.asyncio
    async def test_blacklisted_token_analysis(self, analyzer):
        """Test analysis of blacklisted token."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        # Add to blacklist
        analyzer.add_to_blacklist(token_address)
        
        result = await analyzer.analyze_contract(token_address)
        
        assert result.is_honeypot is True
        assert result.risk_score == 1.0
        assert any("blacklisted" in warning.lower() for warning in result.warnings)
    
    def test_cache_functionality(self, analyzer):
        """Test analysis result caching."""
        token_address = "0x1234567890123456789012345678901234567890"
        
        # Create a test result
        test_result = SecurityResult(
            token_address=token_address,
            is_honeypot=False,
            is_verified=True,
            risk_score=0.1,
            warnings=[],
            analysis_timestamp=datetime.now()
        )
        
        # Add to cache
        analyzer.analysis_cache[token_address] = test_result
        
        # Check cache stats
        stats = analyzer.get_cache_stats()
        assert stats['cached_analyses'] == 1
        
        # Clear cache
        analyzer.clear_cache()
        stats = analyzer.get_cache_stats()
        assert stats['cached_analyses'] == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, analyzer):
        """Test error handling in analysis."""
        token_address = "invalid_address"
        
        # Should handle errors gracefully and return high-risk result
        result = await analyzer.analyze_contract(token_address)
        
        assert result.is_honeypot is True
        assert result.risk_score == 1.0
        assert len(result.warnings) > 0