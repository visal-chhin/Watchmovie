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
import logging

# ---------------------------
# CONFIG
# ---------------------------
TOKEN = "8648355227:AAFk0H3rtjOuDdmqmt0XbQ19cGTbVhEpK80"

user_data = {}

logging.basicConfig(level=logging.INFO)

# ---------------------------
# BOT APP
# ---------------------------
app = ApplicationBuilder().token(TOKEN).build()

# ---------------------------
# HELPERS
# ---------------------------
def ensure_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "url": None,
            "post_id": None,
            "type": None
        }


def get_post_id_from_url(url):
    if not url:
        return None

    match = re.search(r"(?:postid|post-id|data-postid)=(\d+)", url)
    if match:
        return match.group(1)

    try:
        html = requests.get(url, timeout=10).text
    except requests.RequestException as e:
        logging.error(f"POST ID REQUEST ERROR: {e}")
        return None

    match = re.search(r'postid-(\d+)|post-id-(\d+)|data-postid="(\d+)"', html)
    if match:
        return next(group for group in match.groups() if group)

    logging.error("POST ID ERROR: could not extract post ID")
    return None


def get_player_link(post_id, nume=1, type_="movie"):
    ajax_url = "https://khdiamond.net/wp-admin/admin-ajax.php"
    data = {
        "action": "player_ajax",
        "post_id": post_id,
        "nume": nume,
        "type": type_
    }

    try:
        r = requests.post(ajax_url, data=data, timeout=10)
        r.raise_for_status()

        match = re.search(r'https:\/\/player\.khdiamond\.net[^"]+', r.text)
        if match:
            return match.group(0).replace("\/", "/")

    except requests.RequestException as e:
        logging.error(f"PLAYER ERROR: {e}")

    return None


def next_episode_url(url):
    if not url:
        return None

    match = re.search(r"(.*-)(\d+)x(\d+)/?$", url)
    if not match:
        return None

    base, season, episode = match.group(1), int(match.group(2)), int(match.group(3))
    episode += 1
    return f"{base}{season}x{episode}/"


# ---------------------------
# SEND MOVIE
# ---------------------------
async def send_movie(chat_id, context, post_id):
    link = get_player_link(post_id, 1, "movie")
    if not link:
        await context.bot.send_message(chat_id, "❌ Movie not found")
        return

    user_data[chat_id]["post_id"] = post_id
    user_data[chat_id]["type"] = "movie"

    keyboard = [
        [InlineKeyboardButton("🔁 Refresh Movie", callback_data="refresh_movie")]
    ]

    await context.bot.send_message(
        chat_id,
        f"🎬 MOVIE:\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------------------
# SEND EPISODE
# ---------------------------
async def send_episode(chat_id, context, url):
    post_id = get_post_id_from_url(url)
    if not post_id:
        await context.bot.send_message(chat_id, "❌ Could not extract episode post ID")
        return

    link = get_player_link(post_id, 1, "episode")
    if not link:
        await context.bot.send_message(chat_id, "❌ Episode not found")
        return

    user_data[chat_id]["url"] = url
    user_data[chat_id]["post_id"] = post_id
    user_data[chat_id]["type"] = "episode"

    keyboard = [
        [InlineKeyboardButton("🔁 Refresh", callback_data="refresh")],
        [InlineKeyboardButton("⏭️ Next Episode", callback_data="next_ep")]
    ]

    await context.bot.send_message(
        chat_id,
        f"📺 EPISODE:\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------------------
# HANDLE MESSAGE
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_user(chat_id)

    text = update.message.text.strip()
    if "khdiamond.net" not in text:
        await update.message.reply_text("❌ Only khdiamond links allowed")
        return

    post_id = get_post_id_from_url(text)
    if not post_id:
        await update.message.reply_text("❌ Could not extract post ID from the link")
        return

    if "episode" in text or re.search(r"\d+x\d+", text):
        await send_episode(chat_id, context, text)
    else:
        await send_movie(chat_id, context, post_id)


# ---------------------------
# BUTTON HANDLER
# ---------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    ensure_user(chat_id)
    data = query.data

    post_id = user_data[chat_id].get("post_id")
    url = user_data[chat_id].get("url")

    if data == "movie":
        await send_movie(chat_id, context, post_id)
    elif data == "refresh_movie":
        await send_movie(chat_id, context, post_id)
    elif data == "next_ep":
        new_url = next_episode_url(url)
        if not new_url:
            await query.message.reply_text("❌ Cannot determine next episode URL")
            return
        await send_episode(chat_id, context, new_url)
    elif data == "refresh":
        await send_episode(chat_id, context, url)
    else:
        await query.message.reply_text("❌ Unknown action")


# ---------------------------
# REGISTER HANDLERS
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

app.add_handler(
    CallbackQueryHandler(button_handler)
)


# ---------------------------
# RUN BOT
if __name__ == "__main__":
    print("Bot running...")
    app.run_polling()
