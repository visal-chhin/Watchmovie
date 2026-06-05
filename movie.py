import os
import re
import time
import requests
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# -------------------------
# CONFIGURATION
# -------------------------
TOKEN = "8648355227:AAHcQQySFDT3EZvWRJ4rEh7nK7rTQXOp8qk"
AJAX_ENDPOINT = "https://khdiamond.net/wp-admin/admin-ajax.php"
BASE_REFERER = "https://khdiamond.net"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
POST_ID_REGEX = re.compile(r"postid-(\d+)")

# Vercel setup
app = FastAPI()
telegram_app = Application.builder().token(TOKEN).build()

# Temporary in-memory state (Warning: clears when Vercel serverless function goes cold)
session_state = {}

# -------------------------
# HANDLERS (Same Logic)
# -------------------------
async def start(update: Update, context):
    await update.message.reply_text("Send me a khdiamond.net URL.")

async def handle_message(update: Update, context):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    if "khdiamond.net" not in text:
        await update.message.reply_text("Only khdiamond.net URLs are supported.")
        return
    
    session_state[chat_id] = {"url": text, "type": "movie", "ep": 1}
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📽️ Movie Mode", callback_data="set_movie"),
        InlineKeyboardButton("📺 TV Show Mode", callback_data="set_tv")
    ]])
    await update.message.reply_text("Choose the stream processing type:", reply_markup=keyboard)

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    if chat_id not in session_state:
        await query.message.reply_text("Session expired. Send link again.")
        return

    state = session_state[chat_id]
    if query.data == "set_movie": state["type"] = "movie"
    elif query.data == "set_tv": state["type"] = "tv"
    elif query.data == "tv_prev" and state["ep"] > 1: state["ep"] -= 1
    elif query.data == "tv_next": state["ep"] += 1

    try:
        r = requests.get(state["url"], headers={"Referer": BASE_REFERER}, timeout=10)
        match = POST_ID_REGEX.search(r.text)
        if not match: raise Exception("No post ID found.")
        
        payload = {
            "action": "doo_player_ajax",
            "post": match.group(1),
            "nume": str(state["ep"]) if state["type"] == "tv" else "1",
            "type": state["type"]
        }
        res = requests.post(AJAX_ENDPOINT, data=payload, headers={"Referer": state["url"]}, timeout=10).json()
        embed_url = res.get("embed_url")

        if state["type"] == "movie":
            loop_k = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh Movie", callback_data="refresh")]])
            out = f"📺 MOVIE:\n{state['url']}\n\n🎥 WATCH:\n{embed_url}\n\nkhdiamond.net"
        else:
            loop_k = InlineKeyboardMarkup([[
                InlineKeyboardButton("⏮️ Prev", callback_data="tv_prev"),
                InlineKeyboardButton("🔄 Refresh", callback_data="tv_refresh"),
                InlineKeyboardButton("⏭️ Next", callback_data="tv_next")
            ]])
            out = f"📺 TV SHOW (EP {state['ep']}):\n{state['url']}\n\n🎥 WATCH:\n{embed_url}\n\nkhdiamond.net"

        await query.message.reply_text(out, reply_markup=loop_k)
    except Exception as e:
        await query.message.reply_text(f"⚠️ Error: {str(e)}")

# Register everything to Telegram Engine
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(handle_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------
# VERCEL WEBHOOK ENDPOINT
# -------------------------
@app.post("/api/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    await telegram_app.initialize()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

@app.get("/")
def index():
    return {"message": "Bot is running on Vercel"}