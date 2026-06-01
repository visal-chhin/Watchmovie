import logging
import re
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------
# CONFIG
# ---------------------------
TOKEN = "8648355227:AAFk0H3rtjOuDdmqmt0XbQ19cGTbVhEpK80"

user_data = {}

logging.basicConfig(level=logging.INFO)

# ---------------------------
# USER INIT
# ---------------------------
def ensure_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "url": None,
            "post_id": None
        }

# ---------------------------
# GET POST ID
# ---------------------------
def get_post_id(url: str):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": url
        }

        r = requests.get(url, headers=headers, timeout=15)
        html = r.text

        # 👇 SAME AS JS: document.body.className.match(/postid-(\d+)/)
        match = re.search(r'postid-(\d+)', html)

        if match:
            return match.group(1)

        return None

    except Exception as e:
        logging.error(f"POST ID ERROR: {e}")
        return None
    
# ---------------------------
# GET PLAYER LINK (POSTMAN STYLE)
# ---------------------------
def get_player_link(post_id, nume=1, type_="movie"):
    url = "https://khdiamond.net/wp-admin/admin-ajax.php"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://khdiamond.net/",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    data = {
        "action": "player_ajax",
        "post_id": post_id,
        "nume": str(nume),
        "type": type_
    }

    try:
        r = requests.post(url, data=data, headers=headers, timeout=15)

        match = re.search(r'https:\\/\\/player\.khdiamond\.net[^"]+', r.text)

        if match:
            return match.group(0).replace("\\/", "/")

        return None

    except Exception as e:
        logging.error(f"PLAYER ERROR: {e}")
        return None

# ---------------------------
# NEXT EPISODE
# ---------------------------
def next_episode_url(url):
    match = re.search(r"(.*-)(\d+)x(\d+)/?$", url)
    if not match:
        return None

    base = match.group(1)
    season = int(match.group(2))
    episode = int(match.group(3)) + 1

    return f"{base}{season}x{episode}/"

# ---------------------------
# SEND MENU
# ---------------------------
async def send_episode(chat_id, context, url, post_id):
    ensure_user(chat_id)

    user_data[chat_id]["url"] = url
    user_data[chat_id]["post_id"] = post_id

    keyboard = [
        [InlineKeyboardButton("🎬 Movie", callback_data="movie")],
        [InlineKeyboardButton("📺 Episode", callback_data="episode")],
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Ready:\n{url}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------------------
# MESSAGE HANDLER
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.effective_chat.id

    if "khdiamond.net" not in url:
        await update.message.reply_text("❌ Only khdiamond links allowed")
        return

    post_id = get_post_id(url)

    if not post_id:
        await update.message.reply_text("❌ Cannot get post ID")
        return

    await send_episode(chat_id, context, url, post_id)

# ---------------------------
# BUTTON HANDLER
# ---------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    ensure_user(chat_id)

    data = query.data
    url = user_data[chat_id]["url"]
    post_id = user_data[chat_id]["post_id"]

    if not post_id:
        await query.message.reply_text("❌ Missing post ID")
        return

    # MOVIE
    if data == "movie":
        link = get_player_link(post_id, 1, "movie")

        if not link:
            await query.message.reply_text("❌ Movie not found")
            return

        await query.message.reply_text(f"🎬 MOVIE:\n{link}")

    # EPISODE
    elif data == "episode":
        link = get_player_link(post_id, 1, "episode")

        if not link:
            await query.message.reply_text("❌ Episode not found")
            return

        await query.message.reply_text(f"📺 EPISODE:\n{link}")

# ---------------------------
# BOT SETUP
# ---------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    print("Bot running...")
    app.run_polling()