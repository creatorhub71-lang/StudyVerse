import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import secrets
import sqlite3
import os

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tokens
                 (token TEXT PRIMARY KEY, 
                  user_id INTEGER,
                  username TEXT,
                  created_at TIMESTAMP, 
                  expires_at TIMESTAMP)''')
    conn.commit()
    conn.close()

# 10-digit numeric token generate karna
def generate_token():
    digits = '0123456789'
    return ''.join(secrets.choice(digits) for _ in range(10))

# Token database mein save karna
def store_token(user_id, username, token):
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expires_at = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("INSERT INTO tokens VALUES (?, ?, ?, ?, ?)", 
              (token, user_id, username, created_at, expires_at))
    conn.commit()
    conn.close()
    return expires_at

# Check karna agar user ke paas pehle se active token hai
def get_existing_token(user_id):
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT token, expires_at FROM tokens WHERE user_id = ? AND expires_at > ?", 
              (user_id, current_time))
    token_data = c.fetchone()
    conn.close()
    return token_data

# Button callbacks handle karna
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = query.from_user.id
    
    if callback_data.startswith("copy_"):
        token = callback_data.replace("copy_", "")
        # Copy to clipboard functionality (Telegram doesn't support direct clipboard access)
        await query.edit_message_text(
            text=f"📋 Token copied to clipboard!\n\n"
                 f"🔑 Your Token: `{token}`\n\n"
                 f"Now you can use it to login to our website.",
            parse_mode="Markdown"
        )
    
    elif callback_data == "website":
        # Website button pressed
        website_url = "https://yourwebsite.com/login"  # Yahan apni website ka URL dalo
        await query.edit_message_text(
            text=f"🌐 Please visit our website to login:\n\n"
                 f"{website_url}\n\n"
                 f"Use your token to access your account."
        )
    
    elif callback_data == "new_token":
        # New token request
        existing_token = get_existing_token(user_id)
        
        if existing_token:
            token, expires_at = existing_token
            keyboard = [
                [InlineKeyboardButton("📋 Copy Token", callback_data=f"copy_{token}")],
                [InlineKeyboardButton("🌐 Visit Website", callback_data="website")],
                [InlineKeyboardButton("🔄 Generate New Token", callback_data="new_token")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"🔄 You already have an active token!\n\n"
                     f"🔑 Token: `{token}`\n"
                     f"⏰ Expiry: {expires_at}\n\n"
                     f"Use this token to login to our website.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            # Naya token generate karo
            token = generate_token()
            expires_at = store_token(user_id, query.from_user.username or query.from_user.first_name, token)
            
            keyboard = [
                [InlineKeyboardButton("📋 Copy Token", callback_data=f"copy_{token}")],
                [InlineKeyboardButton("🌐 Visit Website", callback_data="website")],
                [InlineKeyboardButton("🔄 Generate New Token", callback_data="new_token")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"✅ Your login token has been generated!\n\n"
                     f"🔑 Token: `{token}`\n"
                     f"⏰ Valid until: {expires_at}\n\n"
                     f"This token is valid for 24 hours.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

# /start command handle karna
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s started the bot.", user.first_name)
    
    # Check if user already has a valid token
    existing_token = get_existing_token(user.id)
    
    if existing_token:
        token, expires_at = existing_token
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Token", callback_data=f"copy_{token}")],
            [InlineKeyboardButton("🌐 Visit Website", callback_data="website")],
            [InlineKeyboardButton("🔄 Generate New Token", callback_data="new_token")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔄 You already have an active token!\n\n"
            f"🔑 Token: `{token}`\n"
            f"⏰ Expiry: {expires_at}\n\n"
            f"Use this token to login to our website.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Naya token generate karo
        token = generate_token()
        expires_at = store_token(user.id, user.username or user.first_name, token)
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Token", callback_data=f"copy_{token}")],
            [InlineKeyboardButton("🌐 Visit Website", callback_data="website")],
            [InlineKeyboardButton("🔄 Generate New Token", callback_data="new_token")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Your login token has been generated!\n\n"
            f"🔑 Token: `{token}`\n"
            f"⏰ Valid until: {expires_at}\n\n"
            f"This token is valid for 24 hours.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# Error handle karna
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # User ko error message bhejna
    if update and update.message:
        await update.message.reply_text(
            "❌ An error occurred. Please try again later."
        )

def main():
    # Database initialize karo
    init_db()
    
    # Bot token yahan dalo (BotFather se mila hua token)
    bot_token = "8473828326:AAEmK8uCLVTLHRolARQYvoA0Rm0NsAaKOO8"
    
    if not bot_token:
        print("Error: Bot token not set!")
        print("Please add your bot token in the code")
        return
    
    # Application banayo
    application = Application.builder().token(bot_token).build()
    
    # Handlers add karo
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler add karo
    application.add_error_handler(error_handler)
    
    # Bot start karo
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()