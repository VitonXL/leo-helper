# bot/ton_checker.py
import httpx
import logging
from datetime import datetime
from bot.database import db

TON_API = "https://toncenter.com/api/v3"

async def check_pending_payments(context: object):
    """Проверяет входящие платежи"""
    wallet = "UQCAjhZZOSxbEUB84daLpOXBPkQIWy3oB-fWoTztKdAZFDLQ"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TON_API}/getTransactions",
                params={"address": wallet, "limit": 50},
                timeout=15
            )
            if response.status_code != 200:
                logging.error(f"❌ Ошибка TON API: {response.status_code}")
                return

            transactions = response.json().get("transactions", [])
            for tx in transactions:
                try:
                    tx_id = tx["transaction_id"]["hash"]
                    if db.is_payment_processed(tx_id):
                        continue

                    # Только входящие
                    if tx["out_msgs"]:
                        continue

                    amount = int(tx["in_msg"]["value"])
                    comment = tx["in_msg"].get("decoded_body", {}).get("comment", "")

                    if amount == 20000000 and comment.startswith("premium:"):
                        user_id = int(comment.split(":")[1])
                        if not db.is_premium(user_id):
                            db.grant_premium(user_id, 30)
                            await notify_user_paid(context, user_id)
                        db.mark_payment_as_processed(tx_id)
                except Exception as e:
                    logging.error(f"❌ Ошибка транзакции: {e}")
    except Exception as e:
        logging.error(f"❌ Ошибка проверки платежей: {e}")

async def notify_user_paid(context, user_id):
    try:
        await context.bot.send_message(
            user_id,
            "🎉 Оплата получена! Вам выдан премиум-доступ на 30 дней.\nСпасибо за поддержку! 💙"
        )
    except Exception as e:
        logging.error(f"❌ Не удалось уведомить {user_id}: {e}")
