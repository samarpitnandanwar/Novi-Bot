import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# ======================
# Logging
# ======================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ======================
# Config
# ======================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
BOT_URL = os.environ.get("BOT_URL")  # e.g. https://mybot.onrender.com

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN environment variable is missing!")
if not BOT_URL:
    raise ValueError("❌ BOT_URL environment variable is missing!")

# ======================
# Flask app
# ======================
flask_app = Flask(__name__)

# ======================
# Telegram Application
# ======================
app = Application.builder().token(TELEGRAM_TOKEN).build()

# Groq API call (dummy example, replace with real API call)
def call_groq_api(text: str) -> str:
    try:
        logger.info(f"🔮 Sending to Groq API: {text}")
        # Replace this with your actual Groq API request
        response = {"answer": f"Echo: {text}"}
        return response["answer"]
    except Exception as e:
        logger.exception("❌ Groq API call failed")
        return f"Error contacting Groq API: {e}"

# ======================
# Handlers
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"🚀 /start command from {update.effective_user.id}")
    await update.message.reply_text("Hello! I am alive 🤖")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_msg = update.message.text
        logger.info(f"💬 User said: {user_msg}")

        await update.message.reply_text("Thinking... 🤖")

        answer = call_groq_api(user_msg)
        logger.info(f"🤖 Bot reply: {answer}")

        await update.message.reply_text(answer)

    except Exception as e:
        logger.exception("❌ Error in handle_text")
        await update.message.reply_text(f"Error: {e}")

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# ======================
# Webhook Route
# ======================
@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    logger.info(f"📩 Incoming update: {update.to_dict()}")
    asyncio.run_coroutine_threadsafe(app.process_update(update), main_loop)
    return "OK"

@flask_app.route("/", methods=["GET"])
def index():
    return "🤖 Bot is running!"

# ======================
# Startup
# ======================
async def set_webhook():
    webhook_url = f"{BOT_URL}/{TELEGRAM_TOKEN}"
    await app.bot.delete_webhook()  # clear old webhook
    await app.bot.set_webhook(webhook_url)
    me = await app.bot.get_me()
    logger.info(f"✅ Webhook set: {webhook_url} for bot {me.username}")

if __name__ == "__main__":
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    main_loop.create_task(set_webhook())

    import threading
    def run_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    threading.Thread(target=run_loop, args=(main_loop,), daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
