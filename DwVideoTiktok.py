import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TOKEN = "8817230493:AAH6akiHO-bvv5hx1AxhK6MuYC17ZCVO41c"

def download_tiktok(url):
    
    ydl_opts = {
    "format": "mp4",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send TikTok link 🎥")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    if "tiktok.com" not in url:
        await update.message.reply_text("❌ Invalid link")
        return

    await update.message.reply_text("⬇️ Downloading...")

    try:
        file_path = download_tiktok(url)

        await update.message.reply_video(video=open(file_path, "rb"))

        os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()