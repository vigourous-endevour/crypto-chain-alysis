# 🔍 Multi-Chain Token Launch Analyzer

A comprehensive tool for detecting and analyzing new token launches across Ethereum, Solana, and Base blockchains with advanced scam/rug pull detection capabilities.

## 🎯 Features

- **Real-time Monitoring**: Continuously monitors new token launches across multiple blockchains
- **Advanced Risk Assessment**: Multi-factor algorithms to detect potential scams and rug pulls
- **Multi-Chain Support**: Ethereum, Solana, and Base blockchain monitoring
- **Interactive Dashboard**: Real-time web dashboard for visualizing and analyzing token launches
- **RESTful API**: Programmatic access to data and monitoring controls
- **Alert System**: Configurable alerts for high-risk token launches
- **Export Functionality**: JSON/CSV data export for further analysis
- **Honeypot Detection**: Advanced contract analysis to identify honeypot patterns
- **Social Signals**: Framework for analyzing social media presence and sentiment

## 🚨 Risk Detection Capabilities

### Critical Risk Indicators
- **Honeypot Contracts** - Code patterns that prevent selling
- **Mint Functions** - Ability to create unlimited tokens
- **Ownership Control** - Non-renounced ownership allowing rug pulls
- **Known Scammer Addresses** - Creator flagged in threat database

### High Risk Indicators
- **Suspicious Names** - "SafeMoon", "ElonDoge", "PumpRocket" patterns
- **Very Low Liquidity** - Less than 0.1 ETH initial liquidity
- **New Creator Addresses** - Less than 5 previous transactions
- **Wash Trading** - Artificial volume inflation

### Medium Risk Indicators
- **High Token Supply** - Dilution risk
- **Unverified Contracts** - No source code verification
- **Low Social Presence** - No website/social media
- **High Holder Concentration** - Few wallets hold majority

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Node.js (optional, for frontend development)
- SQLite3
- Internet connection for blockchain API access

### 1. Clone the Repository

```bash
git clone https://github.com/vigourous-endevour/crypto-chain-alysis.git
cd crypto-chain-alysis
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\\Scripts\\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Edit `config.json` with your RPC endpoints:

```json
{
  "ethereum": {
    "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
  },
  "base": {
    "rpc_url": "https://base-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY"
  },
  "solana": {
    "rpc_url": "https://api.mainnet-beta.solana.com"
  }
}
```

### 4. Get API Keys

#### Alchemy (Recommended)
1. Sign up at [alchemy.com](https://alchemy.com)
2. Create apps for Ethereum and Base networks
3. Copy the API URLs to your config file

#### Alternative RPC Providers
- **Infura**: [infura.io](https://infura.io)
- **QuickNode**: [quicknode.com](https://quicknode.com)
- **Moralis**: [moralis.io](https://moralis.io)

## 🚀 Usage

### Start the Application

```bash
# Start the Flask server
python flask_server.py
```

The application will be available at:
- **Dashboard**: http://localhost:5000
- **API**: http://localhost:5000/api/*

### Start Monitoring

You can start monitoring through the API:

```bash
# Start monitoring
curl -X POST http://localhost:5000/api/monitoring/start

# Check status
curl http://localhost:5000/api/monitoring/status

