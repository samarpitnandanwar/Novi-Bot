import os
import requests
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BOT_URL = os.environ.get("BOT_URL")  # e.g., https://your-app.onrender.com

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is missing!")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is missing!")
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

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me text or an image, and I'll answer or describe it.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Thinking... 🤖")
    try:
        answer = call_groq_api(update.message.text)
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# --- FLASK APP ---
flask_app = Flask(__name__)
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Add handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    # enqueue the update
    asyncio.get_event_loop().create_task(app.process_update(update))
    return "OK"

@flask_app.route("/")
def index():
    return "🤖 Bot is running on Render!"

# --- STARTUP ---
async def set_webhook():
    webhook_url = f"{BOT_URL}/{TELEGRAM_TOKEN}"
    await app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    # Run Flask (blocking)
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
