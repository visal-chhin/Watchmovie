import os
import re
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from telegram.request import HTTPXRequest

# ---------------------------
# CONFIG
# ---------------------------
TOKEN = "8648355227:AAHEK_QyvJrBfX-lSsoFO6wVqQAOQGwR_NM"
  # put your token in environment
user_data = {}

# ---------------------------
# FIX: NETWORK TIMEOUT HANDLER
# ---------------------------
request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30
)

app = ApplicationBuilder().token(TOKEN).request(request).build()

# ---------------------------
# GET POST ID
# ---------------------------
def get_post_id(url):
    try:
        html = requests.get(url, timeout=15).text

        match = re.search(r'postid-(\d+)', html)
        if not match:
            match = re.search(r'class="[^"]*postid-(\d+)[^"]*"', html)

        return match.group(1) if match else None

    except Exception as e:
        print("POST ID ERROR:", e)
        return None


# ---------------------------
# GET PLAYER LINK
# ---------------------------
def get_player_link(post_id, nume=1, type_="movie"):
    try:
        ajax_url = "https://khdiamond.net/wp-admin/admin-ajax.php"

        data = {
            "action": "doo_player_ajax",
            "post": post_id,
            "nume": str(nume),
            "type": type_
        }

        r = requests.post(ajax_url, data=data, timeout=15)

        match = re.search(r'https:\\/\\/player\.khdiamond\.net[^"]+', r.text)

        if match:
            return match.group(0).replace("\\/", "/")

        return None

    except Exception as e:
        print("PLAYER ERROR:", e)
        return None


# ---------------------------
# NEXT EPISODE
# ---------------------------
def next_episode_url(url):
    try:
        url = url.rstrip("/")
        base, ep = url.rsplit("-", 1)

        season, episode = ep.split("x")
        episode = int(episode) + 1

        return f"{base}-{season}x{episode}/"

    except:
        return None


# ---------------------------
# SEND EPISODE
# ---------------------------
async def send_episode(chat_id, context, url, post_id):

    link = get_player_link(post_id, 1, "tv")

    if not link:
        await context.bot.send_message(chat_id, "❌ Episode not found")
        return

    user_data[chat_id] = user_data.get(chat_id, {})
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
# MESSAGE HANDLER
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text.startswith("https://khdiamond.net/"):
        await update.message.reply_text("❌ Only khdiamond links allowed")
        return

    post_id = get_post_id(text)

    if not post_id:
        await update.message.reply_text("❌ Cannot get post ID")
        return

    user_data[chat_id] = {
        "post_id": post_id,
        "url": text
    }

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


# ---------------------------
# BUTTON HANDLER
# ---------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data

    if chat_id not in user_data:
        await query.message.reply_text("❌ Send link first")
        return

    post_id = user_data[chat_id]["post_id"]
    url = user_data[chat_id]["url"]

    # ---------------- MOVIE ----------------
    if data == "movie":

        link = get_player_link(post_id, 1, "movie")

        if not link:
            await query.message.reply_text("❌ Movie not found")
            return

        user_data[chat_id]["type"] = "movie"

        await query.message.reply_text(
            f"📺 MOVIE:\n{url}\n\n🎥 WATCH:\n{link}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Refresh", callback_data="refresh")]
            ])
        )

    # ---------------- EPISODE ----------------
    elif data == "episode":
        await send_episode(chat_id, context, url, post_id)

    # ---------------- NEXT EP ----------------
    elif data == "next_ep":

        new_url = next_episode_url(url)

        if not new_url:
            await query.message.reply_text("❌ Cannot next episode")
            return

        new_post_id = get_post_id(new_url)

        if not new_post_id:
            await query.message.reply_text("❌ Cannot get new post ID")
            return

        await send_episode(chat_id, context, new_url, new_post_id)

    # ---------------- REFRESH ----------------
    elif data == "refresh":

        if user_data[chat_id].get("type") == "movie":
            link = get_player_link(post_id, 1, "movie")
            if not link:
                await query.message.reply_text("❌ Movie not found")
                return

            await query.message.reply_text(f"🎥 MOVIE:\n{link}")
        else:
            await send_episode(chat_id, context, url, post_id)


# ---------------------------
# REGISTER HANDLERS
# ---------------------------
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

# ---------------------------
# RUN BOT
# ---------------------------
print("Bot running...")
app.run_polling()