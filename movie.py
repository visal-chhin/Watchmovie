import os
import re
import json
import time
import threading
import requests

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# -------------------------
# CONFIG
# -------------------------

load_dotenv()

TOKEN = "8648355227:AAHcQQySFDT3EZvWRJ4rEh7nK7rTQXOp8qk"

AJAX_ENDPOINT = "https://khdiamond.net/wp-admin/admin-ajax.php"
BASE_REFERER = "https://khdiamond.net"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://khdiamond.net/",
    "Origin": "https://khdiamond.net",
}

POST_ID_REGEX = re.compile(r"postid-(\d+)")

stats_file = "stats.json"

# -------------------------
# STATS
# -------------------------

stats = {
    "total_requests": 0,
    "users": {}
}

pending_urls = {}

lock = threading.Lock()


def load_stats():
    global stats

    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except:
            pass


def save_stats():
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)


def track_user(chat_id, username):
    with lock:
        key = str(chat_id)

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        stats["total_requests"] += 1

        if key not in stats["users"]:
            stats["users"][key] = {
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "request_count": 0
            }

        stats["users"][key]["request_count"] += 1
        stats["users"][key]["last_seen"] = now

        if username:
            stats["users"][key]["username"] = username

        save_stats()


def stats_report():
    users = list(stats["users"].values())

    users.sort(
        key=lambda x: x["request_count"],
        reverse=True
    )

    top = users[:5]

    lines = []

    for i, user in enumerate(top, start=1):
        lines.append(
            f"{i}. @{user['username']} — {user['request_count']} requests"
        )

    return (
        f"Stats:\n\n"
        f"Total Users: {len(stats['users'])}\n"
        f"Total Requests: {stats['total_requests']}\n\n"
        f"Top 5 Users:\n"
        + "\n".join(lines)
    )


# -------------------------
# KHDIAMOND
# -------------------------

def fetch_html(url, referer):
    headers = HEADERS.copy()
    headers["Referer"] = referer

    r = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    r.raise_for_status()

    return r.text


def get_stream(url, media_type):
    html = fetch_html(url, BASE_REFERER)

    match = POST_ID_REGEX.search(html)

    if not match:
        raise Exception("No post ID found")

    post_id = match.group(1)

    payload = {
        "action": "doo_player_ajax",
        "post": post_id,
        "nume": "1",
        "type": media_type
    }

    headers = HEADERS.copy()
    headers["Referer"] = url

    r = requests.post(
        AJAX_ENDPOINT,
        data=payload,
        headers=headers,
        timeout=30
    )

    r.raise_for_status()

    data = r.json()

    embed_url = data.get("embed_url")

    if not embed_url:
        raise Exception("No embed_url found")

    return embed_url


# -------------------------
# COMMANDS
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a khdiamond.net URL."
    )


async def count_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        stats_report()
    )


# -------------------------
# MESSAGE
# -------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text.startswith("http"):
        await update.message.reply_text(
            "Please send a valid URL."
        )
        return

    if "khdiamond.net" not in text:
        await update.message.reply_text(
            "Only khdiamond.net URLs are supported."
        )
        return

    pending_urls[chat_id] = text

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📺 Movie",
                callback_data="movie"
            ),
            InlineKeyboardButton(
                "🎥 TV Show",
                callback_data="tv"
            )
        ]
    ])

    await update.message.reply_text(
        "Is this Movie or TV Show?",
        reply_markup=keyboard
    )


# -------------------------
# CALLBACK
# -------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat.id

    if chat_id not in pending_urls:
        await query.message.reply_text(
            "Session expired."
        )
        return

    page_url = pending_urls.pop(chat_id)

    media_type = "movie"

    if query.data == "tv":
        media_type = "tv"

    username = query.from_user.username or query.from_user.first_name

    track_user(chat_id, username)

    loading = await query.message.reply_text(
        f"Fetching {media_type} stream..."
    )

    try:
        embed_url = get_stream(
            page_url,
            media_type
        )

        await query.message.reply_text(
            f"📺 {media_type.upper()}:\n"
            f"{page_url}\n\n"
            f"🎥 WATCH:\n"
            f"{embed_url}"
        )

    except Exception as e:
        await query.message.reply_text(
            f"Error: {str(e)}"
        )

    try:
        r.raise_for_status()
    except Exception as e:
            print("FAILED URL:", r.url)
            print("STATUS:", r.status_code)
            print(r.text[:500])
            raise
    except:
        pass


# -------------------------
# MAIN
# -------------------------

def main():
    load_stats()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler(
            "count_process",
            count_process
        )
    )

    app.add_handler(
        CallbackQueryHandler(handle_callback)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()