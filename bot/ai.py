# bot/ai.py
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import os

GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
if not GIGACHAT_CREDENTIALS:
    raise ValueError("GIGACHAT_CREDENTIALS не найден в переменных")

gigachat = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    auth_url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
    verify_ssl_certs=False
)

user_history = {}

def get_user_history(user_id: int, clear=False):
    if clear:
        user_history.pop(user_id, None)
    if user_id not in user_history:
        user_history[user_id] = []
    return user_history[user_id]

async def send_to_gigachat(user_id: int, prompt: str) -> str:
    try:
        history = get_user_history(user_id)
        history.append(Messages(role=MessagesRole.USER, content=prompt))
        if len(history) > 10:
            history = history[-10:]
        chat = Chat(messages=history)
        response = gigachat.chat(chat)
        answer = response.choices[0].message.content
        history.append(Messages(role=MessagesRole.ASSISTANT, content=answer))
        return answer
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"
