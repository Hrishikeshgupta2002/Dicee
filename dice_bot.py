#!/usr/bin/env python3
"""
Telegram Dice Roll Bot
A professional-grade Telegram bot that simulates dice rolls.
"""

import os
import sys
import logging
import signal
import random
import asyncio
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackContext,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
    sys.exit(1)

# Get deployment mode from environment variable
DEPLOYMENT_MODE = os.getenv('DEPLOYMENT_MODE', 'polling')  # Default to polling
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # For webhook mode
PORT = int(os.getenv('PORT', 8443))  # Default port for webhook

class DiceBot:
    """Main bot class with all the functionality."""
    
    def __init__(self):
        """Initialize the bot with application builder."""
        self.application = ApplicationBuilder().token(TOKEN).build()
        self._setup_handlers()
        self._setup_error_handler()
        
    def _setup_handlers(self) -> None:
        """Set up all command handlers."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("roll", self.roll))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
    def _setup_error_handler(self) -> None:
        """Set up error handler for the application."""
        self.application.add_error_handler(self.error_handler)
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        user = update.effective_user
        welcome_message = (
            f"👋 Welcome {user.first_name}!\n\n"
            "I'm your friendly dice rolling bot. Here's what I can do:\n"
            "🎲 /roll - Roll a dice (1-6)\n"
            "❓ /help - Show this help message"
        )
        await update.message.reply_text(welcome_message)
        logger.info(f"User {user.id} started the bot")
        
    async def roll(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /roll command."""
        dice_number = random.randint(1, 6)
        dice_emojis = {
            1: "⚀",
            2: "⚁",
            3: "⚂",
            4: "⚃",
            5: "⚄",
            6: "⚅"
        }
        response = f"🎲 You rolled a {dice_number} {dice_emojis[dice_number]}!"
        await update.message.reply_text(response)
        logger.info(f"User {update.effective_user.id} rolled a {dice_number}")
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        help_text = (
            "🎲 *Dice Roll Bot Commands*\n\n"
            "/start - Start the bot\n"
            "/roll - Roll a dice (1-6)\n"
            "/help - Show this help message\n\n"
            "Made with ❤️ by a professional developer"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def error_handler(self, update: Optional[Update], context: CallbackContext) -> None:
        """Handle errors in the bot."""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Sorry, something went wrong. Please try again later."
            )
            
    async def cleanup(self) -> None:
        """Clean up before shutdown."""
        try:
            if DEPLOYMENT_MODE == 'webhook':
                await self.application.bot.delete_webhook()
            await self.application.stop()
            await self.application.shutdown()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    async def setup_webhook(self) -> None:
        """Set up webhook for production deployment."""
        if not WEBHOOK_URL:
            logger.error("WEBHOOK_URL not set for webhook mode!")
            sys.exit(1)
            
        await self.application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
            
    def run(self) -> None:
        """Run the bot with graceful shutdown handling."""
        async def shutdown(signum, frame):
            """Handle shutdown signals gracefully."""
            logger.info("Received shutdown signal. Cleaning up...")
            await self.cleanup()
            sys.exit(0)
            
        # Register signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, None))
            )
        
        try:
            if DEPLOYMENT_MODE == 'webhook':
                # Webhook mode for production
                logger.info(f"Starting bot in webhook mode on port {PORT}")
                asyncio.run(self.setup_webhook())
                self.application.run_webhook(
                    listen='0.0.0.0',
                    port=PORT,
                    webhook_url=WEBHOOK_URL
                )
            else:
                # Polling mode for development
                logger.info("Starting bot in polling mode...")
                self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.critical(f"Critical error: {e}")
            asyncio.run(self.cleanup())
            sys.exit(1)

def main() -> None:
    """Main entry point of the application."""
    try:
        bot = DiceBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 