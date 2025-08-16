import os
import requests
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
TELEGRAM_TOKEN = "7548833145:AAFCtS6XTxfS7G2qe38gSBO12HnKbBFuibE"
GROQ_API_KEY = "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"

# --- HELPERS ---

def call_groq_api(prompt: str) -> str:
    """Call Groq API for text completion."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]

def call_groq_image(file_path: str) -> str:
    """Call Groq API to describe an image."""
    url = "https://api.groq.com/v1/vision/describe"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()
    result = response.json()
    # Return description or detected text
    return result.get("description", "Could not describe image.")

# --- TELEGRAM HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me text or an image, and I'll answer or describe it.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("Thinking... 🤖")
    try:
        answer = call_groq_api(user_text)
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

# --- MAIN ---

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))

print("Bot is running...")
app.run_polling()
