# 🎯 Crypto Sniper Bot

Advanced memecoin sniping and altcoin trading bot for Base network with comprehensive security features and Telegram integration.

[![CI/CD Pipeline](https://github.com/Luiqbd/sniper/actions/workflows/ci.yml/badge.svg)](https://github.com/Luiqbd/sniper/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Luiqbd/sniper/branch/main/graph/badge.svg)](https://codecov.io/gh/Luiqbd/sniper)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Features

### 🎯 Memecoin Sniper Strategy
- **Real-time Mempool Monitoring**: WebSocket-based monitoring of pending transactions
- **Smart Contract Analysis**: Automated honeypot detection and security verification
- **Social Sentiment Analysis**: Integration with social media APIs for hype detection
- **Risk Management**: Configurable investment limits and stop-loss mechanisms
- **Multi-DEX Support**: Automatic routing across BaseSwap, Uniswap v3, and Camelot

### 📈 Altcoin Trading Strategy
- **Technical Analysis**: RSI, MACD, Bollinger Bands, and moving averages
- **Portfolio Management**: Automated rebalancing and profit reinvestment
- **Swing Trading**: Position management with configurable profit targets
- **DeFi Token Focus**: Specialized in established DeFi tokens with stable liquidity

### 🔒 Security & Protection
- **Honeypot Detection**: Multi-API verification against known scams
- **Contract Verification**: BaseScan integration for source code verification
- **Transaction Analysis**: Pattern recognition for suspicious activity
- **Blacklist Management**: Automatic and manual token blacklisting
- **Risk Scoring**: Comprehensive risk assessment (0.0-1.0 scale)

### 🤖 Telegram Integration
- **Interactive Controls**: Start/stop strategies with inline buttons
- **Real-time Alerts**: Profit/loss notifications and system health checks
- **Portfolio Monitoring**: Live balance and position tracking
- **Manual Trading**: Execute buy/sell orders via commands
- **Performance Analytics**: Detailed trading statistics and ROI tracking

### 🔄 DEX Integration
- **Multi-DEX Routing**: Automatic best price discovery
- **Slippage Protection**: Dynamic slippage calculation and protection
- **Gas Optimization**: Intelligent gas price management
- **Fallback Mechanisms**: Automatic DEX switching on failures

## 📋 Requirements

- Python 3.11+
- Base network RPC access (Alchemy, Infura, or self-hosted)
- Telegram Bot Token
- BaseScan API Key (optional but recommended)
- Minimum 0.1 ETH for gas fees and initial trades

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Luiqbd/sniper.git
   cd sniper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run tests**
   ```bash
   pytest tests/
   ```

5. **Start the bot**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t crypto-sniper-bot .
   ```

2. **Run with environment file**
   ```bash
   docker run --env-file .env crypto-sniper-bot
   ```

### Render Deployment

1. **Fork this repository**

2. **Connect to Render**
   - Create new Web Service on Render
   - Connect your GitHub repository
   - Use `render.yaml` configuration

3. **Set environment variables**
   - Configure all required environment variables in Render dashboard
   - Ensure sensitive keys are properly secured

## ⚙️ Configuration

### Environment Variables

#### Required Configuration
```bash
# Web3 Configuration
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
BASE_WSS_URL=wss://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
WALLET_ADDRESS=0xYOUR_WALLET_ADDRESS

# Telegram Configuration
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID

# API Keys
BASESCAN_API_KEY=YOUR_BASESCAN_API_KEY
```

#### Trading Configuration
```bash
# Memecoin Sniper
MAX_MEMECOIN_INVESTMENT_USD=8
MEMECOIN_PROFIT_TARGET=2.0
MEMECOIN_STOP_LOSS=0.7
MIN_LIQUIDITY_ETH=0.01
MIN_HOLDERS=50

# Altcoin Trader
ALTCOIN_MAX_INVESTMENT_USD=100
ALTCOIN_PROFIT_TARGET=1.2
ALTCOIN_STOP_LOSS=0.9
PORTFOLIO_REBALANCE_HOURS=24

# Gas & Slippage
MAX_GAS_PRICE_GWEI=50
SLIPPAGE_TOLERANCE=0.05
```

#### Security Configuration
```bash
HONEYPOT_CHECK_ENABLED=true
CONTRACT_VERIFICATION_ENABLED=true
MAX_RISK_SCORE=0.3
DRY_RUN_MODE=false
```

### Telegram Bot Setup

1. **Create a Telegram Bot**
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Save the bot token

2. **Get Chat ID**
   - Start a conversation with your bot
   - Send a message
   - Visit `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
   - Find your chat ID in the response

3. **Configure Bot Commands**
   ```
   start - Show main control panel
   status - Show bot status and strategies
   balance - Show wallet balance
   positions - Show active positions
   performance - Show trading statistics
   config - Show current configuration
   buy - Manual buy order
   sell - Manual sell order
   help - Show help information
   ```

## 🎮 Usage

### Starting the Bot

1. **Initialize and start**
   ```bash
   python main.py
   ```

2. **Telegram Controls**
   - Send `/start` to your bot
   - Use interactive buttons to control strategies
   - Monitor alerts and notifications

### Trading Strategies

#### Memecoin Sniper
- Automatically monitors new token launches
- Analyzes security and fundamentals
- Executes trades based on opportunity score
- Manages positions with profit targets and stop losses

#### Altcoin Trader
- Monitors established DeFi tokens
- Uses technical analysis for entry/exit signals
- Rebalances portfolio periodically
- Reinvests profits automatically

### Manual Trading

```bash
# Buy token manually
/buy 0xTOKEN_ADDRESS 50

# Sell position
/sell 0xTOKEN_ADDRESS 100

# Check status
/status

# View performance
/performance
```

## 📊 Monitoring & Analytics

### Performance Metrics
- **ROI**: Return on investment percentage
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Maximum portfolio decline
- **Total Trades**: Number of executed trades

### Health Monitoring
- **Connection Status**: Web3 and API connectivity
- **Balance Alerts**: Low ETH balance warnings
- **Error Tracking**: Automatic error reporting
- **Uptime Monitoring**: System availability tracking

## 🧪 Testing

### Run Test Suite
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test category
pytest tests/test_memecoin_sniper.py -v

# Run integration tests (requires testnet setup)
pytest tests/integration/ -v
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Security Tests**: Contract analysis and risk assessment
- **Performance Tests**: Load and stress testing

## 🔧 Development

### Project Structure
```
sniper/
├── src/
│   ├── core/           # Core infrastructure
│   ├── strategies/     # Trading strategies
│   ├── security/       # Security analysis
│   ├── telegram/       # Telegram integration
│   └── utils/          # Utility functions
├── tests/              # Test suite
├── config/             # Configuration files
├── .github/            # CI/CD workflows
├── Dockerfile          # Container configuration
├── render.yaml         # Render deployment config
└── requirements.txt    # Python dependencies
```

### Contributing

1. **Fork the repository**
2. **Create feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make changes and test**
   ```bash
   pytest tests/
   ```
4. **Commit changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
5. **Push to branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open Pull Request**

### Code Quality

- **Linting**: flake8, black, isort
- **Type Checking**: mypy
- **Security**: bandit, safety
- **Testing**: pytest with coverage
- **Documentation**: Comprehensive docstrings

## 🚨 Risk Disclaimer

**IMPORTANT**: This bot involves automated cryptocurrency trading which carries significant financial risk.

### Risks Include:
- **Market Risk**: Cryptocurrency prices are highly volatile
- **Smart Contract Risk**: DeFi protocols may have bugs or vulnerabilities
- **Impermanent Loss**: DEX trading can result in unfavorable price movements
- **Gas Fees**: High network congestion can lead to expensive transactions
- **Regulatory Risk**: Cryptocurrency regulations may change

### Recommendations:
- **Start Small**: Begin with minimal investment amounts
- **Use Testnet**: Test thoroughly on Base testnet before mainnet
- **Monitor Closely**: Keep track of bot performance and market conditions
- **Set Limits**: Configure appropriate stop losses and investment limits
- **Stay Informed**: Keep up with market news and protocol updates

**Never invest more than you can afford to lose.**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

### Community
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: General questions and community support
- **Telegram**: Real-time community chat (link in repository)

### Professional Support
- **Custom Development**: Tailored bot modifications
- **Deployment Assistance**: Help with setup and configuration
- **Strategy Consulting**: Trading strategy optimization

### Donations
If this project helps you, consider supporting development:
- **ETH/Base**: `0xYOUR_DONATION_ADDRESS`
- **GitHub Sponsors**: [Sponsor this project](https://github.com/sponsors/Luiqbd)

## 🔄 Changelog

### v1.0.0 (Latest)
- ✅ Complete memecoin sniping strategy
- ✅ Advanced altcoin trading with technical analysis
- ✅ Comprehensive security protections
- ✅ Full Telegram integration with interactive controls
- ✅ Multi-DEX support (BaseSwap, Uniswap v3, Camelot)
- ✅ Automated testing and CI/CD pipeline
- ✅ Docker and Render deployment support

### Roadmap
- 🔄 Advanced ML-based price prediction
- 🔄 Cross-chain support (Ethereum, Arbitrum, Optimism)
- 🔄 NFT trading integration
- 🔄 Advanced portfolio analytics dashboard
- 🔄 Mobile app companion

---

**Built with ❤️ for the Base ecosystem**