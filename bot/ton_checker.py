# bot/ton_checker.py
import httpx
import logging
from datetime import datetime
from bot.database import db

# Настройка логов
logger = logging.getLogger(__name__)

# Константы
TON_API_URL = "https://toncenter.com/api/v3"
WALLET_ADDRESS = "UQCAjhZZOSxbEUB84daLpOXBPkQIWy3oB-fWoTztKdAZFDLQ"
EXPECTED_AMOUNT = 20000000  # 0.02 TON в nanotons

async def check_pending_payments(context):
    """
    Проверяет входящие платежи на кошелёк TON.
    Если найден платёж 0.02 TON с комментарием `premium:123456789` — выдаёт премиум.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Получаем последние транзакции
            response = await client.get(
                f"{TON_API_URL}/getTransactions",
                params={"address": WALLET_ADDRESS, "limit": 50},
                timeout=15,
            )

            if response.status_code != 200:
                logger.error(f"❌ Ошибка TonCenter API: {response.status_code} — {response.text}")
                return

            transactions = response.json().get("transactions", [])
            logger.info(f"🔍 Проверено {len(transactions)} транзакций")

            for tx in transactions:
                try:
                    # Извлекаем хеш транзакции
                    tx_hash = tx["transaction_id"]["hash"]

                    # Пропускаем уже обработанные
                    if db.is_payment_processed(tx_hash):
                        continue

                    # Проверяем, что это входящий платеж
                    if tx["out_msgs"]:
                        continue  # Это исходящий платёж — не наш

                    # Получаем сумму и комментарий
                    in_msg = tx.get("in_msg")
                    if not in_msg:
                        continue

                    amount = int(in_msg["value"])
                    body = in_msg.get("decoded_body", {})
                    comment = body.get("comment", "").strip()

                    # Проверяем сумму и формат комментария
                    if amount == EXPECTED_AMOUNT and comment.startswith("premium:"):
                        user_id = int(comment.split(":")[1])

                        # Проверяем, не оплачивал ли уже пользователь
                        if db.is_premium(user_id):
                            logger.info(f"💡 Пользователь {user_id} уже имеет премиум")
                        else:
                            # Выдаём 30 дней
                            db.grant_premium(user_id, 30)
                            logger.info(f"✅ Премиум выдан: {user_id}")

                            # Уведомляем пользователя
                            await context.bot.send_message(
                                user_id,
                                "🎉 Оплата получена! Вам выдан премиум-доступ на 30 дней.\n"
                                "Спасибо за поддержку! 💙"
                            )

                        # Отмечаем как обработанную
                        db.mark_payment_as_processed(tx_hash)

                except Exception as e:
                    logger.error(f"❌ Ошибка при обработке транзакции {tx_hash}: {e}")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при проверке платежей: {e}")


# === Вспомогательная функция для теста (опционально) ===

async def test_ton_connection(context):
    """Тестовое подключение к API TonCenter"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TON_API_URL}/getAddressInformation", params={"address": WALLET_ADDRESS})
            if response.status_code == 200:
                data = response.json()
                balance = int(data.get("balance", 0)) / 1e9  # в TON
                await context.bot.send_message(
                    1799560429,
                    f"🟢 TonCenter: подключение успешно\nБаланс: {balance:.4f} TON"
                )
            else:
                await context.bot.send_message(
                    1799560429,
                    f"🔴 TonCenter: ошибка {response.status_code}"
                )
    except Exception as e:
        await context.bot.send_message(1799560429, f"🔴 Ошибка подключения: {e}")
