# 🎲 Telegram Dice Roll Bot

A professional-grade Telegram bot that simulates dice rolls with proper error handling, logging, and graceful shutdown capabilities.

## ✨ Features

- 🎲 Roll a dice (1-6) with beautiful dice emojis
- 📝 Comprehensive logging system
- 🛡️ Error handling and graceful shutdown
- 🔒 Secure token management using environment variables
- 📚 Well-documented code with type hints

## 🚀 Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dice-bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root and add your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

## 🎮 Usage

1. **Start the bot**
   ```bash
   python dice_bot.py
   ```

2. **Available Commands**
   - `/start` - Start the bot and get welcome message
   - `/roll` - Roll a dice (1-6)
   - `/help` - Show help message

## 📝 Logging

The bot maintains detailed logs in `bot.log` file, including:
- User interactions
- Error messages
- System events
- Shutdown events

## 🔧 Error Handling

The bot includes comprehensive error handling:
- Graceful shutdown on system signals
- User-friendly error messages
- Detailed error logging
- Automatic recovery from common errors

## 🛡️ Security

- Bot token is stored in environment variables
- Input validation and sanitization
- Rate limiting (built into python-telegram-bot)
- Secure error handling

## 📚 Code Structure

```
dice_bot/
├── dice_bot.py      # Main bot code
├── requirements.txt # Dependencies
├── .env            # Environment variables
└── README.md       # Documentation
```

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 