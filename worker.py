# worker.py

import os
import threading
from datetime import time
from bot.bot import application
from web.app import app as web_app

def run_web():
    port = int(os.getenv("PORT", 8000))
    web_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Запускаем веб в фоновом потоке
    threading.Thread(target=run_web, daemon=True).start()

    # Запускаем бота
    application.run_polling()
