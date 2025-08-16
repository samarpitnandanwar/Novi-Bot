import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BOT_URL = os.environ.get("BOT_URL")  # e.g., https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

if not TELEGRAM_TOKEN or not GROQ_API_KEY or not BOT_URL:
    raise ValueError("TELEGRAM_TOKEN, GROQ_API_KEY, BOT_URL must be set as environment variables.")

# --- HELPERS ---
def call_groq_api(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]}
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def call_groq_image(file_path: str) -> str:
    url = "https://api.groq.com/v1/vision/describe"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(url, headers=headers, files=files)
    resp.raise_for_status()
    return resp.json().get("description", "Could not describe image.")

# --- HANDLERS ---
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

# --- APPLICATION ---
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))

# --- AIOHTTP SERVER ---
async def handle_webhook(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

async def init_app():
    webhook_url = f"{BOT_URL}/{TELEGRAM_TOKEN}"
    await app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")
    
    aio_app = web.Application()
    aio_app.router.add_post(f"/{TELEGRAM_TOKEN}", handle_webhook)
    return aio_app

if __name__ == "__main__":
    aio_app = asyncio.run(init_app())
    web.run_app(aio_app, host="0.0.0.0", port=PORT)
