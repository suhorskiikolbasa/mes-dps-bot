import sqlite3
import os
from datetime import datetime

DB_PATH = 'economy.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    conn = get_connection()
    c = conn.cursor()

    # Таблица балансов
    c.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            balance INTEGER DEFAULT 0,
            last_daily TEXT DEFAULT NULL
        )
    ''')

    # Таблица логов транзакций
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT,
            timestamp TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def get_balance(user_id: int, guild_id: int) -> int:
    """Получить баланс пользователя"""
    from config import START_BALANCE
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT balance FROM balances WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    row = c.fetchone()
    conn.close()
    if row is None:
        set_balance(user_id, guild_id, START_BALANCE)
        return START_BALANCE
    return row['balance']

def set_balance(user_id: int, guild_id: int, amount: int):
    """Установить баланс пользователя"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO balances (user_id, guild_id, balance)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance=excluded.balance
    ''', (user_id, guild_id, max(0, amount)))
    conn.commit()
    conn.close()

def add_balance(user_id: int, guild_id: int, amount: int) -> int:
    """Добавить деньги пользователю, вернуть новый баланс"""
    current = get_balance(user_id, guild_id)
    new_balance = current + amount
    set_balance(user_id, guild_id, new_balance)
    return new_balance

def remove_balance(user_id: int, guild_id: int, amount: int) -> tuple:
    """Снять деньги. Возвращает (успех, новый_баланс)"""
    current = get_balance(user_id, guild_id)
    if current < amount:
        return False, current
    new_balance = current - amount
    set_balance(user_id, guild_id, new_balance)
    return True, new_balance

def get_last_daily(user_id: int, guild_id: int):
    """Получить время последней ежедневной выплаты"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT last_daily FROM balances WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    row = c.fetchone()
    conn.close()
    if row and row['last_daily']:
        return datetime.fromisoformat(row['last_daily'])
    return None

def set_last_daily(user_id: int, guild_id: int):
    """Установить время последней ежедневной выплаты"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO balances (user_id, guild_id, balance, last_daily)
        VALUES (?, ?, 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_daily=excluded.last_daily
    ''', (user_id, guild_id, now))
    conn.commit()
    conn.close()

def log_transaction(user_id: int, guild_id: int, action: str, amount: int, description: str = ''):
    """Записать транзакцию в журнал"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (user_id, guild_id, action, amount, description, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, guild_id, action, amount, description, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_transactions(guild_id: int, limit: int = 20):
    """Получить последние транзакции"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM transactions WHERE guild_id=?
        ORDER BY timestamp DESC LIMIT ?
    ''', (guild_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_top_balances(guild_id: int, limit: int = 10):
    """Топ богатейших пользователей"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT user_id, balance FROM balances
        WHERE guild_id=? ORDER BY balance DESC LIMIT ?
    ''', (guild_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows
