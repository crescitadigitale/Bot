#!/usr/bin/env python3
"""
Setup script for CrescitaDigitale Telegram Bot
Helps users configure the bot for first-time use
"""

import os
import sys
import shutil

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def create_config_file():
    """Create config.py from config_example.py"""
    if os.path.exists('config.py'):
        response = input("⚠️  config.py already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Keeping existing config.py")
            return True
    
    if os.path.exists('config_example.py'):
        shutil.copy('config_example.py', 'config.py')
        print("✅ Created config.py from config_example.py")
        print("📝 Please edit config.py and add your bot token and admin IDs")
        return True
    else:
        print("❌ Error: config_example.py not found!")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['screenshots', 'logs']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"📁 Directory already exists: {directory}")

def check_requirements():
    """Check if requirements are installed"""
    try:
        import telegram
        print("✅ python-telegram-bot is installed")
        return True
    except ImportError:
        print("❌ python-telegram-bot is not installed")
        print("Run: pip install -r requirements.txt")
        return False

def main():
    """Main setup function"""
    print("🚀 CrescitaDigitale Bot Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        print("\n📦 To install requirements, run:")
        print("pip install -r requirements.txt")
        print("\nThen run this setup script again.")
        sys.exit(1)
    
    # Create config file
    if not create_config_file():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit config.py and add your bot token from @BotFather")
    print("2. Add your Telegram ID to ADMIN_IDS in config.py")
    print("3. Run the bot with: python bot.py")
    
    print("\n💡 Need help getting your bot token?")
    print("1. Open Telegram and search for @BotFather")
    print("2. Send /newbot and follow the instructions")
    print("3. Copy the token to config.py")
    
    print("\n💡 Need your Telegram ID?")
    print("1. Search for @userinfobot on Telegram")
    print("2. Send any message to get your ID")
    print("3. Add it to ADMIN_IDS in config.py")

if __name__ == "__main__":
    main()