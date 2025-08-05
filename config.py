# Configuration file for CrescitaDigitale Bot
# Telegram Bot @CrescitaDigitale - Instagram Interaction Exchange System

# Bot Token from BotFather
# Get your token from @BotFather on Telegram:
# 1. Start a chat with @BotFather
# 2. Send /newbot
# 3. Follow the instructions to create your bot
# 4. Copy the token here
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Admin Telegram IDs
# Add the Telegram IDs of users who should have admin privileges
# To get your Telegram ID:
# 1. Start a chat with @userinfobot
# 2. Send any message to get your ID
# 3. Add your ID to the list below
ADMIN_IDS = [
    123456789,  # Replace with actual admin Telegram ID
    987654321,  # Add more admin IDs as needed
]

# Database Configuration
DATABASE_FILE = "crescita_digitale.db"
BACKUP_DATABASE_FILE = "backup.db"

# Bot Settings
DEFAULT_COIN_BALANCE = 10  # Starting coin balance for new users
BACKUP_TIME_HOUR = 2  # Hour for daily backup (24-hour format)
BACKUP_TIME_MINUTE = 0  # Minute for daily backup

# Action costs (in Coins)
ACTION_COSTS = {
    'like': 1,
    'follow': 5,
    'commento': 6,
    'condivisione_story': 10,
    'visualizzazione_reel': 5,
    'salvataggio': 5,
    'invio_chat': 1
}

# Earnings percentages
PRIMARY_PROFILE_EARNINGS = 0.25  # 25% for primary profile
SECONDARY_PROFILE_EARNINGS = 0.125  # 12.5% for secondary profiles

# Coin packages for purchase
COIN_PACKAGES = {
    100: 5.0,   # 100 Coins for €5
    250: 10.0,  # 250 Coins for €10
    500: 18.0,  # 500 Coins for €18
    1000: 30.0  # 1000 Coins for €30
}

# Secondary profile requirements
SECONDARY_PROFILE_MIN_POSTS = 10
SECONDARY_PROFILE_MIN_FOLLOWERS = 100
MAX_SECONDARY_PROFILES = 2

# Screenshot requirements
SCREENSHOT_REQUIRED_COST_THRESHOLD = 5  # Actions costing 5+ coins require screenshots

# Ranking periods
RANKING_PERIODS = ['weekly', 'monthly']
TOP_RANKINGS_COUNT = 5

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"

# Notification settings
ENABLE_PUSH_NOTIFICATIONS = True
NOTIFICATION_CHECK_INTERVAL = 300  # 5 minutes in seconds