# bot/features/menu.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import get_db_pool
from utils import generate_cabinet_link

# --- Локализация ---
TEXTS = {
    "ru": {
        "menu_title": "📌 *Главное меню*\n\nВыбери раздел:",
        "profile_title": "🔐 <b>Личный кабинет</b>",
        "profile_intro": "Откройте полный интерфейс управления:",
        "profile_web": "🔗 <a href='{link}'>Перейти в кабинет</a>",
        "profile_desc": "Тут вы можете:\n• Проверить подписку\n• Управлять рефералами\n• Сменить тему\n• Подключить GigaChat",
        "profile_premium": "💎 *Премиум-подписка*",
        "profile_premium_desc": "🔹 Все функции без ограничений\n🔹 Приоритетная поддержка\n🔹 Экспорт данных\n\nЦена: 199 ₽/мес\n\n🛠 Платежи скоро!",
        "profile_referral": "🔗 *Реферальная система*",
        "profile_referral_desc": "Приглашай друзей и получай бонусы!\n\n🔗 Реф. ссылка: <code>t.me/Leo_aide_bot?start=ref123</code>\n🎁 +3 дня за друга\n\n🛠 Активация скоро",
        "profile_settings": "⚙️ *Настройки аккаунта*",
        "profile_settings_desc": "• Смена имени\n• Привязка email\n• Безопасность\n\n🛠 Разрабатывается",
        "profile_info": "📋 *Информация об аккаунте*",
        "profile_info_desc": "• ID: <code>{id}</code>\n• Подписка: {premium}\n• Рефералов: {referrals}\n• Язык: {lang}\n• Тема: {theme}",
        "settings_notifications": "🔔 *Уведомления*",
        "settings_notifications_desc": "Статус: ❌ выключены\n\n🛠 Настройка скоро доступна",
        "settings_language": "🌐 *Язык интерфейса*",
        "settings_language_desc": "Доступно:\n• Русский\n• English\n\n🛠 Переключение в разработке",
        "settings_theme": "🌙 *Тема: {theme}*",
        "settings_theme_desc": "Сейчас используется: <b>{theme}</b>\n\nНажмите ниже, чтобы сменить.",
        "settings_theme_btn": "🌙 Тема: {theme}",
        "theme_light": "Светлая",
        "theme_dark": "Тёмная",
        "lang_ru": "Русский",
        "lang_en": "English",
        "back": "⬅️ Назад",
        "on": "Вкл",
        "off": "Выкл"
    },
    "en": {
        "menu_title": "📌 *Main Menu*\n\nChoose a section:",
        "profile_title": "🔐 <b>Profile</b>",
        "profile_intro": "Open full management interface:",
        "profile_web": "🔗 <a href='{link}'>Open cabinet</a>",
        "profile_desc": "Here you can:\n• Check subscription\n• Manage referrals\n• Change theme\n• Connect GigaChat",
        "profile_premium": "💎 *Premium Subscription*",
        "profile_premium_desc": "🔹 All features unlocked\n🔹 Priority support\n🔹 Data export\n\nPrice: 199 ₽/month\n\n🛠 Payments coming soon!",
        "profile_referral": "🔗 *Referral System*",
        "profile_referral_desc": "Invite friends and get bonuses!\n\n🔗 Ref link: <code>t.me/Leo_aide_bot?start=ref123</code>\n🎁 +3 days per friend\n\n🛠 Activation soon",
        "profile_settings": "⚙️ *Account Settings*",
        "profile_settings_desc": "• Change name\n• Email binding\n• Security\n\n🛠 In development",
        "profile_info": "📋 *Account Info*",
        "profile_info_desc": "• ID: <code>{id}</code>\n• Subscription: {premium}\n• Referrals: {referrals}\n• Language: {lang}\n• Theme: {theme}",
        "settings_notifications": "🔔 *Notifications*",
        "settings_notifications_desc": "Status: ❌ Off\n\n🛠 Settings coming soon",
        "settings_language": "🌐 *Interface Language*",
        "settings_language_desc": "Available:\n• Русский\n• English\n\n🛠 Switching in development",
        "settings_theme": "🌙 *Theme: {theme}*",
        "settings_theme_desc": "Current: <b>{theme}</b>\n\nTap below to change.",
        "settings_theme_btn": "🌙 Theme: {theme}",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "lang_ru": "Russian",
        "lang_en": "English",
        "back": "⬅️ Back",
        "on": "On",
        "off": "Off"
    }
}


# --- Клавиатуры (обновлено с учётом языка) ---
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


