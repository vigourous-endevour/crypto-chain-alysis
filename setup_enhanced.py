#!/usr/bin/env python3
"""
Enhanced Token Analyzer Setup Script
Automatically configures the enhanced version with Etherscan integration
"""

import os
import json
import sys
import subprocess
from pathlib import Path

def print_banner():
    print("""
🔍 Enhanced Token Launch Analyzer Setup
=====================================
Setting up advanced token analysis with Etherscan integration...
""")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    
    packages = [
        'aiohttp>=3.8.5',
        'flask>=2.3.3',
        'flask-cors>=4.0.0',
        'web3>=6.0.0',
        'requests>=2.31.0',
        'python-dateutil>=2.8.2',
        'websockets>=11.0.3'
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    return True

def create_enhanced_files():
    """Create the necessary files for enhanced functionality"""
    print("\n📁 Creating enhanced analyzer files...")
    
    files_to_create = [
        "etherscan_analyzer.py",
        "flask_server_enhanced.py", 
        "config_etherscan.json"
    ]
    
    print("✅ Files to create:")
    for file in files_to_create:
        print(f"   • {file}")
    
    print("\n📝 Please copy the code from the artifacts into these files:")
    print("1. Copy 'Etherscan API Integration Module' → etherscan_analyzer.py")
    print("2. Copy 'Enhanced Flask Server with Etherscan Integration' → flask_server_enhanced.py")
    print("3. Copy 'Enhanced Configuration with Etherscan Integration' → config_etherscan.json")
    
    return True

def print_setup_complete():
    """Print setup completion message"""
    print("""
🎉 Enhanced Token Analyzer Setup Instructions
===========================================

📋 Next Steps:

1. 🔑 Get API Keys (FREE):
   • Etherscan: https://etherscan.io/apis
   • Basescan: https://basescan.org/apis
   • Alchemy: https://alchemy.com

2. ⚙️ Configure API Keys:
   • Edit config_etherscan.json
   • Replace YOUR_*_API_KEY with actual keys

3. 📁 Create Required Files:
   • Copy the provided code into the files listed above
   • Ensure all Python files are in the same directory

4. 🚀 Start the Enhanced Analyzer:
   • Run: python flask_server_enhanced.py

5. 🌐 Access Enhanced Dashboard:
   • Open: http://localhost:5000
   • Click "Test Etherscan API" to verify setup

🔍 Enhanced Features:
✅ Etherscan contract verification
✅ Source code security analysis  
✅ Creator reputation scoring
✅ Transfer pattern detection
✅ Advanced risk assessment
✅ Real-time monitoring
✅ Enhanced alerting system

🆘 Need Help?
• Make sure all files are created with the provided code
• Verify API keys are correctly configured
• Test with known contracts first (e.g., Uniswap token)

Happy analyzing! 🔍💎
""")

def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed during dependency installation")
        sys.exit(1)
    
    # Create files instruction
    create_enhanced_files()
    
    # Print completion message
    print_setup_complete()

if __name__ == '__main__':
    main()