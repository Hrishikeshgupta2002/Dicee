#!/usr/bin/env python3
import os
import sys
import logging
import random
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
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
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
        self.app.add_handler(CommandHandler("toss", self.toss))
        self.app.add_handler(CommandHandler("show", self.show_cards))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("getid", self.get_chat_id))
        self.app.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Welcome to Dice Roll Bot!\n"
            "Use /roll, /toss, or /show (admins only in groups).\n"
            "Use /help for all commands."
        )

    async def roll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_allowed(update, context, "roll"):
            return
        number = random.randint(1, 6)
        await update.message.reply_text(str(number))

    async def toss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_allowed(update, context, "toss"):
            return
        result = random.choice(["Heads", "Tails"])
        await update.message.reply_text(result)

    async def show_cards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_allowed(update, context, "show"):
            return

        suits = ["♠", "♥", "♦", "♣"]
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [f"{v}{s}" for v in values for s in suits]
        random.shuffle(deck)
        hand = random.sample(deck, 3)

        for card in hand:
            await update.message.reply_text(card)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/start - Start the bot\n"
            "/roll - Roll a dice (admin-only in groups)\n"
            "/toss - Toss a coin (admin-only in groups)\n"
            "/show - Show 3 cards (admin-only in groups)\n"
            "/status - Bot uptime and mode\n"
            "/getid - Show chat ID (admin-only in groups)"
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uptime = datetime.now() - self.start_time
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        await update.message.reply_text(
            f"Bot is running.\n"
            f"Mode: {DEPLOYMENT_MODE}\n"
            f"Uptime: {int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        )

    async def get_chat_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        user = update.effective_user

        if chat.type == "private":
            await update.message.reply_text(f"{chat.id}")
            return

        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            if member.status not in ("administrator", "creator"):
                await update.message.reply_text("Only group admins can use /getid.")
                return
        except Exception as e:
            logger.error(f"Failed to fetch chat member in /getid: {e}")
            await update.message.reply_text("Could not verify admin rights.")
            return

        await update.message.reply_text(f"{chat.id}")

    async def _is_allowed(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cmd: str) -> bool:
        chat = update.effective_chat
        user = update.effective_user

        if chat.type == "private":
            return True  # always allowed in private chats

        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            if member.status in ("administrator", "creator"):
                return True
            await update.message.reply_text(f"Only group admins can use /{cmd}.")
            return False
        except Exception as e:
            logger.error(f"Admin check failed in /{cmd}: {e}")
            await update.message.reply_text("Could not verify admin rights.")
            return False

    async def error_handler(self, update: Optional[Update], context: CallbackContext):
        logger.error(f"Error: {context.error}")
        if update and update.effective_message:
            await update.message.reply_text("Something went wrong.")

    def run_webhook(self):
        if not WEBHOOK_URL:
            logger.error("WEBHOOK_URL not set!")
            sys.exit(1)

        logger.info(f"Running in webhook mode at {WEBHOOK_URL}")
        self.app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL
        )

    def run(self):
        if DEPLOYMENT_MODE == "webhook":
            self.run_webhook()
        else:
            logger.info("Running in polling mode")
            self.app.run_polling()

if __name__ == "__main__":
    DiceBot().run()
