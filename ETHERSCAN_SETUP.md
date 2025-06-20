# 🔍 Etherscan Integration Setup Guide

## Quick Setup Instructions

### 1. Create These Files in Your Repository

Copy each code block below into separate files:

#### File 1: `etherscan_analyzer.py`
- Copy the code from artifact "File 1: etherscan_analyzer.py"

#### File 2: `config_etherscan.json` 
- Copy the code from artifact "File 2: config_etherscan.json"

#### File 3: `flask_server_enhanced.py`
- Copy the code from artifact "Enhanced Flask Server with Etherscan Integration"

### 2. Get Free API Keys

#### Etherscan (for Ethereum):
1. Go to: https://etherscan.io/apis
2. Create free account
3. Generate API key
4. Free: 5 req/sec, 100K req/day

#### Basescan (for Base):
1. Go to: https://basescan.org/apis  
2. Create account
3. Generate API key

### 3. Configure API Keys

Edit `config_etherscan.json`:
```json
{
  "etherscan": {
    "networks": {
      "ethereum": {
        "api_key": "YOUR_ACTUAL_ETHERSCAN_API_KEY_HERE"
      },
      "base": {
        "api_key": "YOUR_ACTUAL_BASESCAN_API_KEY_HERE"
      }
    }
  }
}
```

### 4. Install Dependencies

```bash
pip install flask flask-cors aiohttp web3 requests python-dateutil
```

### 5. Run Enhanced Server

```bash
python flask_server_enhanced.py
```

### 6. Access Dashboard

- Open: http://localhost:5000
- Click "Test Etherscan API" to verify setup

## Enhanced Features

✅ **Contract Verification** - Automatic Etherscan checking  
✅ **Source Code Analysis** - Detect dangerous functions  
✅ **Creator Reputation** - Analyze creator history  
✅ **Transfer Patterns** - Detect wash trading  
✅ **Advanced Risk Scoring** - Multi-factor assessment  

## API Endpoints

```bash
# Test API connectivity
GET /api/etherscan/test

# Enhanced token analysis  
GET /api/enhanced-analysis/ethereum/0x1f9840a85d5af5bf1d1762f925bdaddc4201f984

# Contract verification
GET /api/etherscan/verify/ethereum/0x...

# Creator reputation
GET /api/creator-analysis/ethereum/0x...
```

## Quick Test

Test with Uniswap token (known good):
```bash
curl "http://localhost:5000/api/enhanced-analysis/ethereum/0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
```

Should return LOW risk with positive indicators.

## Files to Upload to GitHub

1. `etherscan_analyzer.py` (copy from artifact)
2. `config_etherscan.json` (copy from artifact) 
3. `flask_server_enhanced.py` (copy from artifact)
4. `ETHERSCAN_SETUP.md` (this file)

## Troubleshooting

- **API Test Fails**: Check API keys in config
- **Import Errors**: Ensure all dependencies installed
- **No Response**: Verify server is running on port 5000

You now have professional-grade token analysis with Etherscan integration! 🚀