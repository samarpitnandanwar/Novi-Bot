import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BOT_URL = os.environ.get("BOT_URL")  # e.g., https://your-app.onrender.com

# Validate environment variables
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is missing!")
if not BOT_URL:
    raise ValueError("BOT_URL environment variable is missing!")

# --- HELPERS ---
def call_groq_api(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def call_groq_image(file_path: str) -> str:
    url = "https://api.groq.com/v1/vision/describe"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()
    return response.json().get("description", "Could not describe image.")

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me text or an image, and I'll respond.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Temporary handler to test webhook & bot."""
    await update.message.reply_text(f"✅ Received: {update.message.text}")

# --- FLASK APP ---
flask_app = Flask(__name__)

# Initialize Telegram bot app
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))  # Echo test

# --- Async loop for webhook updates ---
main_loop = asyncio.get_event_loop()

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    # Schedule update processing in the bot's event loop
    asyncio.run_coroutine_threadsafe(app.process_update(update), main_loop)
    return "OK"

@flask_app.route("/")
def index():
    return "🤖 Bot is running on Render!"

# --- SET WEBHOOK ---
async def set_webhook():
    webhook_url = f"{BOT_URL}/{TELEGRAM_TOKEN}"
    await app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

# --- RUN ---
if __name__ == "__main__":
    # 1️⃣ Initialize and start Telegram bot
    main_loop.run_until_complete(app.initialize())
    main_loop.run_until_complete(set_webhook())
    main_loop.run_until_complete(app.start())
    print("🤖 Bot initialized and running!")

    # 2️⃣ Start Flask server
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