def get_settings_menu(lang="ru"):
    theme_btn = TEXTS[lang]["settings_theme_btn"].format(theme=TEXTS[lang]["theme_light"])  # заглушка
    keyboard = [
        [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications")],
        [InlineKeyboardButton("🌐 Язык", callback_data="settings_language")],
        [InlineKeyboardButton(theme_btn, callback_data="settings_theme")],
        [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Обработчики ---
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT language FROM users WHERE id = $1", user_id)
        lang = row["language"] if row and row["language"] else "ru"

    await update.message.reply_text(
        TEXTS[lang]["menu_title"],
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )


async def handle_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    # Определяем язык
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT language, theme, premium_expires, referrals FROM users WHERE id = $1", user.id)
        if row:
            lang = row["language"] or "ru"
            theme = row["theme"] or "light"
            premium = "✅ есть" if row["premium_expires"] else "❌ нет"
            referrals = row["referrals"] or 0
        else:
            lang = "ru"
            theme = "light"
            premium = "❌ нет"
            referrals = 0

    # --- Главное меню ---
    if data == "menu_main":
        await query.edit_message_text(
            TEXTS[lang]["menu_title"],
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )

    # --- Личный кабинет ---
    elif data == "menu_profile":
        link = generate_cabinet_link(user.id)
        await query.edit_message_text(
            f"{TEXTS[lang]['profile_title']}\n\n"
            f"{TEXTS[lang]['profile_intro']}\n"
            f"{TEXTS[lang]['profile_web'].format(link=link)}\n\n"
            f"{TEXTS[lang]['profile_desc']}",
            reply_markup=get_profile_menu(),
            parse_mode='HTML',
            disable_web_page_preview=False
        )

    # --- Профиль → Подписка ---
    elif data == "profile_premium":
        await query.edit_message_text(
            TEXTS[lang]["profile_premium"],
            reply_markup=get_profile_menu(),
            parse_mode='Markdown'
        )

    # --- Профиль → Рефералы ---
    elif data == "profile_referral":
        await query.edit_message_text(
            TEXTS[lang]["profile_referral"],
            reply_markup=get_profile_menu(),
            parse_mode='HTML'
        )

    # --- Профиль → Настройки ---
    elif data == "profile_settings":
        await query.edit_message_text(
            TEXTS[lang]["profile_settings"],
            reply_markup=get_profile_menu(),
            parse_mode='Markdown'
        )

    # --- Профиль → Информация ---
    elif data == "profile_info":
        await query.edit_message_text(
            TEXTS[lang]["profile_info"],
            reply_markup=get_profile_menu(),
            parse_mode='HTML'
        )

    # --- Функции ---
    elif data == "menu_features":
        await query.edit_message_text(
            "🛠️ *Функции*\n\nВыбери инструмент:",
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

    # --- Настройки ---
    elif data == "menu_settings":
        await query.edit_message_text(
            "⚙️ *Настройки*\n\nУправляй ботом:",
            reply_markup=get_settings_menu(lang),
            parse_mode='Markdown'
        )

    # --- Настройки → Тема ---
    elif data == "settings_theme":
        current = TEXTS[lang]["theme_dark"] if theme == "light" else TEXTS[lang]["theme_light"]
        await query.edit_message_text(
            TEXTS[lang]["settings_theme"].format(theme=current),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    f"🌙 Сменить на {TEXTS[lang]['theme_light'] if theme == 'light' else TEXTS[lang]['theme_dark']}",
                    callback_data="settings_theme_toggle"
                ),
                InlineKeyboardButton("⬅️ Назад", callback_data="menu_settings")
            ]]),
            parse_mode='HTML'
        )

    elif data == "settings_theme_toggle":
        new_theme = "dark" if theme == "light" else "light"
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET theme = $1 WHERE id = $2", new_theme, user.id)
        new_label = TEXTS[lang]["theme_light"] if new_theme == "light" else TEXTS[lang]["theme_dark"]
        await query.answer(f"✅ Тема изменена: {new_label}", show_alert=True)
        await query.edit_message_text(
            "⚙️ *Настройки*\n\nУправляй ботом:",
            reply_markup=get_settings_menu(lang),
            parse_mode='Markdown'
        )

    # --- Остальные — без изменений (можно оставить как есть)
    # ... (все остальные elif остаются, как в оригинале)

    # --- Обработка остальных callback'ов (оставим как заглушку)
    # Все остальные ветки (features_weather и т.д.) — без изменений
    # Можно оставить как в старом коде, я их не трогал — они не в теме

    # Если нужно — вставь сюда остальные обработчики


# --- Регистрация ---
def setup(application):
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(
        CallbackQueryHandler(
            handle_menu_callbacks,
            pattern=r"^menu_|^profile_|^features_|^premium_|^settings_"
        )
    )
