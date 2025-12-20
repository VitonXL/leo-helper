# bot/features/menu.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import get_db_pool, get_referral_stats, get_user_settings, update_user_theme

# --- Локализация ---
TEXTS = {
    "ru": {
        "menu_title": "📌 *Главное меню*\n\nВыбери раздел:",
        "profile_title": "🔐 <b>Личный кабинет</b>",
        "profile_intro": "Откройте полный интерфейс управления:",
        "profile_web": "🔗 <a href='{link}'>Перейти в кабинет</a>",
        "profile_desc": "Тут вы можете:\n• Проверить подписку\n• Управлять рефералами\n• Сменить тему\n• Подключить GigaChat",
        "settings_theme": "🌙 *Тема: {theme}*",
        "settings_theme_desc": "Сейчас используется: <b>{theme}</b>\n\nНажмите ниже, чтобы сменить.",
        "theme_light": "Светлая",
        "theme_dark": "Тёмкая"
    },
    "en": {
        "menu_title": "📌 *Main Menu*\n\nChoose a section:",
        "profile_title": "🔐 <b>Profile</b>",
        "profile_intro": "Open full management interface:",
        "profile_web": "🔗 <a href='{link}'>Open cabinet</a>",
        "profile_desc": "Here you can:\n• Check subscription\n• Manage referrals\n• Change theme\n• Connect GigaChat",
        "settings_theme": "🌙 *Theme: {theme}*",
        "settings_theme_desc": "Current: <b>{theme}</b>\n\nTap below to change.",
        "theme_light": "Light",
        "theme_dark": "Dark"
    }
}


