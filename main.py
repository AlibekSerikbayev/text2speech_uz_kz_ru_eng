import telebot
import traceback
import subprocess
import os
import logging
from telebot import types
import whisper
from dotenv import load_dotenv

# ---------------- ENV YUKLASH ----------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN .env faylda topilmadi!")

# ---------------- LOGGING --------------------
LOG_FOLDER = ".logs"
os.makedirs(LOG_FOLDER, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    filename=f"{LOG_FOLDER}/app.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bot")

# ---------------- TELEGRAM -------------------
bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- WHISPER --------------------
model = whisper.load_model("small")
print("Whisper modeli yuklandi")

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "🎤 Ovoz yuboring. Men uni matnga aylantiraman.\n"
        "Tillar: Uzbek 🇺🇿, Russian 🇷🇺, Kazakh 🇰🇿, English 🇺🇸\n"
        "Til avtomatik aniqlanadi."
    )

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)

    # Faylni yuklab olish
    downloaded = bot.download_file(file_info.file_path)
    with open("audio.ogg", "wb") as f:
        f.write(downloaded)

    # Avval WAV ga o‘tkazamiz
    subprocess.run(
        ["ffmpeg", "-y", "-i", "audio.ogg", "-ar", "16000", "-ac", "1", "audio.wav"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        result = model.transcribe("audio.wav", fp16=False)
        text = result["text"].strip()
        lang = result.get("language", "?")
    except Exception:
        bot.send_message(message.chat.id, "❌ Transkripsiya qilinmadi.")
        logger.error(traceback.format_exc())
        return

    bot.send_message(
        message.chat.id,
        f"📝 *Matn:* \n{text}\n\n🌐 *Aniqlangan til:* `{lang}`",
        parse_mode="Markdown"
    )

    clear_temp()

def clear_temp():
    for f in ["audio.wav", "audio.ogg"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == '__main__':
    logger.info("Bot ishga tushdi")
    bot.polling(none_stop=True)
    logger.info("Bot to‘xtadi")
