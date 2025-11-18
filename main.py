# filename: stt_bot.py
import os
import tempfile
import subprocess
import logging
from telegram import Update
from telegram.ext import (ApplicationBuilder, ContextTypes,
                          MessageHandler, filters, CommandHandler)
import whisper
from dotenv import load_dotenv

# -------------------- LOAD .env --------------------
load_dotenv()  # .env dagi o'zgaruvchilarni yuklaydi

BOT_TOKEN = os.getenv("BOT_TOKEN")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
# ---------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Loading Whisper model:", WHISPER_MODEL)
model = whisper.load_model(WHISPER_MODEL)
print("Model loaded.")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Menga ovoz yuboring (voice/audio). Men uni matnga aylantiraman.\n"
        "Tilni avtomatik aniqlayman (uz, ru, kk, en)."
    )

def convert_to_wav(input_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-hide_banner",
        "-loglevel", "error",
        output_path
    ]
    subprocess.run(cmd, check=True)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file_obj = None
    ext = "ogg"

    if msg.voice:
        file_obj = await context.bot.get_file(msg.voice.file_id)
        ext = "ogg"
    elif msg.audio:
        file_obj = await context.bot.get_file(msg.audio.file_id)
        ext = msg.audio.file_name.split(".")[-1]
    elif msg.document and msg.document.mime_type.startswith("audio"):
        file_obj = await context.bot.get_file(msg.document.file_id)
        ext = msg.document.file_name.split(".")[-1]
    else:
        await msg.reply_text("Iltimos, voice yoki audio yuboring.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input.{ext}")
        wav_path = os.path.join(tmpdir, "audio.wav")

        await file_obj.download_to_drive(input_path)

        try:
            convert_to_wav(input_path, wav_path)
        except Exception:
            await msg.reply_text("Audio faylni qayta ishlashda xatolik (ffmpeg).")
            return

        try:
            result = model.transcribe(wav_path)
            text = result.get("text", "").strip()
            lang = result.get("language", "unknown")
        except Exception:
            await msg.reply_text("Transkripsiya qilinmadi (Whisper xato).")
            return

        if not text:
            await msg.reply_text("Matn topilmadi.")
            return

        await msg.reply_text(
            f"📝 Matn:\n{text}\n\n🌐 Aniqlangan til: `{lang}`",
            parse_mode="Markdown"
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ovoz yuboring — men uni matnga aylantiraman.")

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN .env faylda topilmadi!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO | (filters.Document & filters.Document.MimeType("audio/*")),
            handle_audio
        )
    )

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