# Stop monitoring
curl -X POST http://localhost:5000/api/monitoring/stop
```

Or use the web interface to control monitoring.

## 📊 Dashboard Features

The web dashboard provides:
- **Real-time token feed** with risk scores
- **Statistical overview** of detected tokens
- **Risk distribution charts** 
- **Filtering and search** capabilities
- **Detailed token analysis** reports
- **Alert system** for high-risk tokens

## 🔧 API Endpoints

### Token Data
- `GET /api/tokens` - Get token launches with filtering
- `GET /api/token/<chain>/<address>` - Get specific token details
- `GET /api/stats` - Get statistics and analytics

### Monitoring Control
- `POST /api/monitoring/start` - Start blockchain monitoring
- `POST /api/monitoring/stop` - Stop monitoring
- `GET /api/monitoring/status` - Get monitoring status

### Data Export
- `GET /api/export?format=json` - Export as JSON
- `GET /api/export?format=csv` - Export as CSV

### Query Parameters

For `/api/tokens`:
- `hours` - Time range (default: 24)
- `min_risk_score` - Minimum risk score (0.0-1.0)
- `chain` - Filter by chain (ethereum/base/solana/all)
- `risk_level` - Filter by risk level (LOW/MEDIUM/HIGH/CRITICAL/all)

## 🧠 Risk Assessment Algorithm

The tool uses multiple factors to assess token risk:

### Risk Scoring Components
1. **Contract Analysis** (40% weight)
   - Mint/burn function presence
   - Ownership renouncement
   - Honeypot patterns
   - Contract verification

2. **Creator Analysis** (25% weight)
   - Address transaction history
   - Known scammer database
   - ETH balance

3. **Liquidity Analysis** (20% weight)
   - Initial liquidity amount
   - DEX pool analysis
   - Locked liquidity

4. **Social Signals** (10% weight)
   - Website presence
   - Social media following
   - Community engagement

5. **Trading Patterns** (5% weight)
   - Wash trading detection
   - Bot activity
   - Volume analysis

### Risk Levels
- **0.0-0.4**: Low Risk ✅
- **0.4-0.6**: Medium Risk ⚡
- **0.6-0.8**: High Risk ⚠️
- **0.8-1.0**: Critical Risk 🚨

## 🔒 Security Features

- **Multi-layer Analysis** - Combines multiple risk factors
- **Pattern Recognition** - ML-ready framework for detecting scam patterns
- **Threat Intelligence** - Maintains database of known bad actors
- **Historical Tracking** - Monitors token behavior over time

## 📈 Advanced Analytics

The system tracks:
- **Token launch frequency** by chain and time
- **Risk score distributions** over time  
- **Creator address patterns** and repeat offenders
- **Liquidity trends** and market conditions
- **Social sentiment** correlation with risk

## ⚡ Performance Optimizations

- **Async Processing** - Handles multiple chains simultaneously
- **Database Indexing** - Fast queries on large datasets
- **Rate Limiting** - Respects RPC provider limits
- **Caching** - Reduces redundant API calls
- **Batch Processing** - Efficient block analysis

## 🎯 Use Cases

### For Investors
- Screen new tokens before investing
- Get early warnings about potential scams
- Track token performance post-launch
- Historical analysis of successful vs failed projects

### For Researchers
- Study scam patterns and evolution
- Analyze market manipulation techniques  
- Track DeFi ecosystem growth
- Gather data for academic research

### For Security Teams
- Monitor for new threats
- Track known bad actors
- Generate threat intelligence
- Protect exchange listings

## 🔧 Extending the Tool

### Adding New Blockchains

1. Create a new monitor class:
```python
class NewChainMonitor:
    def __init__(self, client):
        self.client = client
    
    async def monitor_new_tokens(self, callback):
        # Implementation
        pass
```

2. Add configuration for the new chain
3. Integrate into the main analyzer

### Custom Risk Factors

Add new risk analysis methods:

```python
async def analyze_custom_risk(self, contract_address):
    # Custom risk analysis logic
    risk_factors = []
    risk_score = 0.0
    
    # Your analysis here
    
    return risk_score, risk_factors
```

### Alert Integration

Extend the alert system:

```python
async def send_discord_alert(self, token_launch):
    # Discord webhook integration
    pass

async def send_telegram_alert(self, token_launch):
    # Telegram bot integration
    pass
```

## 🔄 Continuous Monitoring

The system provides 24/7 monitoring with:
- **Real-time block processing** on all supported chains
- **Automatic risk assessment** of every new token
- **Instant alerts** for critical risk detections
- **Historical data collection** for trend analysis
- **Performance metrics** and uptime monitoring

## 🛡️ Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Rate Limits**: Respect RPC provider rate limits
3. **Data Privacy**: Be mindful of storing sensitive blockchain data
4. **Legal Compliance**: Ensure compliance with local regulations

## 🐛 Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check your RPC endpoints are correct
   - Verify API keys are valid
   - Ensure internet connectivity

2. **High CPU Usage**
   - Reduce monitoring frequency
   - Limit the number of blocks processed
   - Use more efficient RPC endpoints

3. **Database Errors**
   - Check SQLite permissions
   - Ensure disk space is available
   - Verify database path is writable

### Debug Mode

Run with debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Project Structure

```
crypto-chain-alysis/
├── token_analyzer.py          # Core monitoring and analysis
├── flask_server.py           # Web server and API
├── enhanced_analyzer.py      # Advanced risk analysis
├── dashboard.html           # Web dashboard
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── LICENSE               # GPL-3.0 License
```

## 🤝 Contributing

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Test thoroughly
5. Submit a pull request

## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and research purposes. Always conduct your own research before making investment decisions. The authors are not responsible for any financial losses incurred from using this tool.

## 🙏 Acknowledgments

- Built with love for the crypto community
- Thanks to all RPC providers for blockchain access
- Inspired by the need for safer DeFi investing

---

**⭐ Star this repository if you find it useful!**

**📧 Questions? Open an issue or reach out to the community.**