# bot/commands/antivirus.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
import requests
import os
from bot.database import log_action

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
VT_FILE_SCAN_URL = "https://www.virustotal.com/api/v3/files"
VT_URL_SCAN_URL = "https://www.virustotal.com/api/v3/urls"
VT_REPORT_URL = "https://www.virustotal.com/api/v3/analyses/"

async def virus_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверка ссылки
    if update.message.text and update.message.entities:
        for entity in update.message.entities:
            if entity.type == "url":
                url = update.message.text[entity.offset:entity.offset + entity.length]
                await _scan_url(update, context, url)
                log_action(user_id, "check_url", url)
                return

    # Проверка файла
    if update.message.document:
        file = update.message.document
        if file.file_size > 32 * 1024 * 1024:  # >32 МБ
            await update.message.reply_text("❌ Файл слишком большой. Максимум — 32 МБ.")
            return

        if file.mime_type in ["text/plain", "application/zip", "application/x-rar-compressed", 
                              "application/pdf", "application/vnd.ms-excel", 
                              "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            await update.message.reply_text("🔍 Проверяю файл на вирусы...")
            file_obj = await context.bot.get_file(file.file_id)
            await _scan_file(update, context, file_obj, file.file_name)
            log_action(user_id, "check_file", file.file_name)

    elif update.message.photo:
        # Берём самое большое фото
        photo = update.message.photo[-1]
        if photo.file_size > 32 * 1024 * 1024:
            await update.message.reply_text("📸 Фото слишком большое для проверки.")
            return
        await update.message.reply_text("🔍 Проверяю фото на угрозы...")
        file_obj = await context.bot.get_file(photo.file_id)
        await _scan_file(update, context, file_obj, "photo.jpg")


async def _scan_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_obj, file_name):
    try:
        # Скачиваем файл
        file_data = await file_obj.download_as_bytearray()

        # Отправляем на VirusTotal
        headers = {"x-apikey": VIRUSTOTAL_API_KEY}
        response = requests.post(
            VT_FILE_SCAN_URL,
            headers=headers,
            files={"file": (file_name, file_data)}
        )

        if response.status_code == 200:
            data = response.json()
            analysis_id = data["data"]["id"]
            await _wait_and_send_report(update, context, analysis_id, "file")
        else:
            await update.message.reply_text(f"❌ Ошибка: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при проверке: {str(e)}")


async def _scan_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    try:
        headers = {"x-apikey": VIRUSTOTAL_API_KEY}
        data = {"url": url}
        response = requests.post(VT_URL_SCAN_URL, headers=headers, data=data)

        if response.status_code == 200:
            data = response.json()
            analysis_id = data["data"]["id"]
            await _wait_and_send_report(update, context, analysis_id, "url", url)
        else:
            await update.message.reply_text(f"❌ Ошибка: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при проверке ссылки: {str(e)}")


async def _wait_and_send_report(update: Update, context: ContextTypes.DEFAULT_TYPE, analysis_id: str, type: str, url=None):
    import asyncio
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}

    # Ждём до 30 секунд (VirusTotal может анализировать)
    for _ in range(6):
        await asyncio.sleep(5)
        response = requests.get(f"{VT_REPORT_URL}{analysis_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            attributes = data["data"]["attributes"]
            stats = attributes["stats"]
            malicious = stats["malicious"]
            total = sum(stats.values())

            link = f"https://www.virustotal.com/gui/{'file' if type == 'file' else 'url'}/{analysis_id}"

            if type == "url":
                msg = f"🌐 *Результат проверки ссылки*\n\n"
                msg += f"🔍 Ссылка: `{url}`\n"
            else:
                msg = f"📁 *Результат проверки файла*\n\n"

            msg += f"🟢 Безопасно: {stats['harmless']} сервисов\n"
            msg += f"🔴 Вредоносно: {malicious} сервисов\n"
            msg += f"🟡 Подозрительно: {stats['suspicious']}\n"
            msg += f"⚪ Неизвестно: {stats['undetected']}\n\n"

            if malicious > 0:
                msg += "🚨 *Высокий риск!* Ссылка/файл содержит вредоносный код.\n"
                msg += "❌ Не рекомендуется открывать."
            else:
                msg += "✅ Никаких угроз не обнаружено.\n"
                msg += "🟢 Считается безопасным."

            msg += f"\n\n🔍 Подробнее: [VirusTotal]({link})"

            await update.message.reply_text(msg, parse_mode='Markdown', disable_web_page_preview=True)
            return

    await update.message.reply_text("⏳ Время ожидания истекло. Попробуйте позже: [VirusTotal](https://www.virustotal.com)", 
                                   parse_mode='Markdown')


# Рекомендуемые антивирусы (по твоему списку)
ANTIVIRUS_LINKS = {
    "Dr.Web CureIt!": "https://free.drweb.ru/cureit/",
    "Malwarebytes AdwCleaner": "https://www.malwarebytes.com/adwcleaner",
    "MinerSearch": "https://github.com/SecurityLab/MinerSearch"
}

async def antivirus_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /antivirus — показывает список рекомендованных утилит"""
    msg = "🛡️ *Рекомендуемые антивирусные утилиты*\n\n"
    for name, link in ANTIVIRUS_LINKS.items():
        msg += f"• [{name}]({link})\n"
    msg += "\n💡 Используйте для глубокой проверки ПК."
    await update.message.reply_text(msg, parse_mode='Markdown')
