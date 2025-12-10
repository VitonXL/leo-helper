import os
import threading
from bot.bot import main as start_bot
from virus_total_proxy import app as flask_app

def run_flask():
    port = int(os.getenv('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Запускаем Flask в потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Запускаем бота
    start_bot()
