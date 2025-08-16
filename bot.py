import os
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BOT_URL = os.environ.get("BOT_URL")  # e.g., https://your-app.onrender.com

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0, use_context=True)

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

# --- HANDLERS ---
def start(update, context):
    update.message.reply_text("Hello! Send me text or an image, and I'll answer or describe it.")

def handle_text(update, context):
    update.message.reply_text("Thinking... 🤖")
    try:
        answer = call_groq_api(update.message.text)
        update.message.reply_text(answer)
    except Exception as e:
        update.message.reply_text(f"Error: {e}")

def handle_image(update, context):
    photo = update.message.photo[-1]
    file = bot.get_file(photo.file_id)
    file_path = f"temp_{photo.file_id}.jpg"
    file.download(file_path)
    update.message.reply_text("Analyzing image... 🖼️")
    try:
        desc = call_groq_image(file_path)
        update.message.reply_text(desc)
    except Exception as e:
        update.message.reply_text(f"Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# --- REGISTER HANDLERS ---
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_image))

# --- FLASK APP ---
app = Flask(__name__)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "🤖 Bot is running on Render!"

if __name__ == "__main__":
    # Set webhook
    webhook_url = f"{BOT_URL}/{TELEGRAM_TOKEN}"
    bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to {webhook_url}")

    # Start Flask server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
