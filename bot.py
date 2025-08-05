#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot @CrescitaDigitale - Instagram Interaction Exchange System
Created with python-telegram-bot library v20.x
"""

import logging
import sqlite3
import asyncio
import random
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import re

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

# Import configuration
from config import ADMIN_IDS, BOT_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Conversation states
(WAITING_PROFILE, WAITING_INTERACTION_TYPE, WAITING_POST_LINK, 
 WAITING_QUANTITY, WAITING_SCREENSHOT, WAITING_PURCHASE_NAME,
 WAITING_PURCHASE_PHONE, WAITING_PURCHASE_COINS, WAITING_TICKET_MESSAGE,
 WAITING_ADMIN_LINK, WAITING_ADMIN_ACTION, WAITING_ADMIN_QUANTITY,
 WAITING_ADMIN_COIN) = range(12)

# Database file path
DB_FILE = 'crescita_digitale.db'
BACKUP_DB_FILE = 'backup.db'

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                instagram_username TEXT,
                coin_balance INTEGER DEFAULT 10,
                secondary_profile_1 TEXT DEFAULT NULL,
                secondary_profile_2 TEXT DEFAULT NULL,
                secondary_profile_1_verified BOOLEAN DEFAULT FALSE,
                secondary_profile_2_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER,
                post_link TEXT NOT NULL,
                action_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                cost_per_action INTEGER NOT NULL,
                total_cost INTEGER NOT NULL,
                completed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                screenshot_id TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (requester_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # User interactions (who did what)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                interaction_id INTEGER,
                screenshot_id TEXT DEFAULT NULL,
                earnings INTEGER,
                profile_type TEXT DEFAULT 'primary',
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                FOREIGN KEY (interaction_id) REFERENCES interactions (id)
            )
        ''')
        
        # Rankings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                points INTEGER DEFAULT 0,
                period TEXT NOT NULL,
                period_start DATE,
                period_end DATE,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Purchase forms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                coins_requested INTEGER NOT NULL,
                amount_euro REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # Screenshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screenshots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                file_path TEXT NOT NULL,
                interaction_id INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                FOREIGN KEY (interaction_id) REFERENCES interactions (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_status ON interactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_interactions_user_id ON user_interactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rankings_period ON rankings(period, period_start)')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user data by Telegram ID"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'telegram_id': row[0],
                'instagram_username': row[1],
                'coin_balance': row[2],
                'secondary_profile_1': row[3],
                'secondary_profile_2': row[4],
                'secondary_profile_1_verified': row[5],
                'secondary_profile_2_verified': row[6],
                'created_at': row[7],
                'last_active': row[8]
            }
        return None
    
    def create_user(self, telegram_id: int) -> bool:
        """Create a new user"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (telegram_id) VALUES (?)',
                (telegram_id,)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def update_user_balance(self, telegram_id: int, amount: int) -> bool:
        """Update user's coin balance"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET coin_balance = coin_balance + ?, last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?',
            (amount, telegram_id)
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def set_user_profile(self, telegram_id: int, username: str, profile_type: str = 'primary') -> bool:
        """Set user's Instagram profile"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if profile_type == 'primary':
            cursor.execute(
                'UPDATE users SET instagram_username = ?, last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?',
                (username, telegram_id)
            )
        elif profile_type == 'secondary_1':
            cursor.execute(
                'UPDATE users SET secondary_profile_1 = ?, last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?',
                (username, telegram_id)
            )
        elif profile_type == 'secondary_2':
            cursor.execute(
                'UPDATE users SET secondary_profile_2 = ?, last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?',
                (username, telegram_id)
            )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_available_interactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get available interactions for a user"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Get interactions that are not from this user and are still active
        cursor.execute('''
            SELECT i.*, u.instagram_username 
            FROM interactions i
            JOIN users u ON i.requester_id = u.telegram_id
            WHERE i.requester_id != ? 
            AND i.status = 'active' 
            AND i.completed_count < i.quantity
            ORDER BY RANDOM()
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in rows:
            interactions.append({
                'id': row[0],
                'requester_id': row[1],
                'post_link': row[2],
                'action_type': row[3],
                'quantity': row[4],
                'cost_per_action': row[5],
                'total_cost': row[6],
                'completed_count': row[7],
                'status': row[8],
                'screenshot_id': row[9],
                'created_at': row[10],
                'requester_username': row[11]
            })
        
        return interactions
    
    def create_interaction_request(self, user_id: int, post_link: str, action_type: str, 
                                 quantity: int, cost_per_action: int) -> int:
        """Create a new interaction request"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        total_cost = quantity * cost_per_action
        
        cursor.execute('''
            INSERT INTO interactions (requester_id, post_link, action_type, quantity, 
                                    cost_per_action, total_cost)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, post_link, action_type, quantity, cost_per_action, total_cost))
        
        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return interaction_id
    
    def complete_interaction(self, user_id: int, interaction_id: int, earnings: int, 
                           profile_type: str = 'primary', screenshot_id: str = None) -> bool:
        """Mark an interaction as completed by a user"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if user already completed this interaction
        cursor.execute('''
            SELECT id FROM user_interactions 
            WHERE user_id = ? AND interaction_id = ?
        ''', (user_id, interaction_id))
        
        if cursor.fetchone():
            conn.close()
            return False  # Already completed
        
        # Add user interaction record
        cursor.execute('''
            INSERT INTO user_interactions (user_id, interaction_id, earnings, profile_type, screenshot_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, interaction_id, earnings, profile_type, screenshot_id))
        
        # Update interaction completed count
        cursor.execute('''
            UPDATE interactions 
            SET completed_count = completed_count + 1
            WHERE id = ?
        ''', (interaction_id,))
        
        # Update user balance
        cursor.execute('''
            UPDATE users 
            SET coin_balance = coin_balance + ?, last_active = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (earnings, user_id))
        
        conn.commit()
        conn.close()
        return True
    
    def create_ticket(self, user_id: int, message: str) -> int:
        """Create a support ticket"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tickets (user_id, message)
            VALUES (?, ?)
        ''', (user_id, message))
        
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return ticket_id
    
    def create_purchase_form(self, user_id: int, name: str, phone: str, 
                           coins_requested: int, amount_euro: float) -> int:
        """Create a purchase form"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO purchase_forms (user_id, name, phone, coins_requested, amount_euro)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, phone, coins_requested, amount_euro))
        
        form_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return form_id
    
    def get_user_rankings(self, period: str, limit: int = 5) -> List[Dict]:
        """Get user rankings for a specific period"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.user_id, r.points, u.instagram_username
            FROM rankings r
            JOIN users u ON r.user_id = u.telegram_id
            WHERE r.period = ?
            ORDER BY r.points DESC
            LIMIT ?
        ''', (period, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        rankings = []
        for i, row in enumerate(rows):
            rankings.append({
                'position': i + 1,
                'user_id': row[0],
                'points': row[1],
                'username': row[2] or 'Utente senza profilo'
            })
        
        return rankings
    
    def backup_database(self):
        """Create a backup of the database"""
        try:
            shutil.copy2(self.db_file, BACKUP_DB_FILE)
            logger.info(f"Database backup created: {BACKUP_DB_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return False

# Initialize database manager
db = DatabaseManager()

# Action costs and earnings
ACTION_COSTS = {
    'like': 1,
    'follow': 5,
    'commento': 6,
    'condivisione_story': 10,
    'visualizzazione_reel': 5,
    'salvataggio': 5,
    'invio_chat': 1
}

ACTION_NAMES = {
    'like': '👍 Like',
    'follow': '➕ Follow',
    'commento': '💬 Commento',
    'condivisione_story': '📤 Condivisione Story',
    'visualizzazione_reel': '🎥 Visualizzazione Reel',
    'salvataggio': '💾 Salvataggio',
    'invio_chat': '💌 Invio in chat'
}

def calculate_earnings(cost: int, profile_type: str = 'primary') -> int:
    """Calculate earnings based on action cost and profile type"""
    if profile_type == 'primary':
        return int(cost * 0.25)  # 25% for primary profile
    else:
        return int(cost * 0.125)  # 12.5% for secondary profiles

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_IDS

def is_valid_instagram_link(link: str) -> bool:
    """Validate Instagram link format"""
    pattern = r'https?://(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/[A-Za-z0-9_-]+/?'
    return bool(re.match(pattern, link))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        db.create_user(user_id)
        welcome_text = (
            "🎉 *Benvenuto in CrescitaDigitale!* 🎉\n\n"
            "Il tuo bot per far crescere il tuo profilo Instagram! 🚀\n\n"
            "💰 Hai ricevuto *10 Coin* di benvenuto!\n\n"
            "🔥 *Come funziona:*\n"
            "• Guadagna Coin completando interazioni\n"
            "• Usa i Coin per ricevere interazioni sul tuo profilo\n"
            "• Partecipa alle classifiche settimanali e mensili\n\n"
            "📱 *Inizia subito:*\n"
            "1. Registra il tuo profilo Instagram con /profilo\n"
            "2. Clicca su 'Inizia Ora' per guadagnare Coin\n"
            "3. Usa 'Ricevi Interazioni' per far crescere il tuo profilo\n\n"
            "💪 *Sei pronto a crescere? Iniziamo!*"
        )
    else:
        welcome_text = (
            f"🎉 *Bentornato!* 🎉\n\n"
            f"💰 Saldo attuale: *{user['coin_balance']} Coin*\n\n"
            "🚀 Pronto a continuare la tua crescita su Instagram?\n\n"
            "Usa i pulsanti qui sotto per iniziare!"
        )
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🚀 Inizia Ora", callback_data="start_earning")],
        [InlineKeyboardButton("📈 Ricevi Interazioni", callback_data="receive_interactions")],
        [InlineKeyboardButton("💳 Acquista Coin", callback_data="buy_coins")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /profilo command"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ *Formato non corretto!*\n\n"
            "Usa: `/profilo <username>`\n\n"
            "Esempio: `/profilo mio_profilo_instagram`\n\n"
            "📝 *Nota:* Inserisci solo il nome utente senza @",
            parse_mode='Markdown'
        )
        return
    
    username = context.args[0].replace('@', '')
    user = db.get_user(user_id)
    
    if not user:
        db.create_user(user_id)
    
    # Check if it's a secondary profile
    if user and user['instagram_username']:
        if not user['secondary_profile_1']:
            profile_type = 'secondary_1'
            message = "📱 *Profilo secondario 1 registrato!*"
        elif not user['secondary_profile_2']:
            profile_type = 'secondary_2'
            message = "📱 *Profilo secondario 2 registrato!*"
        else:
            await update.message.reply_text(
                "❌ *Hai già registrato il massimo numero di profili!*\n\n"
                "• 1 profilo principale\n"
                "• 2 profili secondari\n\n"
                "Contatta l'admin se hai bisogno di modifiche.",
                parse_mode='Markdown'
            )
            return
    else:
        profile_type = 'primary'
        message = "✅ *Profilo principale registrato!*"
    
    if db.set_user_profile(user_id, username, profile_type):
        if profile_type.startswith('secondary'):
            message += (
                f"\n\n📋 *Username:* @{username}\n\n"
                "⚠️ *Attenzione:* I profili secondari devono essere verificati dall'admin.\n\n"
                "📋 *Requisiti per la verifica:*\n"
                "• Foto profilo\n"
                "• Almeno 10 post\n"
                "• Almeno 100 follower\n\n"
                "🔍 Usa /stato_profilo per controllare lo stato della verifica.\n\n"
                "💡 *Guadagni ridotti:* I profili secondari guadagnano il 12.5% invece del 25%."
            )
        else:
            message += f"\n\n📋 *Username:* @{username}\n\n🎉 Ora puoi iniziare a guadagnare Coin!"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "❌ *Errore durante la registrazione del profilo.*\n\n"
            "Riprova più tardi o contatta il supporto con /ticket",
            parse_mode='Markdown'
        )

async def profile_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stato_profilo command"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ *Profilo non trovato!*\n\n"
            "Registra prima il tuo profilo con /profilo <username>",
            parse_mode='Markdown'
        )
        return
    
    status_text = "📊 *Stato dei tuoi profili:*\n\n"
    
    # Primary profile
    if user['instagram_username']:
        status_text += f"✅ *Profilo principale:* @{user['instagram_username']}\n"
        status_text += "🟢 *Stato:* Verificato\n\n"
    else:
        status_text += "❌ *Profilo principale:* Non registrato\n\n"
    
    # Secondary profile 1
    if user['secondary_profile_1']:
        status_text += f"📱 *Profilo secondario 1:* @{user['secondary_profile_1']}\n"
        if user['secondary_profile_1_verified']:
            status_text += "🟢 *Stato:* Verificato\n\n"
        else:
            status_text += "🟡 *Stato:* In attesa di verifica\n\n"
    else:
        status_text += "📱 *Profilo secondario 1:* Non registrato\n\n"
    
    # Secondary profile 2
    if user['secondary_profile_2']:
        status_text += f"📱 *Profilo secondario 2:* @{user['secondary_profile_2']}\n"
        if user['secondary_profile_2_verified']:
            status_text += "🟢 *Stato:* Verificato\n\n"
        else:
            status_text += "🟡 *Stato:* In attesa di verifica\n\n"
    else:
        status_text += "📱 *Profilo secondario 2:* Non registrato\n\n"
    
    status_text += (
        "💡 *Informazioni:*\n"
        "• I profili secondari richiedono verifica manuale\n"
        "• Guadagni: 25% (principale), 12.5% (secondari)\n"
        "• Massimo 2 profili secondari per utente"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bilancio command"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        db.create_user(user_id)
        balance = 10
    else:
        balance = user['coin_balance']
    
    balance_text = (
        f"💰 *Il tuo saldo:*\n\n"
        f"🪙 *{balance} Coin*\n\n"
        "💡 *Come guadagnare più Coin:*\n"
        "• Clicca 'Inizia Ora' per completare interazioni\n"
        "• Ogni azione completata ti fa guadagnare Coin\n"
        "• Più azioni fai, più guadagni!\n\n"
        "💳 *Hai bisogno di più Coin?*\n"
        "Usa il pulsante 'Acquista Coin' per comprarne altri!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Inizia Ora", callback_data="start_earning")],
        [InlineKeyboardButton("💳 Acquista Coin", callback_data="buy_coins")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        balance_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ticket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ticket command"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🎫 *Supporto Tecnico*\n\n"
            "Per inviare un messaggio al nostro team di supporto usa:\n\n"
            "`/ticket <il tuo messaggio>`\n\n"
            "Esempio:\n"
            "`/ticket Ho un problema con il mio saldo`\n\n"
            "📞 Il nostro team ti risponderà il prima possibile!",
            parse_mode='Markdown'
        )
        return
    
    message = ' '.join(context.args)
    user = db.get_user(user_id)
    
    if not user:
        db.create_user(user_id)
    
    ticket_id = db.create_ticket(user_id, message)
    
    await update.message.reply_text(
        f"✅ *Ticket inviato con successo!*\n\n"
        f"🎫 *ID Ticket:* #{ticket_id}\n\n"
        f"📝 *Messaggio:* {message}\n\n"
        "📞 Il nostro team di supporto ti contatterà presto!\n\n"
        "💡 *Suggerimento:* Salva l'ID del ticket per riferimenti futuri.",
        parse_mode='Markdown'
    )
    
    # Notify admins about new ticket
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🎫 *Nuovo Ticket Ricevuto*\n\n"
                f"👤 *Utente:* {user_id}\n"
                f"🎫 *ID:* #{ticket_id}\n"
                f"📝 *Messaggio:* {message}\n"
                f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about ticket: {e}")

