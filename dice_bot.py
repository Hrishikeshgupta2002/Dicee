#!/usr/bin/env python3
import os
import sys
import logging
import random
import asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "webhook")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()  # 🛠️ fixed here
PORT = int(os.getenv("PORT", 10000))

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DiceBot:
    def __init__(self):
        if not TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            sys.exit(1)
        self.start_time = datetime.now()
        self.app: Application = ApplicationBuilder().token(TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("roll", self.roll))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🎲 Welcome to Dice Roll Bot!\n\n"
            "Use /roll to roll a dice.\n"
            "Use /help for help.\n"
            "Use /status to check bot status."
        )

    async def roll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        number = random.randint(1, 6)
        dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        await update.message.reply_text(f"You rolled a {number} {dice_emojis[number]}!")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🆘 Commands:\n"
            "/start - Start the bot\n"
            "/roll - Roll a dice\n"
            "/help - Show help\n"
            "/status - Show bot status"
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uptime = datetime.now() - self.start_time
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        await update.message.reply_text(
            f"🤖 Bot is running\n"
            f"Mode: {DEPLOYMENT_MODE}\n"
            f"Uptime: {int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        )

    async def error_handler(self, update: Optional[Update], context: CallbackContext):
        logger.error(f"Error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("⚠️ Something went wrong.")

    async def run_webhook(self):
        if not WEBHOOK_URL:
            logger.error("WEBHOOK_URL not set!")
            sys.exit(1)

        # Debug
        print(f"DEBUG: WEBHOOK_URL = '{WEBHOOK_URL}'")
        print(f"DEBUG length = {len(WEBHOOK_URL)}")

        logger.info(f"Running in webhook mode at {WEBHOOK_URL}")
        await self.app.bot.set_webhook(WEBHOOK_URL)

        # Start the built-in webhook server (correct for PTB 20.8)
        self.app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL
        )

    def run(self):
        if DEPLOYMENT_MODE == "webhook":
            asyncio.run(self.run_webhook())
        else:
            logger.info("Running in polling mode")
            self.app.run_polling()

if __name__ == "__main__":
    DiceBot().run()
