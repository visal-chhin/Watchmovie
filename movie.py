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
# SAFE USER INIT
# ---------------------------
def ensure_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "url": None,
            "post_id": None,
            "type": None
        }

# ---------------------------
# GET POST ID
# ---------------------------
def get_post_id(url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9"
        }

        r = requests.get(url, headers=headers, timeout=15)
        html = r.text

        # 1. Try normal patterns
        patterns = [
            r'postid-(\d+)',
            r'post-id-(\d+)',
            r'data-postid=["\'](\d+)["\']',
            r'"postid":\s*"(\d+)"',
            r'"postId":\s*"(\d+)"',
            r'"id":(\d+),',
        ]

        for p in patterns:
            match = re.search(p, html, re.IGNORECASE)
            if match:
                return match.group(1)

        # 2. NEW FIX: WordPress fallback (very important)
        wp_match = re.search(r'wp-json.*?posts/(\d+)', html)
        if wp_match:
            return wp_match.group(1)

        # 3. DEBUG (IMPORTANT)
        print("❌ POST ID NOT FOUND")
        print("URL:", url)
        print(html[:3000])  # show page preview

        return None

    except Exception as e:
        logging.error(f"POST ID ERROR: {e}")
        return None

# ---------------------------
# GET PLAYER LINK
# ---------------------------
def get_player_link(post_id, nume=1, type_="movie"):

    ajax_url = "https://khdiamond.net/wp-admin/admin-ajax.php"

    data = {
        "action": "doo_player_ajax",
        "post": post_id,
        "nume": str(nume),
        "type": type_
    }

    try:
        r = requests.post(ajax_url, data=data, timeout=10)

        match = re.search(
            r'https:\\/\\/player\.khdiamond\.net[^"]+',
            r.text
        )

        if match:
            return match.group(0).replace("\\/", "/")

        return None

    except Exception as e:
        logging.error(f"PLAYER ERROR: {e}")
        return None

# ---------------------------
# NEXT EPISODE URL
# ---------------------------
def next_episode_url(url):

    match = re.search(r"(.*-)(\d+)x(\d+)/?$", url)

    if not match:
        return None

    base = match.group(1)
    season = match.group(2)
    episode = int(match.group(3)) + 1

    return f"{base}{season}x{episode}/"

# ---------------------------
# SEND MOVIE
# ---------------------------
async def send_movie(chat_id, context, post_id, url=None):

    link = get_player_link(post_id, 1, "movie")

    if not link:
        await context.bot.send_message(chat_id, "❌ Movie not found")
        return

    ensure_user(chat_id)

    # save like episode style
    user_data[chat_id]["url"] = url
    user_data[chat_id]["post_id"] = post_id
    user_data[chat_id]["type"] = "movie"

    keyboard = [
        [InlineKeyboardButton("🔁 Refresh", callback_data="refresh_movie")]
    ]

    await context.bot.send_message(
        chat_id,
        f"📺 MOVIE:\n{url}\n\n🎥 WATCH:\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
# ---------------------------
# SEND EPISODE
# ---------------------------
async def send_episode(chat_id, context, url, post_id):

    ensure_user(chat_id)

    link = get_player_link(post_id, 1, "tv")

    if not link:
        await context.bot.send_message(chat_id, "❌ Episode not found")
        return

    # SAVE DATA
    user_data[chat_id]["url"] = url
    user_data[chat_id]["post_id"] = post_id
    user_data[chat_id]["type"] = "episode"

    keyboard = [
        [InlineKeyboardButton("🔁 Refresh", callback_data="refresh")],
        [InlineKeyboardButton("➡ Next Ep", callback_data="next_ep")]
    ]

    await context.bot.send_message(
        chat_id,
        f"📺 EPISODE:\n{url}\n\n🎥 WATCH:\n{link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------------------
# HANDLE MESSAGE
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if text.startswith("https://khdiamond.net/"):

        post_id = get_post_id(text)

        if not post_id:
            await update.message.reply_text("❌ Cannot get post ID")
            return

        ensure_user(chat_id)

        user_data[chat_id]["post_id"] = post_id
        user_data[chat_id]["url"] = text

        keyboard = [
            [
                InlineKeyboardButton("🎬 Movie", callback_data="movie"),
                InlineKeyboardButton("📺 Episode", callback_data="episode")
            ]
        ]

        await update.message.reply_text(
            "Choose type:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        await update.message.reply_text(
            "❌ Only khdiamond links allowed"
        )

# ---------------------------
# BUTTON HANDLER
# ---------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data

    ensure_user(chat_id)

    post_id = user_data[chat_id]["post_id"]
    url = user_data[chat_id]["url"]

    if not post_id or not url:
        await query.message.reply_text("❌ Send link first")
        return

    # ---------------- MOVIE ----------------
    if data == "movie":

        user_data[chat_id]["type"] = "movie"

        await send_movie(chat_id, context, post_id,url)

    # ---------------- REFRESH MOVIE ----------------
    elif data == "refresh_movie":
        await send_movie(chat_id, context, post_id, url)

    # ---------------- EPISODE ----------------
    elif data == "episode":

        await send_episode(chat_id, context, url, post_id)

    # ---------------- NEXT EPISODE ----------------
    elif data == "next_ep":

        current_url = user_data[chat_id]["url"]

        new_url = next_episode_url(current_url)

        if not new_url:
            await query.message.reply_text("❌ Cannot next episode")
            return

        new_post_id = get_post_id(new_url)

        if not new_post_id:
            await query.message.reply_text("❌ Cannot get new post ID")
            return

        await send_episode(
            chat_id,
            context,
            new_url,
            new_post_id
        )

    # ---------------- REFRESH EPISODE ----------------
    elif data == "refresh":

        await send_episode(chat_id, context, url, post_id)

# ---------------------------
# REGISTER HANDLERS
# ---------------------------
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
# ---------------------------
print("Bot running...")
app.run_polling()