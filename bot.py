import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import asyncio

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("7548833145:AAFCtS6XTxfS7G2qe38gSBO12HnKbBFuibE")
GROQ_API_KEY = os.environ.get("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")
BOT_URL = os.environ.get("https://novi-bot.onrender.com")  # e.g., https://your-app.onrender.com

print("TELEGRAM_TOKEN =", os.environ.get("TELEGRAM_TOKEN"))
print("GROQ_API_KEY =", os.environ.get("GROQ_API_KEY"))
print("BOT_URL =", os.environ.get("BOT_URL"))


# Validate environment variables
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is missing!")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is missing!")
if not BOT_URL:
    raise ValueError("RENDER_URL environment variable is missing!")

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
    await update.message.reply_text("Hello! Send me text or an image, and I'll answer or describe it.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Thinking... 🤖")
    try:
        answer = call_groq_api(update.message.text)
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = f"temp_{photo.file_id}.jpg"
    await file.download_to_drive(file_path)
    await update.message.reply_text("Analyzing image... 🖼️")
    try:
        description = call_groq_image(file_path)
        await update.message.reply_text(description)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# --- FLASK APP ---
flask_app = Flask(__name__)
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Receive updates from Telegram via webhook"""
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put(update)
    return "OK"

@flask_app.route("/")
def index():
    return "Bot is running on Render!"

# --- SET WEBHOOK ---
async def set_webhook():
    webhook_url = f"{BOT_URL}/{TELEGRAM_TOKEN}"
    await app.bot.set_webhook(webhook_url)
    print(f"Webhook set to: {webhook_url}")

# --- RUN ---
if __name__ == "__main__":
    # First, set the webhook
    asyncio.run(set_webhook())
    # Start the bot and Flask server
    app.start()
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

