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

# ---------------------------
# CONFIG
# ---------------------------
TOKEN = "8648355227:AAHEK_QyvJrBfX-lSsoFO6wVqQAOQGwR_NM"
user_data = {}

# ---------------------------
# TELEGRAM BOT APP
# ---------------------------
app = ApplicationBuilder().token(TOKEN).build()

# ---------------------------
# GET POST ID
# ---------------------------
def get_post_id(url):
    try:
        html = requests.get(url, timeout=10).text

        match = re.search(r'postid-(\d+)', html)

        if match:
            return match.group(1)

        return None

    except Exception as e:
        print("POST ID ERROR:", e)
        return None

def clean_title(url):
    try:
        html = requests.get(url, timeout=10).text
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)

        if match:
            title = match.group(1)

            # remove site branding
            title = title.replace("– KhDiaMonD", "")
            title = title.replace("| KhDiaMonD", "")
            return title.strip()

        return "UNKNOWN TITLE"
    except:
        return "UNKNOWN TITLE"
    
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
        print("PLAYER ERROR:", e)
        return None


# ---------------------------
# NEXT EPISODE URL
# ---------------------------
def next_episode_url(url):

    match = re.search(r"(.*-)(\d+x)(\d+)/?$", url)

    if not match:
        return None

    base = match.group(1)
    season = match.group(2)
    episode = int(match.group(3)) + 1

    return f"{base}{season}{episode}/"


# ---------------------------
# SEND EPISODE
# ---------------------------
async def send_episode(chat_id, context, url, post_id):

    link = get_player_link(post_id, 1, "tv")

    if not link:
        await context.bot.send_message(
            chat_id,
            "❌ Episode not found"
        )
        return

    # SAVE CURRENT DATA
    user_data[chat_id]["url"] = url
    user_data[chat_id]["post_id"] = post_id

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
            await update.message.reply_text(
                "❌ Cannot get post ID"
            )
            return

        user_data[chat_id] = {
            "post_id": post_id,
            "url": text
        }

        keyboard = [
            [
                InlineKeyboardButton(
                    "🎬 Movie",
                    callback_data="movie"
                ),

                InlineKeyboardButton(
                    "📺 Episode",
                    callback_data="episode"
                )
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

    if chat_id not in user_data:
        await query.message.reply_text(
            "❌ Send link first"
        )
        return

    post_id = user_data[chat_id]["post_id"]
    url = user_data[chat_id]["url"]

    # ---------------- MOVIE ----------------
    if data == "movie":

        link = get_player_link(post_id, 1, "movie")

        if not link:
            await query.message.reply_text(
                "❌ Movie not found"
            )
            return

        await query.message.reply_text(
            f"📺 MOVIE:\n{url}\n\n🎥 WATCH:\n{link}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Refresh", callback_data="refresh")]
            ]),
        )


    # ---------------- EPISODE ----------------
    elif data == "episode":

        await send_episode(
            chat_id,
            context,
            url,
            post_id
        )

    # ---------------- NEXT EPISODE ----------------
    elif data == "next_ep":

        current_url = user_data[chat_id]["url"]

        new_url = next_episode_url(current_url)

        if not new_url:
            await query.message.reply_text(
                "❌ Cannot next episode"
            )
            return

        # GET NEW POST ID
        new_post_id = get_post_id(new_url)

        if not new_post_id:
            await query.message.reply_text(
                "❌ Cannot get new post ID"
            )
            return

        # SEND NEW EPISODE
        await send_episode(
            chat_id,
            context,
            new_url,
            new_post_id
        )

    # ---------------- REFRESH ----------------
    elif data == "refresh":

        await send_episode(
            chat_id,
            context,
            url,
            post_id
        )


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