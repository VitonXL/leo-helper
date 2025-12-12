# bot/commands/admin.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime, date
from bot.database import (
    get_user_count, get_premium_count, get_today_joined_count,
    get_user, set_premium, log_action, get_db
)
import os

# Получаем список админов
ADMIN_IDS = set(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else set()

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели.")
        return

    # Статистика
    total_users = get_user_count()
    premium_users = get_premium_count()
    today_joined = get_today_joined_count()

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🎁 Выдать премиум", callback_data="admin_grant")],
        [InlineKeyboardButton("📣 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_find_user")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = f"""
🔐 *Админ-панель*  
Привет, админ!  

👥 Всего пользователей: *{total_users}*  
💎 Премиум: *{premium_users}*  
🆕 Заходили сегодня: *{today_joined}*

Выберите действие:
    """.strip()

    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return

    data = query.data

    if data == "admin_stats":
        total = get_user_count()
        premium = get_premium_count()
        today = get_today_joined_count()
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        msg = f"""
📈 *Статистика бота*  
Обновлено: `{now}`

👥 Всего пользователей: `{total}`
💎 Премиум: `{premium}`
🆕 Сегодня: `{today}`
        """.strip()

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        await query.answer()

    elif data == "admin_grant":
        await query.message.reply_text("Введите ID пользователя и количество дней (пример: `123456789 30`)")

        context.user_data['awaiting_grant'] = True
        await query.answer()

    elif data == "admin_broadcast":
        await query.message.reply_text("Введите сообщение для рассылки (поддерживается Markdown)")

        context.user_data['awaiting_broadcast'] = True
        await query.answer()

    elif data == "admin_find_user":
        await query.message.reply_text("Введите ID пользователя для поиска")

        context.user_data['awaiting_user_id'] = True
        await query.answer()

    elif data == "admin_refresh":
        await admin_panel(update, context)
        await query.answer()

    elif data == "admin_back":
        await admin_panel(update, context)
        await query.answer()


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    text = update.message.text.strip()

    # Выдача премиума
    if context.user_data.get('awaiting_grant'):
        try:
            parts = text.split()
            target_id = int(parts[0])
            days = int(parts[1]) if len(parts) > 1 else 30

            target_user = get_user(target_id)
            if not target_user:
                await update.message.reply_text("❌ Пользователь не найден.")
                return

            set_premium(target_id, days=days)
            await update.message.reply_text(f"✅ Пользователю {target_id} выдан премиум на {days} дней.")

            # Уведомление пользователю
            try:
                await context.bot.send_message(
                    target_id,
                    f"🎉 Вам выдан премиум-доступ на {days} дней от администратора!"
                )
            except:
                pass

            log_action(user_id, "admin_grant_premium", f"to={target_id}, days={days}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            context.user_data.clear()

    # Рассылка
    elif context.user_data.get('awaiting_broadcast'):
        await _send_broadcast(update, context, text)
        context.user_data.clear()

    # Поиск пользователя
    elif context.user_data.get('awaiting_user_id'):
        try:
            target_id = int(text)
            user = get_user(target_id)
            if not user:
                await update.message.reply_text("❌ Пользователь не найден.")
                return

            expire = user['premium_expire'].strftime("%d.%m.%Y %H:%M") if user['premium_expire'] else "нет"
            joined = user['joined_at'].strftime("%d.%m.%Y")

            msg = f"""
🔍 *Информация о пользователе* `{target_id}`

👤 Имя: {user['first_name']}
🌐 Username: @{user['username']} 
📅 Зарегистрирован: {joined}
💎 Премиум: {'✅ Да (до ' + expire + ')' if user['is_premium'] else '❌ Нет'}
🆔 ID: `{target_id}`
            """.strip()

            keyboard = [
                [InlineKeyboardButton("🎁 Выдать премиум", callback_data=f"grant_{target_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
            ]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ Неверный ID.")
        finally:
            context.user_data.clear()


async def _send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await update.message.reply_text("📤 Рассылка начата...")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row['user_id'] for row in cursor.fetchall()]
    conn.close()

    success = 0
    blocked = 0

    for uid in user_ids:
        try:
            await context.bot.send_message(uid, text, parse_mode='Markdown', disable_web_page_preview=False)
            success += 1
        except Exception as e:
            if "blocked" in str(e) or "kicked" in str(e):
                blocked += 1
        await asyncio.sleep(0.05)  # чтобы не превысить лимиты Telegram

    await update.message.reply_text(f"✅ Рассылка завершена!\n\n📬 Отправлено: {success}\n🚫 Заблокировали бота: {blocked}")
    log_action(update.effective_user.id, "admin_broadcast", f"to={len(user_ids)} users")


# Подключаем в bot.py
def register_admin_handlers(app):
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^grant_"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^back_to_admin$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
