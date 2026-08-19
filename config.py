import os
from dotenv import load_dotenv

load_dotenv()

# ── ОСНОВНЫЕ НАСТРОЙКИ ──
TOKEN = os.getenv('DISCORD_TOKEN')

# Название валюты
CURRENCY_NAME = 'рублей'
CURRENCY_SYMBOL = '₽'

# Ежедневная выплата
DAILY_AMOUNT = 500

# Канал логов (название канала)
LOG_CHANNEL_NAME = 'логи-бота'

# Роли администрации (названия ролей)
ADMIN_ROLES = ['Администратор', 'Модератор', 'Командование', 'Начальник']

# Стартовый баланс для новых пользователей
START_BALANCE = 1000

# Кулдаун команд экономики (в секундах)
ECONOMY_COOLDOWN = 5
DAILY_COOLDOWN = 86400  # 24 часа

# Музыка
MAX_VOLUME = 100
DEFAULT_VOLUME = 50
MAX_QUEUE_SIZE = 50
