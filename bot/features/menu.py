# bot/features/menu.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler


# --- Клавиатуры ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 Личный кабинет", callback_data="menu_profile")],
        [InlineKeyboardButton("💎 Премиум функционал", callback_data="menu_premium")],
        [InlineKeyboardButton("🔧 Функционал", callback_data="menu_features")],
        [InlineKeyboardButton("🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton("🛡 Антивирус", callback_data="menu_antivirus")],
        [InlineKeyboardButton("🌐 Обход блокировок", callback_data="menu_unlock")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications")],
        [InlineKeyboardButton("🌐 Язык", callback_data="settings_language")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Обработчики ---
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Главное меню*\n\nВыбери раздел:",
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )


async def handle_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # --- Главное меню ---
    if data == "menu_main":
        await query.edit_message_text("📌 *Главное меню*", reply_markup=get_main_menu(), parse_mode='Markdown')

    # --- Личный кабинет ---
    elif data == "menu_profile":
        await query.edit_message_text(
            "👤 *Личный кабинет*\n\n"
            "🔹 Статус: Бесплатный\n"
            "🔹 Подписка: не активна\n"
            "🔹 Регистрация: сегодня\n\n"
            "🛠 В разработке...",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Премиум функционал ---
    elif data == "menu_premium":
        await query.edit_message_text(
            "💎 *Премиум функционал*\n\n"
            "Доступно только по подписке:\n"
            "• Ускоренный отклик\n"
            "• Неограниченные напоминания\n"
            "• Экспорт данных\n"
            "• Приоритетная поддержка\n\n"
            "🛠 В разработке...",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Функционал ---
    elif data == "menu_features":
        await query.edit_message_text(
            "🔧 *Функционал*\n\n"
            "Список доступных функций:\n"
            "• Напоминания\n"
            "• Список дел\n"
            "• Календарь\n"
            "• Голосовые команды\n\n"
            "🛠 Все функции в разработке",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Игры ---
    elif data == "menu_games":
        await query.edit_message_text(
            "🎮 *Игры*\n\n"
            "Доступные игры:\n"
            "• Викторина\n"
            "• Угадай число\n"
            "• Крестики-нолики\n\n"
            "🛠 Игры скоро появятся!",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Антивирус ---
    elif data == "menu_antivirus":
        await query.edit_message_text(
            "🛡 *Антивирус*\n\n"
            "Проверка безопасности:\n"
            "• Сканирование ссылок\n"
            "• Проверка файлов\n"
            "• Блокировка фишинга\n\n"
            "🛠 Модуль в разработке",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Обход блокировок ---
    elif data == "menu_unlock":
        await query.edit_message_text(
            "🌐 *Обход блокировок*\n\n"
            "Функции:\n"
            "• Прокси-бот\n"
            "• Шифрование трафика\n"
            "• Доступ к заблокированным ресурсам\n\n"
            "⚠️ В разработке. Следите за обновлениями.",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Настройки ---
    elif data == "menu_settings":
        await query.edit_message_text(
            "⚙️ *Настройки*\n\nВыбери параметр:",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )

    # --- Подменю: Уведомления ---
    elif data == "settings_notifications":
        await query.edit_message_text(
            "🔔 *Уведомления*\n\n"
            "Текущий статус: выключены\n\n"
            "🛠 Настройка скоро будет доступна",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )

    # --- Подменю: Язык ---
    elif data == "settings_language":
        await query.edit_message_text(
            "🌐 *Язык*\n\n"
            "Доступные языки:\n"
            "• Русский\n"
            "• English\n\n"
            "🛠 Переключение в разработке",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )


# --- Регистрация ---
def setup(application):
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(
        CallbackQueryHandler(handle_menu_callbacks, pattern=r"^menu_|^settings_")
    )
