# bot/instance.py
"""
Глобальное хранилище для доступа к боту и application из других частей проекта.
Инициализируется в bot/main.py при запуске бота.
"""

from typing import Optional
from telegram.ext import Application
from telegram import Bot

# Глобальные переменные — будут инициализированы при запуске бота
application: Optional[Application] = None
bot: Optional[Bot] = None