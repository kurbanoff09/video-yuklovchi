import os
import re
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AD_BOT_USERNAME = os.getenv("AD_BOT_USERNAME", "AdInboxBot")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

user_lang = {}

LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(LANGUAGES[code], callback_data=f"lang_{code}") for code in LANGUAGES]
    ]
    await update.message.reply_text(
        "Tilni tanlang / Choose your language / Выберите язык:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split("_")[1]
    user_lang[query.from_user.id] = lang_code

    keyboard = [
        [InlineKeyboardButton("📄 YouTube/Instagram/TikTok", callback_data="download")],
        [InlineKeyboardButton("🖖 Premium", callback_data="premium")],
        [InlineKeyboardButton("🗣 Reklama", callback_data="reklama")]
    ]

    texts = {
        "uz": "Xizmatlardan birini tanlang:",
        "ru": "Выберите услугу:",
        "en": "Choose a service:"
    }

    await query.edit_message_text(
        texts.get(lang_code, texts["uz"]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("🔗 Video yoki audio havolasini yuboring:")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not re.match(r'https?://', url):
        await update.message.reply_text("❌ Iltimos, to'g'ri havola yuboring.")
        return

    context.user_data["url"] = url

    keyboard = [[
        InlineKeyboardButton("🎥 Video", callback_data="get_video"),
        InlineKeyboardButton("🎵 Audio", callback_data="get_audio")
    ]]
    await update.message.reply_text("Yuklash turini tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def fetch_from_rapidapi(url: str):
    api_url = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "social-download-all-in-one.p.rapidapi.com"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params={"url": url}, headers=headers) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    url = context.user_data.get("url")

    if not url:
        await query.message.reply_text("❌ Avval havola yuboring.")
        return

    await query.message.reply_text("⏳ Yuklanmoqda...")
    data = await fetch_from_rapidapi(url)
    if not data or data.get("error"):
        await query.message.reply_text("❌ Yuklab bo‘lmadi.")
        return

    file_url = None
    if action == "get_video":
        for media in data.get("medias", []):
            if media.get("type") == "video" and "no_watermark" in media.get("quality", ""):
                file_url = media.get("url")
                break
    elif action == "get_audio":
        for media in data.get("medias", []):
            if media.get("type") == "audio":
                file_url = media.get("url")
                break

    if not file_url:
        await query.message.reply_text("❌ Tegishli fayl topilmadi.")
        return

    caption = "🔗 Yuklangan. 🤝 @YourBotUsername orqali yuklandi."
    try:
        if action == "get_video":
            await query.message.reply_video(video=file_url, caption=caption)
        else:
            await query.message.reply_audio(audio=file_url, caption=caption)
    except Exception as e:
        await query.message.reply_text(f"❌ Yuklab bo‘lmadi: {str(e)}")

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, "uz")
    texts = {
        "uz": f"👑 Premium olish uchun @{AD_BOT_USERNAME} ga murojaat qiling.\nNarxi: 10 000 so‘m\nReklama chiqmaydi.",
        "ru": f"👑 Чтобы получить премиум, напишите @{AD_BOT_USERNAME}.\nЦена: 10 000 сум\nРеклама отключена.",
        "en": f"👑 To get premium, contact @{AD_BOT_USERNAME}.\nPrice: 10,000 UZS\nNo ads will be shown."
    }
    await update.callback_query.message.reply_text(texts.get(lang, texts["uz"]))

async def reklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, "uz")
    texts = {
        "uz": f"📣 Reklama berish uchun @{AD_BOT_USERNAME} ga yozing. Admin siz bilan bog‘lanadi.",
        "ru": f"📣 Для размещения рекламы напишите @{AD_BOT_USERNAME}. Админ свяжется с вами.",
        "en": f"📣 To place an ad, contact @{AD_BOT_USERNAME}. Admin will reply to you."
    }
    await update.callback_query.message.reply_text(texts.get(lang, texts["uz"]))

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("lang_"):
        await set_language(update, context)
    elif data == "premium":
        await premium(update, context)
    elif data == "reklama":
        await reklama(update, context)
    elif data == "download":
        await download_menu(update, context)
    elif data in ["get_video", "get_audio"]:
        await process_download(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()

if __name__ == '__main__':
    main()