async def rankings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /classifica command"""
    # For now, we'll show weekly rankings
    period = 'weekly'
    rankings = db.get_user_rankings(period, 5)
    
    if not rankings:
        rankings_text = (
            "📊 *Classifica Settimanale* 📊\n\n"
            "🏆 Nessun dato disponibile ancora!\n\n"
            "💪 *Sii il primo a guadagnare punti!*\n\n"
            "🎯 *Come guadagnare punti:*\n"
            "• Like = 1 punto\n"
            "• Follow = 5 punti\n"
            "• Commento = 6 punti\n"
            "• Condivisione Story = 10 punti\n"
            "• Visualizzazione Reel = 5 punti\n"
            "• Salvataggio = 5 punti\n"
            "• Invio in chat = 1 punto\n\n"
            "🏅 *I primi 5 riceveranno buoni Amazon!*\n"
            "Contatta l'admin per il premio!"
        )
    else:
        rankings_text = "🏆 *Classifica Settimanale* 🏆\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for ranking in rankings:
            medal = medals[ranking['position'] - 1]
            rankings_text += (
                f"{medal} *{ranking['position']}°* - @{ranking['username']}\n"
                f"     📊 {ranking['points']} punti\n\n"
            )
        
        rankings_text += (
            "🎁 *I primi 5 riceveranno buoni Amazon!*\n"
            "Contatta l'admin per il premio!\n\n"
            "💪 *Continua così! Più interazioni = più punti!*"
        )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Guadagna Punti", callback_data="start_earning")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        rankings_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# Callback query handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "start_earning":
        await handle_start_earning(update, context)
    elif data == "receive_interactions":
        await handle_receive_interactions(update, context)
    elif data == "buy_coins":
        await handle_buy_coins(update, context)
    elif data.startswith("do_action_"):
        await handle_do_action(update, context)
    elif data.startswith("interaction_type_"):
        await handle_interaction_type_selection(update, context)
    elif data.startswith("confirm_action_"):
        await handle_confirm_action(update, context)
    elif data.startswith("upload_screenshot_"):
        await handle_upload_screenshot(update, context)
    elif data == "main_menu":
        await handle_main_menu(update, context)

async def handle_start_earning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Inizia Ora' button"""
    query = update.callback_query
    user_id = query.from_user.id
    
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id)
        user = db.get_user(user_id)
    
    # Get available interactions
    interactions = db.get_available_interactions(user_id, 5)
    
    if not interactions:
        await query.edit_message_text(
            "😔 *Nessuna interazione disponibile al momento!*\n\n"
            "🔄 Riprova tra qualche minuto o chiedi agli amici di pubblicare nuove richieste!\n\n"
            "💡 *Suggerimento:* Puoi anche creare le tue richieste con 'Ricevi Interazioni'!",
            parse_mode='Markdown'
        )
        return
    
    text = (
        "🚀 *Inizia a Guadagnare Coin!* 🚀\n\n"
        "Scegli un'interazione da completare:\n\n"
    )
    
    keyboard = []
    for interaction in interactions:
        action_name = ACTION_NAMES.get(interaction['action_type'], interaction['action_type'])
        cost = interaction['cost_per_action']
        earnings = calculate_earnings(cost)
        remaining = interaction['quantity'] - interaction['completed_count']
        
        button_text = f"{action_name} - Guadagna {earnings}C ({remaining} rimasti)"
        callback_data = f"do_action_{interaction['id']}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔄 Aggiorna Lista", callback_data="start_earning")])
    keyboard.append([InlineKeyboardButton("🏠 Menu Principale", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_do_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action selection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    interaction_id = int(query.data.split('_')[2])
    
    # Get interaction details
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.*, u.instagram_username 
        FROM interactions i
        JOIN users u ON i.requester_id = u.telegram_id
        WHERE i.id = ?
    ''', (interaction_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        await query.edit_message_text(
            "❌ *Interazione non trovata!*\n\n"
            "Questa interazione potrebbe essere stata completata o rimossa.",
            parse_mode='Markdown'
        )
        return
    
    interaction = {
        'id': row[0],
        'requester_id': row[1],
        'post_link': row[2],
        'action_type': row[3],
        'quantity': row[4],
        'cost_per_action': row[5],
        'total_cost': row[6],
        'completed_count': row[7],
        'status': row[8],
        'screenshot_id': row[9],
        'created_at': row[10],
        'requester_username': row[11]
    }
    
    action_name = ACTION_NAMES.get(interaction['action_type'], interaction['action_type'])
    earnings = calculate_earnings(interaction['cost_per_action'])
    
    text = (
        f"📋 *Dettagli Interazione*\n\n"
        f"🎯 *Azione:* {action_name}\n"
        f"💰 *Guadagno:* {earnings} Coin\n"
        f"👤 *Richiesto da:* @{interaction['requester_username']}\n"
        f"🔗 *Link:* {interaction['post_link']}\n\n"
        f"📝 *Istruzioni:*\n"
    )
    
    if interaction['action_type'] == 'like':
        text += "1. Clicca sul link\n2. Metti like al post\n3. Torna qui e conferma"
    elif interaction['action_type'] == 'follow':
        text += "1. Clicca sul link\n2. Segui l'account\n3. Fai uno screenshot\n4. Torna qui e invia la prova"
    elif interaction['action_type'] == 'commento':
        text += "1. Clicca sul link\n2. Scrivi un commento (min. 6 parole)\n3. Fai uno screenshot\n4. Torna qui e invia la prova"
    elif interaction['action_type'] == 'condivisione_story':
        text += "1. Clicca sul link\n2. Condividi nelle tue storie\n3. Fai uno screenshot\n4. Torna qui e invia la prova"
    elif interaction['action_type'] == 'visualizzazione_reel':
        text += "1. Clicca sul link\n2. Guarda il reel completo\n3. Fai uno screenshot\n4. Torna qui e invia la prova"
    elif interaction['action_type'] == 'salvataggio':
        text += "1. Clicca sul link\n2. Salva il post\n3. Fai uno screenshot\n4. Torna qui e invia la prova"
    elif interaction['action_type'] == 'invio_chat':
        text += "1. Clicca sul link\n2. Invia il post a un amico in chat\n3. Torna qui e conferma"
    
    keyboard = []
    
    # Check if screenshot is required (actions >= 5C)
    if interaction['cost_per_action'] >= 5:
        keyboard.append([InlineKeyboardButton("📸 Invia Screenshot", callback_data=f"upload_screenshot_{interaction_id}")])
    else:
        keyboard.append([InlineKeyboardButton("✅ Ho Completato", callback_data=f"confirm_action_{interaction_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="start_earning")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_receive_interactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Ricevi Interazioni' button"""
    query = update.callback_query
    user_id = query.from_user.id
    
    user = db.get_user(user_id)
    if not user:
        await query.edit_message_text(
            "❌ *Profilo non trovato!*\n\n"
            "Registra prima il tuo profilo con /profilo <username>",
            parse_mode='Markdown'
        )
        return
    
    if not user['instagram_username']:
        await query.edit_message_text(
            "❌ *Profilo Instagram non registrato!*\n\n"
            "Registra prima il tuo profilo con /profilo <username>",
            parse_mode='Markdown'
        )
        return
    
    text = (
        "📈 *Ricevi Interazioni per il tuo Profilo!* 📈\n\n"
        f"💰 *Saldo attuale:* {user['coin_balance']} Coin\n\n"
        "Scegli il tipo di interazione che vuoi ricevere:\n\n"
        "*💰 Costi per interazione:*\n"
        "• 👍 Like - 1 Coin\n"
        "• ➕ Follow - 5 Coin\n"
        "• 💬 Commento - 6 Coin\n"
        "• 📤 Condivisione Story - 10 Coin\n"
        "• 🎥 Visualizzazione Reel - 5 Coin\n"
        "• 💾 Salvataggio - 5 Coin\n"
        "• 💌 Invio in chat - 1 Coin"
    )
    
    keyboard = [
        [InlineKeyboardButton("👍 Like (1C)", callback_data="interaction_type_like")],
        [InlineKeyboardButton("➕ Follow (5C)", callback_data="interaction_type_follow")],
        [InlineKeyboardButton("💬 Commento (6C)", callback_data="interaction_type_commento")],
        [InlineKeyboardButton("📤 Condivisione Story (10C)", callback_data="interaction_type_condivisione_story")],
        [InlineKeyboardButton("🎥 Visualizzazione Reel (5C)", callback_data="interaction_type_visualizzazione_reel")],
        [InlineKeyboardButton("💾 Salvataggio (5C)", callback_data="interaction_type_salvataggio")],
        [InlineKeyboardButton("💌 Invio in chat (1C)", callback_data="interaction_type_invio_chat")],
        [InlineKeyboardButton("🏠 Menu Principale", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_buy_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Acquista Coin' button"""
    query = update.callback_query
    user_id = query.from_user.id
    
    text = (
        "💳 *Acquista Coin* 💳\n\n"
        "Per acquistare Coin, compila il modulo qui sotto.\n"
        "Il nostro team esaminerà la tua richiesta e ti contatterà per il pagamento.\n\n"
        "💰 *Pacchetti disponibili:*\n"
        "• 100 Coin - €5\n"
        "• 250 Coin - €10\n"
        "• 500 Coin - €18\n"
        "• 1000 Coin - €30\n\n"
        "📝 Clicca il pulsante per iniziare:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Compila Modulo", callback_data="start_purchase_form")],
        [InlineKeyboardButton("🏠 Menu Principale", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# Admin commands
async def admin_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_richiesta command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "❌ *Formato non corretto!*\n\n"
            "Usa: `/admin_richiesta <link> <azione> <quantità> <coin>`\n\n"
            "Esempio: `/admin_richiesta https://instagram.com/p/123 follow 100 5`\n\n"
            "*Azioni disponibili:*\n"
            "like, follow, commento, condivisione_story, visualizzazione_reel, salvataggio, invio_chat",
            parse_mode='Markdown'
        )
        return
    
    link = context.args[0]
    action = context.args[1]
    try:
        quantity = int(context.args[2])
        cost_per_action = int(context.args[3])
    except ValueError:
        await update.message.reply_text("❌ Quantità e costo devono essere numeri!")
        return
    
    if not is_valid_instagram_link(link):
        await update.message.reply_text("❌ Link Instagram non valido!")
        return
    
    if action not in ACTION_COSTS:
        await update.message.reply_text(
            f"❌ Azione non valida! Azioni disponibili:\n"
            f"{', '.join(ACTION_COSTS.keys())}"
        )
        return
    
    # Create interaction request with admin as requester (use first admin ID)
    interaction_id = db.create_interaction_request(
        ADMIN_IDS[0], link, action, quantity, cost_per_action
    )
    
    await update.message.reply_text(
        f"✅ *Richiesta creata con successo!*\n\n"
        f"🆔 *ID:* {interaction_id}\n"
        f"🔗 *Link:* {link}\n"
        f"🎯 *Azione:* {ACTION_NAMES.get(action, action)}\n"
        f"📊 *Quantità:* {quantity}\n"
        f"💰 *Costo:* {cost_per_action} Coin per azione\n"
        f"💳 *Totale:* {quantity * cost_per_action} Coin",
        parse_mode='Markdown'
    )

async def admin_manage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_gestisci command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    # Get pending interactions
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.*, u.instagram_username 
        FROM interactions i
        JOIN users u ON i.requester_id = u.telegram_id
        WHERE i.status = 'active'
        ORDER BY i.created_at DESC
        LIMIT 10
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await update.message.reply_text("📋 Nessuna interazione attiva al momento.")
        return
    
    text = "📋 *Gestione Interazioni Attive:*\n\n"
    
    for row in rows:
        interaction_id = row[0]
        requester_username = row[11] or "Sconosciuto"
        action_name = ACTION_NAMES.get(row[3], row[3])
        completed = row[7]
        total = row[4]
        
        text += (
            f"🆔 *ID:* {interaction_id}\n"
            f"👤 *Utente:* @{requester_username}\n"
            f"🎯 *Azione:* {action_name}\n"
            f"📊 *Progresso:* {completed}/{total}\n"
            f"🔗 *Link:* {row[2]}\n\n"
        )
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_coin command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ *Formato non corretto!*\n\n"
            "Usa: `/admin_coin <user_id> <quantità>`\n\n"
            "Esempio: `/admin_coin 123456789 100`\n"
            "(quantità può essere negativa per rimuovere Coin)",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ User ID e quantità devono essere numeri!")
        return
    
    user = db.get_user(target_user_id)
    if not user:
        await update.message.reply_text("❌ Utente non trovato!")
        return
    
    old_balance = user['coin_balance']
    
    if db.update_user_balance(target_user_id, amount):
        new_balance = old_balance + amount
        
        await update.message.reply_text(
            f"✅ *Saldo aggiornato!*\n\n"
            f"👤 *Utente:* {target_user_id}\n"
            f"💰 *Saldo precedente:* {old_balance} Coin\n"
            f"🔄 *Modifica:* {amount:+d} Coin\n"
            f"💳 *Nuovo saldo:* {new_balance} Coin",
            parse_mode='Markdown'
        )
        
        # Notify user
        try:
            if amount > 0:
                message = f"🎉 Hai ricevuto {amount} Coin dall'admin! 💰"
            else:
                message = f"ℹ️ Ti sono stati rimossi {abs(amount)} Coin dall'admin."
            
            await context.bot.send_message(target_user_id, message)
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")
    else:
        await update.message.reply_text("❌ Errore durante l'aggiornamento del saldo!")

async def admin_campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_campagna command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "❌ *Formato non corretto!*\n\n"
            "Usa: `/admin_campagna <link> <azione> <quantità> <coin>`\n\n"
            "Esempio: `/admin_campagna https://instagram.com/p/123 follow 100 5`\n\n"
            "Questo creerà una campagna speciale con condizioni personalizzate.",
            parse_mode='Markdown'
        )
        return
    
    # This is similar to admin_request but could have special handling
    await admin_request_command(update, context)

async def admin_verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_verifica command for screenshot verification"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ *Formato non corretto!*\n\n"
            "Usa: `/admin_verifica <screenshot_id>`\n\n"
            "Esempio: `/admin_verifica 123456789_1_20231201_143022`",
            parse_mode='Markdown'
        )
        return
    
    screenshot_id = context.args[0]
    
    # Get screenshot details
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, ui.user_id, ui.interaction_id, ui.earnings, i.post_link, i.action_type
        FROM screenshots s
        JOIN user_interactions ui ON s.id = ui.screenshot_id
        JOIN interactions i ON ui.interaction_id = i.id
        WHERE s.id = ?
    ''', (screenshot_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        await update.message.reply_text("❌ Screenshot non trovato!")
        return
    
    screenshot_info = {
        'id': row[0],
        'user_id': row[1],
        'file_path': row[2],
        'interaction_id': row[3],
        'uploaded_at': row[4],
        'earnings': row[7],
        'post_link': row[8],
        'action_type': row[9]
    }
    
    try:
        # Send the screenshot to admin for verification
        with open(screenshot_info['file_path'], 'rb') as photo:
            await context.bot.send_photo(
                user_id,
                photo=photo,
                caption=(
                    f"📸 *Verifica Screenshot*\n\n"
                    f"🆔 *Screenshot ID:* {screenshot_id}\n"
                    f"👤 *Utente:* {screenshot_info['user_id']}\n"
                    f"🎯 *Azione:* {ACTION_NAMES.get(screenshot_info['action_type'], screenshot_info['action_type'])}\n"
                    f"🔗 *Link:* {screenshot_info['post_link']}\n"
                    f"💰 *Guadagno utente:* {screenshot_info['earnings']} Coin\n"
                    f"📅 *Data:* {screenshot_info['uploaded_at']}"
                ),
                parse_mode='Markdown'
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Errore nel caricare lo screenshot: {e}\n\n"
            f"Percorso file: {screenshot_info['file_path']}"
        )

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_stats command for bot statistics"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get various statistics
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM interactions WHERE status = "active"')
    active_interactions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM user_interactions')
    completed_interactions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "open"')
    open_tickets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM purchase_forms WHERE status = "pending"')
    pending_purchases = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(coin_balance) FROM users')
    total_coins = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM screenshots')
    total_screenshots = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 *Statistiche Bot CrescitaDigitale*\n\n"
        f"👥 *Utenti totali:* {total_users}\n"
        f"🔄 *Interazioni attive:* {active_interactions}\n"
        f"✅ *Interazioni completate:* {completed_interactions}\n"
        f"🎫 *Ticket aperti:* {open_tickets}\n"
        f"💳 *Richieste acquisto in sospeso:* {pending_purchases}\n"
        f"🪙 *Coin totali in circolazione:* {total_coins}\n"
        f"📸 *Screenshot caricati:* {total_screenshots}\n\n"
        f"📅 *Aggiornato:* {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def admin_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_broadcast command for sending messages to all users"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per usare questo comando.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 *Broadcast Message*\n\n"
            "Usa: `/admin_broadcast <messaggio>`\n\n"
            "Esempio: `/admin_broadcast Nuove funzionalità disponibili! Controlla il menu principale.`\n\n"
            "⚠️ *Attenzione:* Questo invierà il messaggio a tutti gli utenti registrati.",
            parse_mode='Markdown'
        )
        return
    
    message = ' '.join(context.args)
    
    # Get all users
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await update.message.reply_text("📭 Nessun utente registrato trovato.")
        return
    
    # Confirm broadcast
    await update.message.reply_text(
        f"📢 *Conferma Broadcast*\n\n"
        f"📝 *Messaggio:* {message}\n"
        f"👥 *Destinatari:* {len(users)} utenti\n\n"
        f"Invia 'CONFERMA' per procedere o qualsiasi altro messaggio per annullare.",
        parse_mode='Markdown'
    )
    
    # Store broadcast data for confirmation
    context.user_data['pending_broadcast'] = {
        'message': message,
        'users': users
    }

async def handle_broadcast_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirmation"""
    if update.message.text.upper() == 'CONFERMA':
        broadcast_data = context.user_data.get('pending_broadcast')
        
        if not broadcast_data:
            await update.message.reply_text("❌ Nessun broadcast in sospeso.")
            return
        
        message = broadcast_data['message']
        users = broadcast_data['users']
        
        # Send broadcast
        sent_count = 0
        failed_count = 0
        
        for user_row in users:
            user_id = user_row[0]
            try:
                await context.bot.send_message(
                    user_id,
                    f"📢 *Messaggio dall'Admin*\n\n{message}",
                    parse_mode='Markdown'
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user_id}: {e}")
                failed_count += 1
        
        await update.message.reply_text(
            f"✅ *Broadcast completato!*\n\n"
            f"📤 *Inviati:* {sent_count}\n"
            f"❌ *Falliti:* {failed_count}\n"
            f"👥 *Totale:* {len(users)}",
            parse_mode='Markdown'
        )
        
        # Clear pending broadcast
        context.user_data.pop('pending_broadcast', None)
    else:
        await update.message.reply_text("❌ Broadcast annullato.")
        context.user_data.pop('pending_broadcast', None)

# Daily backup task
async def daily_backup(context: ContextTypes.DEFAULT_TYPE):
    """Perform daily database backup"""
    if db.backup_database():
        logger.info("Daily database backup completed successfully")
        
        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"✅ *Backup Giornaliero Completato*\n\n"
                    f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    f"💾 File: {BACKUP_DB_FILE}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about backup: {e}")
    else:
        logger.error("Failed to create daily backup")

# Conversation handlers for multi-step interactions
async def start_purchase_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start purchase form conversation"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 *Modulo Acquisto Coin* - Passo 1/3\n\n"
        "Inserisci il tuo *nome completo*:",
        parse_mode='Markdown'
    )
    
    return WAITING_PURCHASE_NAME

async def purchase_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase form name input"""
    context.user_data['purchase_name'] = update.message.text
    
    await update.message.reply_text(
        "📝 *Modulo Acquisto Coin* - Passo 2/3\n\n"
        "Inserisci il tuo *numero di telefono*:",
        parse_mode='Markdown'
    )
    
    return WAITING_PURCHASE_PHONE

async def purchase_phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase form phone input"""
    context.user_data['purchase_phone'] = update.message.text
    
    await update.message.reply_text(
        "📝 *Modulo Acquisto Coin* - Passo 3/3\n\n"
        "Quanti Coin vuoi acquistare?\n\n"
        "*Pacchetti disponibili:*\n"
        "• 100 Coin (€5)\n"
        "• 250 Coin (€10)\n"
        "• 500 Coin (€18)\n"
        "• 1000 Coin (€30)\n\n"
        "Inserisci il numero di Coin desiderati:",
        parse_mode='Markdown'
    )
    
    return WAITING_PURCHASE_COINS

async def purchase_coins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase form coins input"""
    try:
        coins_requested = int(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "❌ Inserisci un numero valido di Coin!"
        )
        return WAITING_PURCHASE_COINS
    
    if coins_requested <= 0:
        await update.message.reply_text(
            "❌ Il numero di Coin deve essere positivo!"
        )
        return WAITING_PURCHASE_COINS
    
    # Calculate price (simplified pricing)
    if coins_requested <= 100:
        price = 5.0
    elif coins_requested <= 250:
        price = 10.0
    elif coins_requested <= 500:
        price = 18.0
    elif coins_requested <= 1000:
        price = 30.0
    else:
        price = coins_requested * 0.03  # 3 cents per coin for large quantities
    
    user_id = update.effective_user.id
    name = context.user_data['purchase_name']
    phone = context.user_data['purchase_phone']
    
    form_id = db.create_purchase_form(user_id, name, phone, coins_requested, price)
    
    await update.message.reply_text(
        f"✅ *Modulo inviato con successo!*\n\n"
        f"📋 *Riepilogo:*\n"
        f"👤 *Nome:* {name}\n"
        f"📞 *Telefono:* {phone}\n"
        f"🪙 *Coin richiesti:* {coins_requested}\n"
        f"💰 *Prezzo stimato:* €{price:.2f}\n\n"
        f"🆔 *ID Modulo:* #{form_id}\n\n"
        "📞 Il nostro team ti contatterà presto per completare l'acquisto!\n\n"
        "💡 *Nota:* Il prezzo finale potrebbe variare leggermente.",
        parse_mode='Markdown'
    )
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"💳 *Nuova Richiesta Acquisto*\n\n"
                f"🆔 *Form ID:* #{form_id}\n"
                f"👤 *Utente:* {user_id}\n"
                f"📋 *Nome:* {name}\n"
                f"📞 *Telefono:* {phone}\n"
                f"🪙 *Coin:* {coins_requested}\n"
                f"💰 *Prezzo:* €{price:.2f}\n"
                f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about purchase form: {e}")
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

async def handle_interaction_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interaction type selection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    action_type = query.data.split('_')[2]  # Extract action from callback_data
    
    # Store the selected action type
    context.user_data['interaction_type'] = action_type
    
    await query.edit_message_text(
        f"📋 *Richiesta {ACTION_NAMES.get(action_type, action_type)}*\n\n"
        f"Inserisci il link del tuo post Instagram:\n\n"
        f"Esempio: https://instagram.com/p/ABC123DEF456/\n\n"
        f"💡 *Assicurati che il link sia corretto!*",
        parse_mode='Markdown'
    )
    
    return WAITING_POST_LINK

async def handle_post_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle post link input"""
    link = update.message.text.strip()
    
    if not is_valid_instagram_link(link):
        await update.message.reply_text(
            "❌ *Link non valido!*\n\n"
            "Inserisci un link Instagram valido.\n\n"
            "Esempio: https://instagram.com/p/ABC123DEF456/",
            parse_mode='Markdown'
        )
        return WAITING_POST_LINK
    
    context.user_data['post_link'] = link
    action_type = context.user_data['interaction_type']
    cost = ACTION_COSTS[action_type]
    
    await update.message.reply_text(
        f"💰 *Costo per interazione:* {cost} Coin\n\n"
        f"Quante interazioni vuoi ricevere?\n\n"
        f"Inserisci un numero (es: 10, 50, 100):",
        parse_mode='Markdown'
    )
    
    return WAITING_QUANTITY

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity input"""
    try:
        quantity = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ *Numero non valido!*\n\n"
            "Inserisci un numero valido di interazioni."
        )
        return WAITING_QUANTITY
    
    if quantity <= 0:
        await update.message.reply_text(
            "❌ *Il numero deve essere positivo!*"
        )
        return WAITING_QUANTITY
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    action_type = context.user_data['interaction_type']
    cost_per_action = ACTION_COSTS[action_type]
    total_cost = quantity * cost_per_action
    
    if user['coin_balance'] < total_cost:
        await update.message.reply_text(
            f"❌ *Saldo insufficiente!*\n\n"
            f"💰 *Saldo attuale:* {user['coin_balance']} Coin\n"
            f"💳 *Costo totale:* {total_cost} Coin\n"
            f"🪙 *Mancano:* {total_cost - user['coin_balance']} Coin\n\n"
            "Usa il pulsante 'Acquista Coin' per comprarne altri!",
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Deduct coins and create interaction request
    db.update_user_balance(user_id, -total_cost)
    post_link = context.user_data['post_link']
    
    interaction_id = db.create_interaction_request(
        user_id, post_link, action_type, quantity, cost_per_action
    )
    
    await update.message.reply_text(
        f"✅ *Richiesta creata con successo!*\n\n"
        f"🆔 *ID Richiesta:* {interaction_id}\n"
        f"🎯 *Azione:* {ACTION_NAMES.get(action_type, action_type)}\n"
        f"📊 *Quantità:* {quantity}\n"
        f"💰 *Costo totale:* {total_cost} Coin\n"
        f"🔗 *Link:* {post_link}\n\n"
        f"🚀 *La tua richiesta è ora attiva!*\n"
        f"Gli altri utenti potranno completare le tue interazioni e guadagnare Coin.\n\n"
        f"💳 *Nuovo saldo:* {user['coin_balance'] - total_cost} Coin",
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action confirmation (for actions that don't require screenshots)"""
    query = update.callback_query
    user_id = query.from_user.id
    
    interaction_id = int(query.data.split('_')[2])
    
    # Get interaction details
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM interactions WHERE id = ?', (interaction_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        await query.edit_message_text(
            "❌ *Interazione non trovata!*",
            parse_mode='Markdown'
        )
        return
    
    cost_per_action = row[5]
    earnings = calculate_earnings(cost_per_action)
    
    if db.complete_interaction(user_id, interaction_id, earnings):
        await query.edit_message_text(
            f"🎉 *Interazione completata!*\n\n"
            f"💰 *Hai guadagnato:* {earnings} Coin\n\n"
            f"Grazie per aver partecipato! 🚀\n\n"
            f"Continua a completare interazioni per guadagnare più Coin!",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ *Hai già completato questa interazione!*",
            parse_mode='Markdown'
        )

async def handle_upload_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot upload request"""
    query = update.callback_query
    interaction_id = int(query.data.split('_')[2])
    
    context.user_data['pending_interaction_id'] = interaction_id
    
    await query.edit_message_text(
        "📸 *Invia il tuo screenshot*\n\n"
        "Invia una foto che dimostra di aver completato l'azione richiesta.\n\n"
        "💡 *Suggerimenti:*\n"
        "• Assicurati che lo screenshot sia chiaro\n"
        "• Mostra chiaramente l'azione completata\n"
        "• Non modificare o ritagliare l'immagine",
        parse_mode='Markdown'
    )
    
    return WAITING_SCREENSHOT

async def handle_screenshot_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot file upload"""
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Invia una foto come screenshot!*\n\n"
            "Riprova inviando un'immagine."
        )
        return WAITING_SCREENSHOT
    
    user_id = update.effective_user.id
    interaction_id = context.user_data.get('pending_interaction_id')
    
    if not interaction_id:
        await update.message.reply_text(
            "❌ *Errore: ID interazione non trovato.*\n\n"
            "Riprova dall'inizio."
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Get the largest photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    
    # Create screenshots directory if it doesn't exist
    os.makedirs('screenshots', exist_ok=True)
    
    # Generate unique filename
    screenshot_id = f"{user_id}_{interaction_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filename = f"screenshots/{screenshot_id}.jpg"
    
    # Download the file
    await file.download_to_drive(filename)
    
    # Store screenshot info in database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO screenshots (id, user_id, file_path, interaction_id)
        VALUES (?, ?, ?, ?)
    ''', (screenshot_id, user_id, filename, interaction_id))
    conn.commit()
    conn.close()
    
    # Get interaction details for earnings calculation
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT cost_per_action FROM interactions WHERE id = ?', (interaction_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        cost_per_action = row[0]
        earnings = calculate_earnings(cost_per_action)
        
        if db.complete_interaction(user_id, interaction_id, earnings, screenshot_id=screenshot_id):
            await update.message.reply_text(
                f"✅ *Screenshot ricevuto e interazione completata!*\n\n"
                f"📸 *ID Screenshot:* {screenshot_id}\n"
                f"💰 *Hai guadagnato:* {earnings} Coin\n\n"
                f"🔍 Il tuo screenshot verrà verificato dall'admin.\n\n"
                f"Grazie per aver partecipato! 🚀",
                parse_mode='Markdown'
            )
            
            # Notify admins about new screenshot
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"📸 *Nuovo Screenshot Ricevuto*\n\n"
                        f"👤 *Utente:* {user_id}\n"
                        f"🆔 *Interazione ID:* {interaction_id}\n"
                        f"📸 *Screenshot ID:* {screenshot_id}\n"
                        f"📁 *File:* {filename}\n"
                        f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id} about screenshot: {e}")
        else:
            await update.message.reply_text(
                "❌ *Hai già completato questa interazione!*"
            )
    else:
        await update.message.reply_text(
            "❌ *Errore: Interazione non trovata.*"
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button"""
    query = update.callback_query
    user_id = query.from_user.id
    
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id)
        user = db.get_user(user_id)
    
    welcome_text = (
        f"🏠 *Menu Principale* 🏠\n\n"
        f"💰 Saldo attuale: *{user['coin_balance']} Coin*\n\n"
        "Cosa vuoi fare?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Inizia Ora", callback_data="start_earning")],
        [InlineKeyboardButton("📈 Ricevi Interazioni", callback_data="receive_interactions")],
        [InlineKeyboardButton("💳 Acquista Coin", callback_data="buy_coins")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current conversation"""
    await update.message.reply_text(
        "❌ Operazione annullata.\n\n"
        "Usa /start per tornare al menu principale."
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("profilo", profile_command))
    application.add_handler(CommandHandler("stato_profilo", profile_status_command))
    application.add_handler(CommandHandler("bilancio", balance_command))
    application.add_handler(CommandHandler("ticket", ticket_command))
    application.add_handler(CommandHandler("classifica", rankings_command))
    
    # Admin commands
    application.add_handler(CommandHandler("admin_richiesta", admin_request_command))
    application.add_handler(CommandHandler("admin_gestisci", admin_manage_command))
    application.add_handler(CommandHandler("admin_coin", admin_coin_command))
    application.add_handler(CommandHandler("admin_campagna", admin_campaign_command))
    application.add_handler(CommandHandler("admin_verifica", admin_verify_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("admin_broadcast", admin_broadcast_command))
    
    # Admin broadcast confirmation handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_IDS), 
        handle_broadcast_confirmation
    ))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Purchase form conversation handler
    purchase_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_purchase_form, pattern="start_purchase_form")],
        states={
            WAITING_PURCHASE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_name_handler)],
            WAITING_PURCHASE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_phone_handler)],
            WAITING_PURCHASE_COINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_coins_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(purchase_conv_handler)
    
    # Interaction request conversation handler
    interaction_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_interaction_type_selection, pattern="interaction_type_.*")],
        states={
            WAITING_POST_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_post_link)],
            WAITING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(interaction_conv_handler)
    
    # Screenshot upload conversation handler
    screenshot_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_upload_screenshot, pattern="upload_screenshot_.*")],
        states={
            WAITING_SCREENSHOT: [MessageHandler(filters.PHOTO, handle_screenshot_upload)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(screenshot_conv_handler)
    
    # Schedule daily backup (run at 2 AM every day)
    job_queue = application.job_queue
    job_queue.run_daily(daily_backup, time=datetime.time(2, 0, 0))
    
    # Start the bot
    logger.info("Starting CrescitaDigitale Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()