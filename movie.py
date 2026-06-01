from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

import requests
import re

TOKEN = "8648355227:AAFk0H3rtjOuDdmqmt0XbQ19cGTbVhEpK80"
GO_API = "http://localhost:8080/get"

user_data = {}

def get_post_id(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        html = requests.get(url, headers=headers, timeout=10).text

        # try multiple patterns
        patterns = [
            r'postid-(\d+)',
            r'data-postid="(\d+)"',
            r'"post_id":(\d+)',
            r'post_id=(\d+)'
        ]

        for p in patterns:
            match = re.search(p, html)
            if match:
                return match.group(1)

        return None

    except Exception as e:
        print("POST ID ERROR:", e)
        return None


def get_player_from_go(post_id):
    try:
        r = requests.get(GO_API, params={"post": post_id}, timeout=10)
        data = r.json()
        return data.get("link")
    except:
        return None


app = ApplicationBuilder().token(TOKEN).build()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = update.message.text
    chat_id = update.effective_chat.id

    if not url.startswith("https://khdiamond.net/"):
        await update.message.reply_text("❌ Only khdiamond links")
        return

    post_id = get_post_id(url)

    if not post_id:
        await update.message.reply_text("❌ Cannot get post ID")
        return

    link = get_player_from_go(post_id)

    if not link:
        await update.message.reply_text("❌ Video not found")
        return

    user_data[chat_id] = {"url": url, "post_id": post_id}

    keyboard = [
        [InlineKeyboardButton("🔁 Refresh", callback_data="refresh")]
    ]

    await update.message.reply_text(
        f"🎬 LINK READY:\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    post_id = user_data.get(chat_id, {}).get("post_id")

    if not post_id:
        await query.message.reply_text("Send link first")
        return

    link = get_player_from_go(post_id)

    await query.message.reply_text(f"🔁 NEW LINK:\n{link}")


app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("Bot running...")
app.run_polling()