# --- Клавиатуры ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🧑‍💼 Личный кабинет", callback_data="menu_profile")],
        [InlineKeyboardButton("💎 Премиум", callback_data="menu_premium")],
        [InlineKeyboardButton("🛠️ Функции", callback_data="menu_features")],
        [
            InlineKeyboardButton("🎮 Игры", callback_data="menu_games"),
            InlineKeyboardButton("🛡️ Безопасность", callback_data="menu_antivirus")
        ],
        [
            InlineKeyboardButton("🌐 Обход", callback_data="menu_unlock"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_profile_menu():
    keyboard = [
        [InlineKeyboardButton("💳 Подписка", callback_data="profile_premium")],
        [InlineKeyboardButton("🤝 Рефералы", callback_data="profile_referral")],
        [InlineKeyboardButton("🔐 Настройки", callback_data="profile_settings")],
        [InlineKeyboardButton("ℹ️ Профиль", callback_data="profile_info")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_features_menu():
    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="features_weather")],
        [InlineKeyboardButton("💱 Курсы", callback_data="features_currency")],
        [InlineKeyboardButton("🔔 Напоминания", callback_data="features_reminders")],
        [InlineKeyboardButton("📋 Подписки", callback_data="features_subscriptions")],
        [InlineKeyboardButton("🎯 Игры", callback_data="features_telegram_games")],
        [InlineKeyboardButton("📰 Новости", callback_data="features_news")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_premium_menu():
    keyboard = [
        [InlineKeyboardButton("🤖 GigaChat", callback_data="premium_gigachat")],
        [InlineKeyboardButton("🎮 Кастом-игры", callback_data="premium_games")],
        [InlineKeyboardButton("🎬 Фильмы", callback_data="premium_movies")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")],
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
    user = update.effective_user
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT language FROM users WHERE id = $1", user.id)
        lang = row["language"] if row and row["language"] else "ru"

    await update.message.reply_text(
        TEXTS[lang]["menu_title"],
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )


async def handle_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие

    user = query.from_user
    data = query.data

    pool = await get_db_pool()

    # Получаем настройки и рефералов
    settings = await get_user_settings(pool, user.id)
    lang = settings["language"]
    theme = settings["theme"]
    referrals = await get_referral_stats(pool, user.id)
    premium = "✅ есть" if settings.get("premium_expires") else "❌ нет"

    # --- Главное меню ---
    if data == "menu_main":
        await query.edit_message_text("📌 *Главное меню*", reply_markup=get_main_menu(), parse_mode='Markdown')

    # --- Личный кабинет ---
    elif data == "menu_profile":
        try:
            from utils import generate_cabinet_link
            link = generate_cabinet_link(user.id)
            await query.edit_message_text(
                "🔐 <b>Личный кабинет</b>\n\n"
                "Откройте полный интерфейс управления:\n"
                f"<a href='{link}'>Перейти в кабинет</a>\n\n"
                "Тут вы можете:\n"
                "• Проверить подписку\n"
                "• Управлять рефералами\n"
                "• Сменить тему\n"
                "• Подключить GigaChat",
                reply_markup=get_profile_menu(),
                parse_mode='HTML',
                disable_web_page_preview=False
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка: не удалось сгенерировать ссылку\n{e}",
                reply_markup=get_profile_menu()
            )

    elif data == "profile_premium":
        await query.answer("💳 Подписка — скоро!", show_alert=False)
        await query.edit_message_text(
            "💎 *Премиум-подписка*\n\n"
            "🔹 Все функции без ограничений\n"
            "🔹 Приоритетная поддержка\n"
            "🔹 Экспорт данных\n\n"
            "Цена: 199 ₽/мес\n\n"
            "🛠 Платежи скоро!",
            reply_markup=get_profile_menu(),
            parse_mode='Markdown'
        )

    elif data == "profile_referral":
        await query.answer("🤝 Рефералы — скоро!", show_alert=False)
        await query.edit_message_text(
            "🔗 *Реферальная система*\n\n"
            "Приглашай друзей и получай бонусы!\n\n"
            "🔗 Реф. ссылка: `t.me/Leo_aide_bot?start=ref123`\n"
            f"🎁 +3 дня за {referrals} друзей\n\n"
            "🛠 Активация скоро",
            reply_markup=get_profile_menu(),
            parse_mode='Markdown'
        )

    elif data == "profile_settings":
        await query.answer("🔐 Настройки — скоро!", show_alert=False)
        await query.edit_message_text(
            "⚙️ *Настройки аккаунта*\n\n"
            "• Смена имени\n"
            "• Привязка email\n"
            "• Безопасность\n\n"
            "🛠 Разрабатывается",
            reply_markup=get_profile_menu(),
            parse_mode='Markdown'
        )

    elif data == "profile_info":
        await query.answer("ℹ️ Данные загружаются...", show_alert=False)
        await query.edit_message_text(
            "📋 *Информация об аккаунте*\n\n"
            f"• ID: `{user.id}`\n"
            f"• Подписка: {premium}\n"
            f"• Рефералов: {referrals}\n"
            f"• Язык: {lang}\n"
            f"• Тема: {TEXTS[lang]['theme_light'] if theme == 'light' else TEXTS[lang]['theme_dark']}",
            reply_markup=get_profile_menu(),
            parse_mode='Markdown'
        )

    # --- Функционал ---
    elif data == "menu_features":
        await query.edit_message_text(
            "🛠️ *Функции*\n\nВыбери инструмент:",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    elif data == "features_weather":
        await query.answer("🌤 Загрузка погоды...", show_alert=False)
        await query.edit_message_text(
            "🌤 *Погода*\n\n"
            "Используй: `/weather Москва`\n\n"
            "📍 Прогноз на 3 дня\n"
            "🔔 Ежедневные уведомления\n\n"
            "🛠 Реализуется",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    elif data == "features_currency":
        await query.answer("💱 Курсы валют", show_alert=False)
        await query.edit_message_text(
            "💱 *Курсы валют*\n\n"
            "Доступно: USD, EUR, CNY\n\n"
            "Используй: `/currency USD`",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    elif data == "features_reminders":
        await query.answer("🔔 Напоминания — скоро!", show_alert=False)
        await query.edit_message_text(
            "🕰 *Напоминания*\n\n"
            "Создай: `/remind 30 Встать`\n\n"
            "📌 Сохраняются в облаке\n"
            "🔔 Уведомления точно вовремя\n\n"
            "🛠 Готовится к запуску",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    elif data == "features_subscriptions":
        await query.answer("📋 Подписки — скоро!", show_alert=False)
        await query.edit_message_text(
            "🔔 *Отслеживание подписок*\n\n"
            "Контролируй:\n"
            "• YouTube\n"
            "• Spotify\n"
            "• Telegram Premium\n\n"
            "🔔 Напоминание за 3 дня",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    elif data == "features_telegram_games":
        await query.answer("🎯 Игры — скоро!", show_alert=False)
        await query.edit_message_text(
            "🎮 *Telegram Игры*\n\n"
            "Сыграй в:\n"
            "• @gamee\n"
            "• @fork_delta_bot\n"
            "• @snake\n\n"
            "🕹 Подбор лучших — скоро",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    elif data == "features_news":
        await query.answer("📰 Новости — скоро!", show_alert=False)
        await query.edit_message_text(
            "📰 *Новости*\n\n"
            "Темы:\n"
            "• Технологии\n"
            "• Финансы\n"
            "• Обновления Telegram\n\n"
            "🛠 Лента в разработке",
            reply_markup=get_features_menu(),
            parse_mode='Markdown'
        )

    # --- Премиум ---
    elif data == "menu_premium":
        await query.edit_message_text(
            "💎 *Премиум*\n\nЭксклюзивные функции:",
            reply_markup=get_premium_menu(),
            parse_mode='Markdown'
        )

    elif data == "premium_gigachat":
        await query.answer("🤖 GigaChat — скоро!", show_alert=False)
        await query.edit_message_text(
            "🤖 *GigaChat*\n\n"
            "Задай любой вопрос:\n"
            "`/giga Расскажи про ИИ`\n\n"
            "🚀 Мощь ИИ от Сбера\n\n"
            "🛠 Интеграция в процессе",
            reply_markup=get_premium_menu(),
            parse_mode='Markdown'
        )

    elif data == "premium_games":
        await query.answer("🎮 Кастом-игры — скоро!", show_alert=False)
        await query.edit_message_text(
            "🎯 *Кастомные игры*\n\n"
            "• Угадай мем\n"
            "• Викторина по фильмам\n"
            "• Крестики-нолики с ИИ\n\n"
            "🛠 Все игры — в разработке",
            reply_markup=get_premium_menu(),
            parse_mode='Markdown'
        )

    elif data == "premium_movies":
        await query.answer("🎬 Подбор фильмов — скоро!", show_alert=False)
        await query.edit_message_text(
            "🎬 *Подбор фильмов*\n\n"
            "Укажи жанр:\n"
            "`/movie комедия`\n\n"
            "🎯 Подбор по твоим предпочтениям\n\n"
            "🛠 Рекомендации скоро",
            reply_markup=get_premium_menu(),
            parse_mode='Markdown'
        )

    # --- Безопасность ---
    elif data == "menu_antivirus":
        await query.answer("🛡️ Безопасность — скоро!", show_alert=False)
        await query.edit_message_text(
            "🛡️ *Безопасность*\n\n"
            "• Проверка ссылок\n"
            "• Сканирование файлов\n"
            "• Защита от фишинга\n\n"
            "🛠 Модуль в разработке",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Обход блокировок ---
    elif data == "menu_unlock":
        await query.answer("🌐 Обход — скоро!", show_alert=False)
        await query.edit_message_text(
            "🌐 *Обход блокировок*\n\n"
            "• Прокси-бот\n"
            "• Шифрование\n"
            "• Доступ к ресурсам\n\n"
            "⚠️ В разработке",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Настройки ---
    elif data == "menu_settings":
        await query.edit_message_text(
            "⚙️ *Настройки*\n\nУправляй ботом:",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )

    elif data == "settings_notifications":
        await query.answer("🔔 Уведомления — скоро!", show_alert=False)
        await query.edit_message_text(
            "🔔 *Уведомления*\n\n"
            "Статус: ❌ выключены\n\n"
            "🛠 Настройка скоро доступна",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )

    elif data == "settings_language":
        await query.answer("🌐 Язык — скоро!", show_alert=False)
        await query.edit_message_text(
            "🌐 *Язык интерфейса*\n\n"
            "Доступно:\n"
            "• Русский\n"
            "• English\n\n"
            "🛠 Переключение в разработке",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )

    # --- Назад в меню ---
    elif data == "menu_main":
        await query.edit_message_text(
            "📌 *Главное меню*",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )


# --- Регистрация ---
def setup(application):
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(
        CallbackQueryHandler(
            handle_menu_callbacks,
            pattern=r"^menu_|^profile_|^features_|^premium_|^settings_"
        )
    )
