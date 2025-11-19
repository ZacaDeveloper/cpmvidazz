import telebot
from telebot import types
import sqlite3
import random
import datetime
import time
from threading import Thread
import hashlib
import re
import logging

import sqlite3
import datetime

sqlite3.register_adapter(datetime.datetime, lambda val: val.isoformat())
sqlite3.register_converter("timestamp", lambda val: datetime.datetime.fromisoformat(val.decode()))

sqlite3.connect('CryptoSendXBots.db'),
detect_types=sqlite3.PARSE_DECLTYPES

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = '8278373049:AAFOKaPME7lYdPmPt5NxnYh1whxvW7DtJOU'
ADMINS = [5000091853, 7746658178]
BOT_NAME = "Test"

# Константы
CRYPTO_CREATION_FEE = 100000.0  
TRANSACTION_FEE_RATE = 0.10   
COOLDOWN_TIME = 2  

bot = telebot.TeleBot(TOKEN)

user_cooldowns = {}

class DatabaseManager:
    def __init__(self, db_name='CryptoSendXBots.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 100.0,
            wallet_id TEXT UNIQUE,
            registration_date TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            notifications_enabled INTEGER DEFAULT 1,
            is_banned INTEGER DEFAULT 0,
            last_activity TEXT,
            total_earned REAL DEFAULT 0,
            FOREIGN KEY (referred_by) REFERENCES users (user_id)
        )
        ''')
        
        # Таблица криптовалют
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cryptocurrencies (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price REAL,
            supply INTEGER,
            market_cap REAL,
            creator_id INTEGER,
            created_date TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (creator_id) REFERENCES users (user_id)
        )
        ''')
        
        # Таблица портфелей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            user_id INTEGER,
            crypto_symbol TEXT,
            amount REAL DEFAULT 0,
            PRIMARY KEY (user_id, crypto_symbol),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (crypto_symbol) REFERENCES cryptocurrencies (symbol)
        )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            crypto_symbol TEXT,
            amount REAL,
            price REAL,
            total REAL,
            fee REAL DEFAULT 0,
            date TEXT,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Таблица чеков
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checks (
            code TEXT PRIMARY KEY,
            user_id INTEGER,
            asset_type TEXT,
            crypto_symbol TEXT,
            amount REAL,
            created_date TEXT,
            expires_date TEXT,
            used INTEGER DEFAULT 0,
            used_date TEXT,
            used_by INTEGER,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Таблица счетов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            to_user_id INTEGER,
            asset_type TEXT,
            crypto_symbol TEXT,
            amount REAL,
            description TEXT,
            created_date TEXT,
            expires_date TEXT,
            paid INTEGER DEFAULT 0,
            paid_date TEXT,
            FOREIGN KEY (from_user_id) REFERENCES users (user_id),
            FOREIGN KEY (to_user_id) REFERENCES users (user_id)
        )
        ''')
        
        base_cryptos = [
            ('BTC', 'Bitcoin', '₿', 50000.0, 21000000, 1050000000000, 0, datetime.datetime.now().isoformat()),
            ('ETH', 'Ethereum', 'Ξ', 3000.0, 120000000, 360000000000, 0, datetime.datetime.now().isoformat()),
            ('DOGE', 'Dogecoin', 'Ð', 0.25, 132670764300, 19900614645, 0, datetime.datetime.now().isoformat()),
            ('LTC', 'Litecoin', 'Ł', 70.0, 84000000, 5880000000, 0, datetime.datetime.now().isoformat()),
            ('BNB', 'Binance Coin', 'ß', 3.5, 3000000, 9000000, 0, datetime.datetime.now().isoformat()),
            ('TON', 'Toncoin', '₿', 2.811, 15000000, 45000000, 0, datetime.datetime.now().isoformat()),
            ('XCOIN', 'X Coin', 'X', 2.0, 1000000, 2000000, 0, datetime.datetime.now().isoformat()),
            ('BEBRA', 'Bebra Coin', 'B', 0.2, 600000, 120000, 0, datetime.datetime.now().isoformat()),
            ('SOL', 'Solana', '§', 193.15, 10000000, 20000000000, 0, datetime.datetime.now()),
            ('XRP', 'XRP', 'X', 2.47, 1000000000, 2470000000, 0, datetime.datetime.now()),
            ('NOT', 'Notcoin', '₿', 0.86, 1000000000, 86000000, 0, datetime.datetime.now()),
            ('BRAVE', 'Brave Coin', 'B', 50, 100000000, 5000000000, 0, datetime.datetime.now()),
            ('VeyCoin✅', 'VeyCoin', '§', 8000, 10000000, 8000000000, 0, datetime.datetime.now()),
            ('PENGUCOIN', 'Pengu Coin', '₿', 15, 100000000, 150000000, 0, datetime.datetime.now()),
            ('VENTA✅', 'Venta Coin', 'V', 90.0, 100000000, 9000000000, 0, datetime.datetime.now().isoformat())
        ]
        
        for crypto in base_cryptos:
            cursor.execute('SELECT symbol FROM cryptocurrencies WHERE symbol = ?', (crypto[0],))
            if not cursor.fetchone():
                cursor.execute('''
                INSERT INTO cryptocurrencies (symbol, name, emoji, price, supply, market_cap, creator_id, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', crypto)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

db_manager = DatabaseManager()

class CacheManager:
    def __init__(self):
        self.users_cache = {}
        self.cryptocurrencies_cache = {}
        self.portfolio_cache = {}
        self.last_update = {}
    
    def get_user(self, user_id):
        current_time = time.time()
        if user_id in self.users_cache and current_time - self.last_update.get(f'user_{user_id}', 0) < 60:
            return self.users_cache[user_id]
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user = {
                'user_id': user_data[0],
                'username': user_data[1],
                'first_name': user_data[2],
                'last_name': user_data[3],
                'balance': user_data[4],
                'wallet_id': user_data[5],
                'registration_date': user_data[6],
                'referral_code': user_data[7],
                'referred_by': user_data[8],
                'notifications_enabled': user_data[9],
                'is_banned': user_data[10],
                'last_activity': user_data[11],
                'total_earned': user_data[12]
            }
            self.users_cache[user_id] = user
            self.last_update[f'user_{user_id}'] = current_time
            return user
        return None
    
    def get_all_cryptocurrencies(self):
        current_time = time.time()
        if self.cryptocurrencies_cache and current_time - self.last_update.get('cryptos', 0) < 30:
            return self.cryptocurrencies_cache
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cryptocurrencies WHERE is_active = 1')
        cryptos_data = cursor.fetchall()
        conn.close()
        
        cryptos = {}
        for crypto in cryptos_data:
            cryptos[crypto[0]] = {
                'name': crypto[1],
                'emoji': crypto[2],
                'price': crypto[3],
                'supply': crypto[4],
                'market_cap': crypto[5],
                'creator_id': crypto[6],
                'created_date': crypto[7],
                'is_active': crypto[8]
            }
        
        self.cryptocurrencies_cache = cryptos
        self.last_update['cryptos'] = current_time
        return cryptos
    
    def get_user_portfolio(self, user_id):
        cache_key = f"portfolio_{user_id}"
        current_time = time.time()
        
        if cache_key in self.portfolio_cache and current_time - self.last_update.get(cache_key, 0) < 60:
            return self.portfolio_cache[cache_key]
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT crypto_symbol, amount FROM portfolio WHERE user_id = ?', (user_id,))
        portfolio_data = cursor.fetchall()
        conn.close()
        
        portfolio = {}
        for item in portfolio_data:
            portfolio[item[0]] = item[1]
        
        self.portfolio_cache[cache_key] = portfolio
        self.last_update[cache_key] = current_time
        return portfolio
    
    def invalidate_cache(self, cache_type, key=None):
        if cache_type == 'user' and key:
            if key in self.users_cache:
                del self.users_cache[key]
        elif cache_type == 'portfolio' and key:
            cache_key = f"portfolio_{key}"
            if cache_key in self.portfolio_cache:
                del self.portfolio_cache[cache_key]
        elif cache_type == 'cryptos':
            self.cryptocurrencies_cache = {}
            self.last_update['cryptos'] = 0

cache = CacheManager()

class UserManager:
    @staticmethod
    def create_user(user_id, username, first_name, last_name="", referred_by=None):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        wallet_id = hashlib.md5(f"{user_id}{datetime.datetime.now()}".encode()).hexdigest()[:10].upper()
        
        referral_code = hashlib.md5(f"{user_id}{username}{time.time()}".encode()).hexdigest()[:8].upper()
        
        registration_date = datetime.datetime.now().isoformat()
        last_activity = registration_date
        
        try:
            cursor.execute('''
            INSERT INTO users 
            (user_id, username, first_name, last_name, balance, wallet_id, registration_date, referral_code, referred_by, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, 100.0, wallet_id, registration_date, referral_code, referred_by, last_activity))
            
            conn.commit()
            
            if referred_by:
                UserManager.update_user_balance(referred_by, 10.0)
                UserManager.add_transaction(referred_by, 'REFERRAL_BONUS', 'USD', 10.0, 1.0, 10.0)
                NotificationManager.send_notification(referred_by, f"🎉 Новый реферал! Вам начислено $10.0")
            
            logger.info(f"New user created: {user_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"User already exists: {user_id}")
            return False
        finally:
            conn.close()
            cache.invalidate_cache('user', user_id)
    
    @staticmethod
    def update_user_balance(user_id, amount):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE users SET balance = balance + ?, last_activity = ? WHERE user_id = ?', 
                         (amount, datetime.datetime.now().isoformat(), user_id))
            
            if amount > 0:
                cursor.execute('UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?', 
                             (amount, user_id))
            
            conn.commit()
            cache.invalidate_cache('user', user_id)
            cache.invalidate_cache('portfolio', user_id)
            logger.info(f"Balance updated for user {user_id}: {amount}")
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def update_user_portfolio(user_id, crypto_symbol, amount):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT amount FROM portfolio WHERE user_id = ? AND crypto_symbol = ?', (user_id, crypto_symbol))
            existing = cursor.fetchone()
            
            if existing:
                new_amount = existing[0] + amount
                if new_amount <= 0:
                    cursor.execute('DELETE FROM portfolio WHERE user_id = ? AND crypto_symbol = ?', (user_id, crypto_symbol))
                else:
                    cursor.execute('UPDATE portfolio SET amount = ? WHERE user_id = ? AND crypto_symbol = ?', 
                                  (new_amount, user_id, crypto_symbol))
            else:
                if amount > 0:
                    cursor.execute('INSERT INTO portfolio (user_id, crypto_symbol, amount) VALUES (?, ?, ?)',
                                  (user_id, crypto_symbol, amount))
            
            cursor.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', 
                         (datetime.datetime.now().isoformat(), user_id))
            
            conn.commit()
            cache.invalidate_cache('portfolio', user_id)
            logger.info(f"Portfolio updated for user {user_id}: {crypto_symbol} {amount}")
        except Exception as e:
            logger.error(f"Error updating portfolio for user {user_id}: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def add_transaction(user_id, transaction_type, crypto_symbol, amount, price, total, fee=0, status='completed'):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        date = datetime.datetime.now().isoformat()
        
        try:
            cursor.execute('''
            INSERT INTO transactions (user_id, type, crypto_symbol, amount, price, total, fee, date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, transaction_type, crypto_symbol, amount, price, total, fee, date, status))
            
            conn.commit()
            logger.info(f"Transaction added for user {user_id}: {transaction_type} {crypto_symbol}")
        except Exception as e:
            logger.error(f"Error adding transaction for user {user_id}: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def reset_account(user_id):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            
            cursor.execute('UPDATE users SET balance = 100.0, total_earned = 0 WHERE user_id = ?', (user_id,))
            
            cursor.execute('DELETE FROM portfolio WHERE user_id = ?', (user_id,))
            
            cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            
            cursor.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', 
                         (datetime.datetime.now().isoformat(), user_id))
            
            conn.commit()
            cache.invalidate_cache('user', user_id)
            cache.invalidate_cache('portfolio', user_id)
            logger.info(f"Account reset for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting account for user {user_id}: {e}")
            return False
        finally:
            conn.close()

class CryptoManager:
    @staticmethod
    def update_crypto_price(symbol, new_price):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE cryptocurrencies SET price = ?, market_cap = price * supply WHERE symbol = ?', 
                         (new_price, symbol))
            conn.commit()
            cache.invalidate_cache('cryptos')
            logger.debug(f"Price updated for {symbol}: {new_price}")
        except Exception as e:
            logger.error(f"Error updating price for {symbol}: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def create_cryptocurrency(symbol, name, emoji, price, supply, creator_id):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        created_date = datetime.datetime.now().isoformat()
        market_cap = price * supply
        
        try:
            cursor.execute('''
            INSERT INTO cryptocurrencies (symbol, name, emoji, price, supply, market_cap, creator_id, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, name, emoji, price, supply, market_cap, creator_id, created_date))
            
            conn.commit()
            cache.invalidate_cache('cryptos')
            logger.info(f"New cryptocurrency created: {symbol} by user {creator_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Cryptocurrency already exists: {symbol}")
            return False
        except Exception as e:
            logger.error(f"Error creating cryptocurrency {symbol}: {e}")
            return False
        finally:
            conn.close()

class NotificationManager:
    @staticmethod
    def send_notification(user_id, message):
        user = cache.get_user(user_id)
        if not user or user['is_banned'] or not user['notifications_enabled']:
            return False
        
        try:
            bot.send_message(user_id, f"🔔 {message}")
            logger.info(f"Notification sent to user {user_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to send notification to user {user_id}: {e}")
            return False

class CheckManager:
    @staticmethod
    def create_check(user_id, amount, crypto_symbol=None, description="", expires_hours=24):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        code = hashlib.md5(f"{user_id}{datetime.datetime.now()}{random.random()}".encode()).hexdigest()[:12].upper()
        
        asset_type = 'CRYPTO' if crypto_symbol else 'USD'
        created_date = datetime.datetime.now().isoformat()
        expires_date = (datetime.datetime.now() + datetime.timedelta(hours=expires_hours)).isoformat()
        
        try:
            cursor.execute('''
            INSERT INTO checks (code, user_id, asset_type, crypto_symbol, amount, created_date, expires_date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code, user_id, asset_type, crypto_symbol, amount, created_date, expires_date, description))
            
            conn.commit()
            logger.info(f"Check created: {code} by user {user_id}")
            return code
        except Exception as e:
            logger.error(f"Error creating check for user {user_id}: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def use_check(user_id, code):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM checks WHERE code = ? AND used = 0', (code,))
            check_data = cursor.fetchone()
            
            if not check_data:
                return False, "Чек не найден или уже использован"
            
            expires_date = datetime.datetime.fromisoformat(check_data[6])
            if datetime.datetime.now() > expires_date:
                return False, "Срок действия чека истек"
            
            code, check_user_id, asset_type, crypto_symbol, amount, created_date, expires_date, used, used_date, used_by, description = check_data
            
            if asset_type == 'USD':
                UserManager.update_user_balance(user_id, amount)
                UserManager.add_transaction(user_id, 'CHECK_USD', 'USD', amount, 1.0, amount)
            else:
                UserManager.update_user_portfolio(user_id, crypto_symbol, amount)
                crypto_price = cache.get_all_cryptocurrencies()[crypto_symbol]['price']
                UserManager.add_transaction(user_id, 'CHECK_CRYPTO', crypto_symbol, amount, crypto_price, amount * crypto_price)
            
            used_date = datetime.datetime.now().isoformat()
            cursor.execute('UPDATE checks SET used = 1, used_date = ?, used_by = ? WHERE code = ?', 
                          (used_date, user_id, code))
            
            conn.commit()
            logger.info(f"Check used: {code} by user {user_id}")
            return True, "Чек успешно активирован"
        except Exception as e:
            logger.error(f"Error using check {code}: {e}")
            return False, "Ошибка при активации чека"
        finally:
            conn.close()

class InvoiceManager:
    @staticmethod
    def create_invoice(from_user_id, to_user_id, amount, crypto_symbol=None, description="", expires_hours=24):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        asset_type = 'CRYPTO' if crypto_symbol else 'USD'
        created_date = datetime.datetime.now().isoformat()
        expires_date = (datetime.datetime.now() + datetime.timedelta(hours=expires_hours)).isoformat()
        
        try:
            cursor.execute('''
            INSERT INTO invoices (from_user_id, to_user_id, asset_type, crypto_symbol, amount, description, created_date, expires_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (from_user_id, to_user_id, asset_type, crypto_symbol, amount, description, created_date, expires_date))
            
            invoice_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Invoice created: #{invoice_id} by user {from_user_id}")
            return invoice_id
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def pay_invoice(invoice_id, user_id):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM invoices WHERE id = ? AND paid = 0', (invoice_id,))
            invoice_data = cursor.fetchone()
            
            if not invoice_data:
                return False, "Счет не найден или уже оплачен"
            
            expires_date = datetime.datetime.fromisoformat(invoice_data[8])
            if datetime.datetime.now() > expires_date:
                return False, "Срок действия счета истек"
            
            (inv_id, from_user_id, to_user_id, asset_type, crypto_symbol, amount, 
             description, created_date, expires_date, paid, paid_date) = invoice_data
            
            if to_user_id != user_id:
                return False, "Этот счет предназначен другому пользователю"
            
            user = cache.get_user(user_id)
            
            if asset_type == 'USD':
                if user['balance'] < amount:
                    return False, "Недостаточно средств на балансе"
                
                UserManager.update_user_balance(user_id, -amount)
                UserManager.update_user_balance(from_user_id, amount)
                UserManager.add_transaction(user_id, 'INVOICE_PAYMENT', 'USD', -amount, 1.0, amount)
                UserManager.add_transaction(from_user_id, 'INVOICE_RECEIVED', 'USD', amount, 1.0, amount)
            else:
                portfolio = cache.get_user_portfolio(user_id)
                if crypto_symbol not in portfolio or portfolio[crypto_symbol] < amount:
                    return False, f"Недостаточно {crypto_symbol} в портфеле"
                
                UserManager.update_user_portfolio(user_id, crypto_symbol, -amount)
                UserManager.update_user_portfolio(from_user_id, crypto_symbol, amount)
                crypto_price = cache.get_all_cryptocurrencies()[crypto_symbol]['price']
                total = amount * crypto_price
                UserManager.add_transaction(user_id, 'INVOICE_PAYMENT', crypto_symbol, -amount, crypto_price, total)
                UserManager.add_transaction(from_user_id, 'INVOICE_RECEIVED', crypto_symbol, amount, crypto_price, total)
            
            paid_date = datetime.datetime.now().isoformat()
            cursor.execute('UPDATE invoices SET paid = 1, paid_date = ? WHERE id = ?', (paid_date, invoice_id))
            
            conn.commit()
            logger.info(f"Invoice paid: #{invoice_id} by user {user_id}")
            return True, "Счет успешно оплачен"
        except Exception as e:
            logger.error(f"Error paying invoice #{invoice_id}: {e}")
            return False, "Ошибка при оплате счета"
        finally:
            conn.close()

def check_cooldown(user_id):
    current_time = time.time()
    if user_id in user_cooldowns:
        elapsed_time = current_time - user_cooldowns[user_id]
        if elapsed_time < COOLDOWN_TIME:
            return False, COOLDOWN_TIME - elapsed_time
    user_cooldowns[user_id] = current_time
    return True, 0

def update_crypto_prices():
    logger.info("Starting crypto price update service")
    while True:
        try:
            time.sleep(300)  # каждве 5 мин оьновление цены
            cryptos = cache.get_all_cryptocurrencies()
            for crypto_symbol, crypto_data in cryptos.items():
                volatility = 0.08 if crypto_symbol in ['BTC', 'ETH'] else 0.12
                change = random.uniform(-volatility, volatility)
                new_price = max(0.0001, crypto_data['price'] * (1 + change))
                new_price = round(new_price, 4)
                CryptoManager.update_crypto_price(crypto_symbol, new_price)
            
            logger.debug("Crypto prices updated successfully")
        except Exception as e:
            logger.error(f"Error in price update service: {e}")

price_thread = Thread(target=update_crypto_prices, daemon=True)
price_thread.start()

# кнопачки
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        '👤 Профиль', '📊 Биржа', '🛠 Создать крипту',
        '🏆 Топ пользователей', '📰 Новости', '💸 Переводы',
        '⚙️ Настройки'
    ]
    keyboard.add(*buttons[:4])
    keyboard.add(*buttons[4:])
    return keyboard

# ===============================
# 📜 СИСТЕМА ЛОГОВ (для админов)
# ===============================

def admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        '📊 Статистика', '📢 Рассылка', '🔨 Бан/Разбан',
        '💰 Баланс пользователей', '💎 Изменить баланс',
        '🗑 Удалить крипту', '🔄 Обнулить аккаунт',
        '🧾 Логи',  # ✅ Новая кнопка логов
        '⬅️ Назад'
    ]
    keyboard.add(*buttons[:3])
    keyboard.add(*buttons[3:6])
    keyboard.add(*buttons[6:9])
    return keyboard


@bot.message_handler(func=lambda message: message.text == '🧾 Логи' and message.from_user.id in ADMINS)
def admin_logs(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ['👥 Логи регистраций', '💸 Логи переводов', '⬅️ Назад']
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, "📜 *Выберите тип логов:*", parse_mode='Markdown', reply_markup=keyboard)


# ---------- 👥 Логи регистраций ----------
@bot.message_handler(func=lambda message: message.text == '👥 Логи регистраций' and message.from_user.id in ADMINS)
def registration_logs(message):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, first_name, registration_date
        FROM users
        ORDER BY datetime(registration_date) DESC
        LIMIT 20
    ''')
    users = cursor.fetchall()
    conn.close()

    if not users:
        bot.send_message(message.chat.id, "📭 Нет зарегистрированных пользователей.")
        return

    text = "👥 *Последние регистрации пользователей:*\n\n"
    for i, (user_id, username, first_name, reg_date) in enumerate(users, 1):
        name = username or first_name or f"User {user_id}"
        date = reg_date.split('T')[0] if reg_date else 'N/A'
        time = reg_date.split('T')[1][:5] if 'T' in reg_date else ''
        text += f"{i}. {name} — {date} {time} (ID: {user_id})\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ---------- 💸 Логи переводов ----------
@bot.message_handler(func=lambda message: message.text == '💸 Логи переводов' and message.from_user.id in ADMINS)
def all_transactions_logs(message):
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT t.user_id, u.username, t.type, t.crypto_symbol, t.amount, t.total, t.date
        FROM transactions t
        LEFT JOIN users u ON u.user_id = t.user_id
        ORDER BY datetime(t.date) DESC
        LIMIT 30
    ''')
    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        bot.send_message(message.chat.id, "📭 Логи транзакций пусты.")
        return

    text = "💸 *Последние 30 транзакций всех пользователей:*\n\n"
    for i, (user_id, username, t_type, symbol, amount, total, date) in enumerate(transactions, 1):
        user_display = username or f"User {user_id}"
        emoji = "📈" if amount > 0 else "📉"
        date_str = date.split('T')[0] + " " + date.split('T')[1][:5]
        text += (
            f"{i}. 👤 *{user_display}* (ID: {user_id})\n"
            f"   {emoji} *{t_type}* {symbol or ''}\n"
            f"   {amount:.6f} ({total:.2f}$)\n"
            f"   ⏰ {date_str}\n\n"
        )

    bot.send_message(message.chat.id, text, parse_mode='Markdown')

def profile_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📋 История транзакций", callback_data='transaction_history'),
        types.InlineKeyboardButton("👥 Реферальная система", callback_data='referral_system')
    )
    keyboard.add(
        types.InlineKeyboardButton("🔔 Уведомления", callback_data='notifications'),
        types.InlineKeyboardButton("🔄 Обновить", callback_data='refresh_profile')
    )
    keyboard.add(
        types.InlineKeyboardButton("🗑️ Обнулить аккаунт", callback_data='reset_account')
    )
    return keyboard

def exchange_keyboard():
    cryptos = cache.get_all_cryptocurrencies()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for crypto_symbol, crypto_data in cryptos.items():
        btn = types.InlineKeyboardButton(
            f"{crypto_data['emoji']} {crypto_symbol} - ${crypto_data['price']:.4f}",
            callback_data=f'exchange_{crypto_symbol}'
        )
        buttons.append(btn)
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.add(buttons[i], buttons[i + 1])
        else:
            keyboard.add(buttons[i])
    
    keyboard.add(types.InlineKeyboardButton("🔄 Обновить курсы", callback_data='refresh_exchange'))
    return keyboard

def buy_sell_keyboard(crypto_symbol):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💰 Купить", callback_data=f'buy_{crypto_symbol}'),
        types.InlineKeyboardButton("💵 Продать", callback_data=f'sell_{crypto_symbol}')
    )
    keyboard.add(types.InlineKeyboardButton("📈 Информация", callback_data=f'info_{crypto_symbol}'))
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='back_to_exchange'))
    return keyboard

def transfers_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💸 Отправить крипту", callback_data='send_crypto'),
        types.InlineKeyboardButton("🧾 Создать чек", callback_data='create_check')
    )
    keyboard.add(
        types.InlineKeyboardButton("📝 Создать счет", callback_data='create_invoice'),
        types.InlineKeyboardButton("💰 Активировать чек", callback_data='activate_check')
    )
    keyboard.add(
        types.InlineKeyboardButton("💳 Оплатить счет", callback_data='pay_invoice'),
        types.InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    referred_by = None
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        ref_user = cursor.fetchone()
        if ref_user:
            referred_by = ref_user[0]
        conn.close()
    
    user = cache.get_user(user_id)
    if not user:
        UserManager.create_user(user_id, username, first_name, last_name, referred_by)
        user = cache.get_user(user_id)
    
    welcome_text = f"""
🚀 Добро пожаловать в *{BOT_NAME}*, {first_name}!

*Ваш финансовый портал в мире криптовалют:*
• 📊 Торговля на бирже
• 🛠 Создание собственных монет
• 💸 Мгновенные переводы
• 👥 Реферальная программа
• 🧾 Чеки и счета

*Начальный баланс:* $100.00
*Ваш ID кошелька:* `{user['wallet_id']}`

*⚠️ Внимание:* При продаже криптовалюты взимается комиссия 10%

Используйте кнопки ниже для навигации:
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == '👤 Профиль')
def profile(message):
    # Проверка кулдауна
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    user_id = message.from_user.id
    user = cache.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ Пользователь не найден. Используйте /start")
        return
    
    display_name = user['username'] or f"{user['first_name']} {user['last_name']}".strip() or f"User {user_id}"
    portfolio = cache.get_user_portfolio(user_id)
    
    # Расчет цены портфелz
    portfolio_value = 0
    cryptos = cache.get_all_cryptocurrencies()
    portfolio_items = []
    
    for crypto_symbol, amount in portfolio.items():
        if crypto_symbol in cryptos and amount > 0:
            value = amount * cryptos[crypto_symbol]['price']
            portfolio_value += value
            portfolio_items.append((crypto_symbol, amount, value))
    
    total_wealth = user['balance'] + portfolio_value
    
    portfolio_items.sort(key=lambda x: x[2], reverse=True)
    
    portfolio_text = ""
    for crypto_symbol, amount, value in portfolio_items:
        emoji = cryptos[crypto_symbol]['emoji']
        portfolio_text += f"• {emoji} *{crypto_symbol}*: `{amount:.6f}` (${value:.2f})\n"
    
    if not portfolio_text:
        portfolio_text = "• Портфель пуст\n"
    
    text = f"""
👤 *Профиль пользователя*

*👤 Имя:* {display_name}
*🏷 ID кошелька:* `{user['wallet_id']}`
*🆔 ID пользователя:* `{user_id}`
*📅 Дата регистрации:* {user['registration_date'][:10]}
*⏰ Последняя активность:* {user['last_activity'][:16] if user['last_activity'] else 'N/A'}

*💵 Баланс USD:* `${user['balance']:.2f}`
*📊 Стоимость портфеля:* `${portfolio_value:.2f}`
*💰 Общий капитал:* `${total_wealth:.2f}`
*💎 Всего заработано:* `${user['total_earned']:.2f}`

*💎 Портфолио:*
{portfolio_text}

*⚠️ Комиссия при продаже:* 10%
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=profile_keyboard())

@bot.message_handler(func=lambda message: message.text == '📊 Биржа')
def exchange(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    cryptos = cache.get_all_cryptocurrencies()
    
    text = "📊 *Биржа криптовалют*\n\n*Доступные криптовалюты:*\n"
    
    for crypto_symbol, crypto_data in cryptos.items():
        change_emoji = "📈" if crypto_data['price'] > 0 else "📉"
        text += f"{crypto_data['emoji']} *{crypto_symbol}* - `${crypto_data['price']:.4f}` {change_emoji}\n"
    
    text += "\n*⚠️ Внимание:* При продаже криптовалюты взимается комиссия 10%\n\nВыберите криптовалюту для торговли:"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=exchange_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('exchange_'))
def exchange_action(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    crypto_symbol = call.data.split('_')[1]
    user_id = call.from_user.id
    user = cache.get_user(user_id)
    cryptos = cache.get_all_cryptocurrencies()
    
    if not user:
        bot.send_message(call.message.chat.id, "❌ Вас нет в базе данных, пожалуйста напишите /start и повторите попытку.")
        return
    
    if crypto_symbol not in cryptos:
        bot.answer_callback_query(call.id, "❌ Криптовалюта не найдена")
        return
    
    current_price = cryptos[crypto_symbol]['price']
    portfolio = cache.get_user_portfolio(user_id)
    user_amount = portfolio.get(crypto_symbol, 0)
    
    text = f"""
{cryptos[crypto_symbol]['emoji']} *{crypto_symbol} - {cryptos[crypto_symbol]['name']}*

*📈 Текущая цена:* `${current_price:.4f}`
*💵 Ваш баланс:* `${user['balance']:.2f}`
*📊 У вас есть:* `{user_amount:.6f}` {crypto_symbol}
*💰 Общая стоимость:* `${user_amount * current_price:.2f}`

*⚠️ Комиссия при продаже:* 10%

Выберите действие:
"""
    bot.edit_message_text(
        text, 
        call.message.chat.id, 
        call.message.message_id,
        parse_mode='Markdown', 
        reply_markup=buy_sell_keyboard(crypto_symbol)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_crypto(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    crypto_symbol = call.data.split('_')[1]
    msg = bot.send_message(call.message.chat.id, f"💰 Введите сумму в USD для покупки {crypto_symbol}:")
    bot.register_next_step_handler(msg, process_buy, crypto_symbol)

def process_buy(message, crypto_symbol):
    try:
        amount_usd = float(message.text)
        user_id = message.from_user.id
        user = cache.get_user(user_id)
        cryptos = cache.get_all_cryptocurrencies()
        
        if crypto_symbol not in cryptos:
            bot.send_message(message.chat.id, "❌ Криптовалюта не найдена")
            return
        
        if amount_usd <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть положительной")
            return
        
        if amount_usd < 0.01:
            bot.send_message(message.chat.id, "❌ Минимальная сумма покупки: $0.01")
            return
        
        if user['balance'] < amount_usd:
            bot.send_message(message.chat.id, f"❌ Недостаточно средств. Ваш баланс: ${user['balance']:.2f}")
            return
        
        crypto_price = cryptos[crypto_symbol]['price']
        amount_crypto = amount_usd / crypto_price
        
        UserManager.update_user_balance(user_id, -amount_usd)
        UserManager.update_user_portfolio(user_id, crypto_symbol, amount_crypto)
        UserManager.add_transaction(user_id, 'BUY', crypto_symbol, amount_crypto, crypto_price, amount_usd)
        
        bot.send_message(message.chat.id, 
                        f"✅ *Успешная покупка!*\n\n"
                        f"• Куплено: `{amount_crypto:.6f}` {crypto_symbol}\n"
                        f"• Потрачено: `${amount_usd:.2f}`\n"
                        f"• Курс: `${crypto_price:.4f}`\n"
                        f"• Новый баланс: `${user['balance'] - amount_usd:.2f}`",
                        parse_mode='Markdown')
        
        logger.info(f"User {user_id} bought {amount_crypto} {crypto_symbol} for ${amount_usd}")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при покупке")
        logger.error(f"Error in buy process: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sell_'))
def sell_crypto(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    crypto_symbol = call.data.split('_')[1]
    msg = bot.send_message(call.message.chat.id, f"💵 Введите количество {crypto_symbol} для продажи:")
    bot.register_next_step_handler(msg, process_sell, crypto_symbol)

def process_sell(message, crypto_symbol):
    try:
        amount_crypto = float(message.text)
        user_id = message.from_user.id
        user = cache.get_user(user_id)
        cryptos = cache.get_all_cryptocurrencies()
        portfolio = cache.get_user_portfolio(user_id)
        
        if crypto_symbol not in cryptos:
            bot.send_message(message.chat.id, "❌ Криптовалюта не найдена")
            return
        
        if amount_crypto <= 0:
            bot.send_message(message.chat.id, "❌ Количество должно быть положительным")
            return
        
        if crypto_symbol not in portfolio or portfolio[crypto_symbol] < amount_crypto:
            bot.send_message(message.chat.id, f"❌ Недостаточно {crypto_symbol}. У вас есть: {portfolio.get(crypto_symbol, 0):.6f}")
            return
        
        crypto_price = cryptos[crypto_symbol]['price']
        amount_usd = amount_crypto * crypto_price
        
      # Расчет комки
        fee = amount_usd * TRANSACTION_FEE_RATE
        amount_after_fee = amount_usd - fee
        
        UserManager.update_user_balance(user_id, amount_after_fee)
        UserManager.update_user_portfolio(user_id, crypto_symbol, -amount_crypto)
        UserManager.add_transaction(user_id, 'SELL', crypto_symbol, -amount_crypto, crypto_price, amount_usd, fee)
        
        bot.send_message(message.chat.id, 
                        f"✅ *Успешная продажа!*\n\n"
                        f"• Продано: `{amount_crypto:.6f}` {crypto_symbol}\n"
                        f"• Получено: `${amount_after_fee:.2f}`\n"
                        f"• Комиссия 10%: `${fee:.2f}`\n"
                        f"• Курс: `${crypto_price:.4f}`\n"
                        f"• Новый баланс: `${user['balance'] + amount_after_fee:.2f}`",
                        parse_mode='Markdown')
        
        logger.info(f"User {user_id} sold {amount_crypto} {crypto_symbol} for ${amount_usd} (fee: ${fee})")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при продаже")
        logger.error(f"Error in sell process: {e}")

@bot.message_handler(func=lambda message: message.text == '🛠 Создать крипту')
def create_crypto(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    user_id = message.from_user.id
    user = cache.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ Пользователь не найден")
        return
    
    if user['balance'] < CRYPTO_CREATION_FEE:
        bot.send_message(message.chat.id, 
                        f"❌ Недостаточно средств. Создание криптовалюты стоит ${CRYPTO_CREATION_FEE:.2f}\n"
                        f"Ваш баланс: ${user['balance']:.2f}")
        return
    
    msg = bot.send_message(message.chat.id, 
                          f"🛠 *Создание новой криптовалюты*\n\n"
                          f"*Стоимость создания:* ${CRYPTO_CREATION_FEE:.2f}\n\n"
                          "Введите символ (3-10 символов, только буквы):\n"
                          "*Пример:* MYCOIN",
                          parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_crypto_symbol)

def process_crypto_symbol(message):
    symbol = message.text.strip().upper()
    
    if len(symbol) < 3 or len(symbol) > 10:
        bot.send_message(message.chat.id, "❌ Символ должен содержать от 3 до 10 символов")
        return
    
    if not re.match("^[A-Z]+$", symbol):
        bot.send_message(message.chat.id, "❌ Символ должен содержать только буквы")
        return
    
    cryptos = cache.get_all_cryptocurrencies()
    if symbol in cryptos:
        bot.send_message(message.chat.id, "❌ Криптовалюта с таким символом уже существует")
        return
    
    msg = bot.send_message(message.chat.id, "📝 Введите название криптовалюты (макс 20 символов):")
    bot.register_next_step_handler(msg, process_crypto_name, symbol)

def process_crypto_name(message, symbol):
    name = message.text.strip()
    
    if len(name) > 20:
        bot.send_message(message.chat.id, "❌ Название слишком длинное (макс 20 символов)")
        return
    
    # Список эомдзи для созданнвх криптовалют
    crypto_emojis = ["🌟", "🚀", "💎", "🔥", "⭐", "✨", "🎯", "🏆", "💫", "🎮", "🪙", "®️"]
    emoji = random.choice(crypto_emojis)
    
    msg = bot.send_message(message.chat.id, 
                          f"💰 Введите начальную цену ($0.005- $0.05):\n"
                          f"*Символ:* {symbol}\n"
                          f"*Название:* {name}\n"
                          f"*Эмодзи:* {emoji}",
                          parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_crypto_price, symbol, name, emoji)

def process_crypto_price(message, symbol, name, emoji):
    try:
        price = float(message.text)
        if price < 0.005 or price > 0.05:
            bot.send_message(message.chat.id, "❌ Цена должна быть между $0.05 и $0.005")
            return
        
        msg = bot.send_message(message.chat.id, 
                              f"🔢 Введите общее количество (1,000,000 - 100,000,000):\n"
                              f"*Цена:* ${price:.3f}",
                              parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_crypto_supply, symbol, name, emoji, price)
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")

def process_crypto_supply(message, symbol, name, emoji, price):
    try:
        supply_text = message.text.replace(',', '').replace(' ', '')
        supply = int(supply_text)
        
        if supply < 1000000 or supply > 100000000:
            bot.send_message(message.chat.id, "❌ Количество должно быть между 1,000,000 и 100,000,000")
            return
        
        user_id = message.from_user.id
        
        UserManager.update_user_balance(user_id, -CRYPTO_CREATION_FEE)
        
        success = CryptoManager.create_cryptocurrency(symbol, name, emoji, price, supply, user_id)
        
        if success:
           
            creator_amount = supply * 0.1
            UserManager.update_user_portfolio(user_id, symbol, creator_amount)
            UserManager.add_transaction(user_id, 'CREATE', symbol, creator_amount, price, creator_amount * price)
            
            text = f"""
✅ *Криптовалюта создана успешно!*

{emoji} *{symbol} - {name}*

*💵 Начальная цена:* `${price:.3f}`
*🔢 Общее количество:* `{supply:,}`
*💰 Рыночная капитализация:* `${price * supply:,.2f}`
*🎁 Вам начислено:* `{creator_amount:,.2f}` {symbol}

*💸 Создание стоило:* ${CRYPTO_CREATION_FEE:.2f}
"""
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
                   
            NotificationManager.send_notification(user_id, 
                f"🎉 Вы создали новую криптовалюту {emoji} {symbol}! Вам начислено {creator_amount:,.2f} {symbol}")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при создании криптовалюты")
            
            UserManager.update_user_balance(user_id, CRYPTO_CREATION_FEE)
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")

@bot.message_handler(func=lambda message: message.text == '🏆 Топ пользователей')
def top_users(message):
   
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT user_id, username, first_name, last_name, balance 
    FROM users 
    WHERE is_banned = 0 
    ORDER BY balance DESC 
    LIMIT 10
    ''')
    top_balance = cursor.fetchall()
    
    cursor.execute('''
    SELECT u.user_id, u.username, u.first_name, u.last_name, 
           COALESCE(SUM(p.amount * c.price), 0) + u.balance as total_wealth
    FROM users u
    LEFT JOIN portfolio p ON u.user_id = p.user_id
    LEFT JOIN cryptocurrencies c ON p.crypto_symbol = c.symbol
    WHERE u.is_banned = 0
    GROUP BY u.user_id
    ORDER BY total_wealth DESC
    LIMIT 10
    ''')
    top_wealth = cursor.fetchall()
    
    conn.close()
    
    text = "🏆 *Топ пользователей*\n\n"
    
    text += "*💵 Топ по балансу USD:*\n"
    for i, (user_id, username, first_name, last_name, balance) in enumerate(top_balance, 1):
        display_name = username or f"{first_name} {last_name}".strip() or f"User {user_id}"
        text += f"{i}. {display_name} - `${balance:.2f}`\n"
    
    text += "\n*💰 Топ по общему капиталу:*\n"
    for i, (user_id, username, first_name, last_name, total_wealth) in enumerate(top_wealth, 1):
        display_name = username or f"{first_name} {last_name}".strip() or f"User {user_id}"
        text += f"{i}. {display_name} - `${total_wealth:.2f}`\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📰 Новости')
def news(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    cryptos = cache.get_all_cryptocurrencies()
    
    crypto_list = []
    for symbol, data in cryptos.items():
        crypto_list.append((symbol, data))
    
    crypto_list.sort(key=lambda x: random.uniform(-0.2, 0.2), reverse=True)
    
    text = "📰 *Крипто-новости*\n\n"
    text += "*🚀 Самые растущие сегодня:*\n"
    for i in range(min(3, len(crypto_list))):
        symbol, data = crypto_list[i]
        change = random.uniform(0.05, 0.15)
        text += f"• {data['emoji']} {symbol}: +{change*100:.1f}% (${data['price']:.4f})\n"
    
    text += "\n*📉 Самые падающие сегодня:*\n"
    for i in range(min(3, len(crypto_list))):
        symbol, data = crypto_list[-(i+1)]
        change = random.uniform(-0.12, -0.03)
        text += f"• {data['emoji']} {symbol}: {change*100:.1f}% (${data['price']:.4f})\n"
    
    text += "\n*💡 Совет дня:*\n"
    tips = [
        "Диверсифицируйте свой портфель для снижения рисков",
        "Инвестируйте только то, что можете позволить себе потерять",
        "Изучайте проекты перед инвестированием",
        "Следите за рыночными тенденциями",
        "Рассмотрите долгосрочные инвестиции",
        "Учитывайте комиссию 10% при продаже криптовалюты"
    ]
    text += f"• {random.choice(tips)}"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💸 Переводы')
def transfers(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    text = """
💸 *Система переводов*

Выберите тип операции:
• 💸 *Отправить крипту* - мгновенный перевод криптовалюты другому пользователю
• 🧾 *Создать чек* - генерация чека на получение средств
• 📝 *Создать счет* - выставление счета на оплату
• 💰 *Активировать чек* - получение средств по коду чека
• 💳 *Оплатить счет* - оплата выставленного счета

*⚠️ Внимание:* При продаже криптовалюты через биржу взимается комиссия 10%
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=transfers_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == 'send_crypto')
def send_crypto(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    msg = bot.send_message(call.message.chat.id, 
                          "💸 *Отправка криптовалюты*\n\n"
                          "Введите ID пользователя или @username получателя:",
                          parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_send_crypto_recipient)

def process_send_crypto_recipient(message):
    recipient = message.text.strip()
    msg = bot.send_message(message.chat.id, "Введите символ криптовалюты (например: BTC):")
    bot.register_next_step_handler(msg, process_send_crypto_symbol, recipient)

def process_send_crypto_symbol(message, recipient):
    crypto_symbol = message.text.strip().upper()
    cryptos = cache.get_all_cryptocurrencies()
    
    if crypto_symbol not in cryptos:
        bot.send_message(message.chat.id, "❌ Криптовалюта не найдена")
        return
    
    msg = bot.send_message(message.chat.id, f"Введите количество {crypto_symbol} для отправки:")
    bot.register_next_step_handler(msg, process_send_crypto_amount, recipient, crypto_symbol)

def process_send_crypto_amount(message, recipient, crypto_symbol):
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        portfolio = cache.get_user_portfolio(user_id)
        
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Количество должно быть положительным")
            return
        
        if crypto_symbol not in portfolio or portfolio[crypto_symbol] < amount:
            bot.send_message(message.chat.id, f"❌ Недостаточно {crypto_symbol}. У вас есть: {portfolio.get(crypto_symbol, 0):.6f}")
            return
        
        recipient_id = None
        if recipient.startswith('@'):
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (recipient[1:],))
            result = cursor.fetchone()
            if result:
                recipient_id = result[0]
            conn.close()
        else:
            try:
                recipient_id = int(recipient)
            except ValueError:
                pass
        
        if not recipient_id:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return
        
        recipient_user = cache.get_user(recipient_id)
        if not recipient_user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return
        
        UserManager.update_user_portfolio(user_id, crypto_symbol, -amount)
        UserManager.update_user_portfolio(recipient_id, crypto_symbol, amount)
        
        crypto_price = cache.get_all_cryptocurrencies()[crypto_symbol]['price']
        total_value = amount * crypto_price
        
        UserManager.add_transaction(user_id, 'SEND', crypto_symbol, -amount, crypto_price, total_value)
        UserManager.add_transaction(recipient_id, 'RECEIVE', crypto_symbol, amount, crypto_price, total_value)
        
        bot.send_message(message.chat.id, 
                        f"✅ *Перевод выполнен успешно!*\n\n"
                        f"• Отправлено: `{amount:.6f}` {crypto_symbol}\n"
                        f"• Получатель: {recipient_user.get('username', f'User {recipient_id}')}\n"
                        f"• Стоимость: `${total_value:.2f}`",
                        parse_mode='Markdown')
        
        NotificationManager.send_notification(recipient_id, 
            f"💸 Вы получили {amount:.6f} {crypto_symbol} от пользователя {message.from_user.username or message.from_user.first_name}")
        
        logger.info(f"User {user_id} sent {amount} {crypto_symbol} to user {recipient_id}")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Произошла ошибка при переводе")
        logger.error(f"Error in send crypto process: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'create_check')
def create_check_handler(call):

    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    msg = bot.send_message(call.message.chat.id, 
                          "🧾 *Создание чека*\n\n"
                          "Выберите тип актива:\n"
                          "1. USD - денежный чек\n"
                          "2. CRYPTO - чек на криптовалюту\n\n"
                          "Введите 'USD' или символ криптовалюты:",
                          parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_check_type)

def process_check_type(message):
    asset_type = message.text.strip().upper()
    cryptos = cache.get_all_cryptocurrencies()
    
    if asset_type == 'USD':
        msg = bot.send_message(message.chat.id, "Введите сумму в USD:")
        bot.register_next_step_handler(msg, process_check_amount, 'USD', None)
    elif asset_type in cryptos:
        msg = bot.send_message(message.chat.id, f"Введите количество {asset_type}:")
        bot.register_next_step_handler(msg, process_check_amount, 'CRYPTO', asset_type)
    else:
        bot.send_message(message.chat.id, "❌ Неверный тип актива. Используйте 'USD' или символ криптовалюты")

def process_check_amount(message, asset_type, crypto_symbol):
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть положительной")
            return
        
        if asset_type == 'USD':
            user = cache.get_user(user_id)
            if not user:
                bot.send_message(message.chat.id, "❌ Вас нет в базе данных, пожалуйста напишите /start и повторите попытку.")
                return
            if user['balance'] < amount:
                bot.send_message(message.chat.id, f"❌ Недостаточно средств. Ваш баланс: ${user['balance']:.2f}")
                return
        else:
            portfolio = cache.get_user_portfolio(user_id)
            if crypto_symbol not in portfolio or portfolio[crypto_symbol] < amount:
                bot.send_message(message.chat.id, f"❌ Недостаточно {crypto_symbol}. У вас есть: {portfolio.get(crypto_symbol, 0):.6f}")
                return

        # === Добавляем кнопку "Пропустить" ===
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        skip_button = types.KeyboardButton("⏭ Пропустить")
        keyboard.add(skip_button)

        msg = bot.send_message(
            message.chat.id,
            "Введите описание чека (необязательно):",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, process_check_description, asset_type, crypto_symbol, amount)
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")


def process_check_description(message, asset_type, crypto_symbol, amount):
    description = message.text.strip()
    if description == "⏭ Пропустить":
        description = ""  # пользователь нажал "Пропустить"

    user_id = message.from_user.id

    code = CheckManager.create_check(user_id, amount, crypto_symbol, description)
    
    # Убираем клавиатуру после ответа
    remove_keyboard = types.ReplyKeyboardRemove()
    
    if code:
        if asset_type == 'USD':
            UserManager.update_user_balance(user_id, -amount)
        else:
            UserManager.update_user_portfolio(user_id, crypto_symbol, -amount)
        
        asset_display = f"${amount:.2f}" if asset_type == 'USD' else f"{amount:.6f} {crypto_symbol}"
        
        text = f"""
✅ *Чек создан успешно!*

*💰 Сумма:* {asset_display}
*📝 Описание:* {description or 'Нет'}
*🔢 Код чека:* {code}
*⏰ Срок действия:* 24 часа

*📤 Для активации чека получатель должен:*
1. Перейти в раздел "💸 Переводы"
2. Выбрать "💰 Активировать чек"
3. Ввести код: `{code}`
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=remove_keyboard)
    else:
        bot.send_message(message.chat.id, "❌ Ошибка при создании чека", reply_markup=remove_keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'activate_check')
def activate_check_handler(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    msg = bot.send_message(call.message.chat.id, "💰 Введите код чека для активации:")
    bot.register_next_step_handler(msg, process_activate_check)

def process_activate_check(message):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    
    success, message_text = CheckManager.use_check(user_id, code)
    
    if success:
        bot.send_message(message.chat.id, f"✅ {message_text}")
    else:
        bot.send_message(message.chat.id, f"❌ {message_text}")

@bot.callback_query_handler(func=lambda call: call.data == 'create_invoice')
def create_invoice_handler(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    msg = bot.send_message(call.message.chat.id, 
                          "📝 *Создание счета*\n\n"
                          "Введите ID пользователя или @username для выставления счета:",
                          parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_invoice_recipient)

def process_invoice_recipient(message):
    recipient = message.text.strip()
    msg = bot.send_message(message.chat.id, "Выберите тип актива (USD или символ криптовалюты):")
    bot.register_next_step_handler(msg, process_invoice_type, recipient)

def process_invoice_type(message, recipient):
    asset_type = message.text.strip().upper()
    cryptos = cache.get_all_cryptocurrencies()
    
    if asset_type != 'USD' and asset_type not in cryptos:
        bot.send_message(message.chat.id, "❌ Неверный тип актива")
        return
    
    msg = bot.send_message(message.chat.id, f"Введите сумму {asset_type}:")
    bot.register_next_step_handler(msg, process_invoice_amount, recipient, asset_type)

def process_invoice_amount(message, recipient, asset_type):
    try:
        amount = float(message.text)
        
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть положительной")
            return

        # === Добавляем кнопку "Пропустить" ===
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        skip_button = types.KeyboardButton("⏭ Пропустить")
        keyboard.add(skip_button)

        msg = bot.send_message(
            message.chat.id,
            "Введите описание счета (необязательно):",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, process_invoice_description, recipient, asset_type, amount)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")


def process_invoice_description(message, recipient, asset_type, amount):
    description = message.text.strip()
    if description == "⏭ Пропустить":
        description = ""  # пользователь нажал "Пропустить"

    remove_keyboard = types.ReplyKeyboardRemove()

    user_id = message.from_user.id
    
    recipient_id = None
    if recipient.startswith('@'):
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE username = ?', (recipient[1:],))
        result = cursor.fetchone()
        if result:
            recipient_id = result[0]
        conn.close()
    else:
        try:
            recipient_id = int(recipient)
        except ValueError:
            pass
    
    if not recipient_id:
        bot.send_message(message.chat.id, "❌ Пользователь не найден", reply_markup=remove_keyboard)
        return
    
    recipient_user = cache.get_user(recipient_id)
    if not recipient_user:
        bot.send_message(message.chat.id, "❌ Пользователь не найден", reply_markup=remove_keyboard)
        return
    
    crypto_symbol = None if asset_type == 'USD' else asset_type
    invoice_id = InvoiceManager.create_invoice(user_id, recipient_id, amount, crypto_symbol, description)
    
    if invoice_id:
        asset_display = f"${amount:.2f}" if asset_type == 'USD' else f"{amount:.6f} {asset_type}"
        
        text = f"""
✅ *Счет создан успешно!*

*💰 Сумма:* {asset_display}
*👤 Для:* {recipient_user.get('username', f'User {recipient_id}')}
*📝 Описание:* {description or 'Нет'}
*🔢 Номер счета:* `{invoice_id}`
*⏰ Срок действия:* 24 часа

*📤 Для оплаты счета получатель должен:*
1. Перейти в раздел "💸 Переводы"
2. Выбрать "💳 Оплатить счет"
3. Ввести номер: {invoice_id}
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=remove_keyboard)
        
        NotificationManager.send_notification(
            recipient_id,
            f"📝 Вам выставлен счет #{invoice_id} на {asset_display} от пользователя {message.from_user.username or message.from_user.first_name}"
        )
    else:
        bot.send_message(message.chat.id, "❌ Ошибка при создании счета", reply_markup=remove_keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'pay_invoice')
def pay_invoice_handler(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    msg = bot.send_message(call.message.chat.id, "💳 Введите номер счета для оплаты:")
    bot.register_next_step_handler(msg, process_pay_invoice)

def process_pay_invoice(message):
    try:
        invoice_id = int(message.text)
        user_id = message.from_user.id
        
        success, message_text = InvoiceManager.pay_invoice(invoice_id, user_id)
        
        if success:
            bot.send_message(message.chat.id, f"✅ {message_text}")
        else:
            bot.send_message(message.chat.id, f"❌ {message_text}")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный номер счета")

@bot.message_handler(func=lambda message: message.text == '⚙️ Настройки')
def settings(message):
   
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    user_id = message.from_user.id
    user = cache.get_user(user_id)
    
    if user_id in ADMINS:
        bot.send_message(message.chat.id, "⚙️ *Админ панель*", parse_mode='Markdown', reply_markup=admin_keyboard())
    else:
        status = "включены" if user['notifications_enabled'] else "отключены"
        text = f"""
⚙️ *Настройки*

*🔔 Уведомления:* {status}
*🏷 ID кошелька:* `{user['wallet_id']}`
*👥 Реферальный код:* `{user['referral_code']}`

*⚠️ Комиссия при продаже:* 10%
*💰 Создание крипты:* ${CRYPTO_CREATION_FEE:.2f}

Используйте кнопки в профиле для изменения настроек.
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')

# АДМИН ПАНЕЛЬ
@bot.message_handler(func=lambda message: message.text == '📊 Статистика' and message.from_user.id in ADMINS)
def admin_stats(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
    banned_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM cryptocurrencies')
    total_cryptos = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM transactions')
    total_transactions = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(fee) FROM transactions')
    total_fees = cursor.fetchone()[0] or 0
    
    conn.close()
    
    text = f"""
📊 *Статистика бота*

*👥 Пользователи:*
• Всего: {total_users}
• Заблокированы: {banned_users}
• Активных: {total_users - banned_users}

*💎 Криптовалюты:*
• Всего: {total_cryptos}

*💰 Финансы:*
• Общий баланс: ${total_balance:.2f}
• Всего транзакций: {total_transactions}
• Сумма комиссий: ${total_fees:.2f}

*🔄 Последние действия:*
• Обновление цен: Активно
• Бот работает: ✅
• Комиссия: 10%
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📢 Рассылка' and message.from_user.id in ADMINS)
def admin_broadcast(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    msg = bot.send_message(message.chat.id, "📢 Введите сообщение для рассылки:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    broadcast_text = message.text
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 0 AND notifications_enabled = 1')
    users = cursor.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    
    for (user_id,) in users:
        try:
            bot.send_message(user_id, f"📢 *Сообщение от администратора:*\n\n{broadcast_text}", parse_mode='Markdown')
            sent += 1
        except:
            failed += 1
    
    bot.send_message(message.chat.id, 
                    f"✅ *Рассылка завершена*\n\n"
                    f"• Отправлено: {sent}\n"
                    f"• Не доставлено: {failed}")

@bot.message_handler(func=lambda message: message.text == '🔨 Бан/Разбан' and message.from_user.id in ADMINS)
def admin_ban(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    msg = bot.send_message(message.chat.id, "🔨 Введите ID пользователя для бана/разбана:")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    try:
        user_id = int(message.text)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return
        
        is_banned = result[0]
        new_status = 0 if is_banned else 1
        action = "разбанен" if is_banned else "забанен"
        
        cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (new_status, user_id))
        conn.commit()
        conn.close()
        
        cache.invalidate_cache('user', user_id)
        
        bot.send_message(message.chat.id, f"✅ Пользователь {user_id} {action}")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный ID пользователя")

@bot.message_handler(func=lambda message: message.text == '💰 Баланс пользователей' and message.from_user.id in ADMINS)
def admin_balance(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT user_id, username, first_name, last_name, balance 
    FROM users 
    ORDER BY balance DESC 
    LIMIT 20
    ''')
    users = cursor.fetchall()
    conn.close()
    
    text = "💰 *Топ пользователей по балансу*\n\n"
    
    for i, (user_id, username, first_name, last_name, balance) in enumerate(users, 1):
        display_name = username or f"{first_name} {last_name}".strip() or f"User {user_id}"
        text += f"{i}. {display_name} - `${balance:.2f}`\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💎 Изменить баланс' and message.from_user.id in ADMINS)
def admin_change_balance(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    msg = bot.send_message(message.chat.id, "💎 Введите ID пользователя:")
    bot.register_next_step_handler(msg, process_change_balance_user)

def process_change_balance_user(message):
    try:
        user_id = int(message.text)
        user = cache.get_user(user_id)
        
        if not user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return
        
        msg = bot.send_message(message.chat.id, f"Пользователь: {user.get('username', f'User {user_id}')}\nВведите сумму изменения (+ для пополнения, - для списания):")
        bot.register_next_step_handler(msg, process_change_balance_amount, user_id)
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный ID пользователя")

def process_change_balance_amount(message, user_id):
    try:
        amount = float(message.text)
        UserManager.update_user_balance(user_id, amount)
        
        action = "пополнен" if amount > 0 else "списан"
        bot.send_message(message.chat.id, f"✅ Баланс пользователя {user_id} {action} на ${abs(amount):.2f}")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число")

@bot.message_handler(func=lambda message: message.text == '🗑 Удалить крипту' and message.from_user.id in ADMINS)
def admin_delete_crypto(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    cryptos = cache.get_all_cryptocurrencies()
    
    text = "🗑 *Удаление криптовалюты*\n\nДоступные криптовалюты:\n"
    for symbol, data in cryptos.items():
        text += f"• {data['emoji']} {symbol} - {data['name']}\n"
    
    text += "\nВведите символ криптовалюты для удаления:"
    
    msg = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_crypto)

def process_delete_crypto(message):
    symbol = message.text.strip().upper()
    cryptos = cache.get_all_cryptocurrencies()
    
    if symbol not in cryptos:
        bot.send_message(message.chat.id, "❌ Криптовалюта не найдена")
        return
    
    if symbol in ['BTC', 'ETH', 'DOGE', 'LTC', 'BNB', 'TON', 'SOL', 'XPR', 'NOT', 'BRAVE', 'VENTA✅']:
        bot.send_message(message.chat.id, "❌ Нельзя удалить базовые криптовалюты")
        return
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        
        cursor.execute('UPDATE cryptocurrencies SET is_active = 0 WHERE symbol = ?', (symbol,))
        conn.commit()
        
        cache.invalidate_cache('cryptos')
        
        bot.send_message(message.chat.id, f"✅ Криптовалюта {symbol} удалена")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при удалении: {e}")
    finally:
        conn.close()

@bot.message_handler(func=lambda message: message.text == '🔄 Обнулить аккаунт' and message.from_user.id in ADMINS)
def admin_reset_account(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    msg = bot.send_message(message.chat.id, "🔄 Введите ID пользователя для обнуления аккаунта:")
    bot.register_next_step_handler(msg, process_reset_account)

def process_reset_account(message):
    try:
        user_id = int(message.text)
        user = cache.get_user(user_id)
        
        if not user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return
        
        success = UserManager.reset_account(user_id)
        
        if success:
            bot.send_message(message.chat.id, f"✅ Аккаунт пользователя {user_id} успешно обнулен")
           
            NotificationManager.send_notification(user_id, 
                "🔄 Ваш аккаунт был обнулен администратором. Баланс восстановлен до $100.00")
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка при обнулении аккаунта пользователя {user_id}")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный ID пользователя")

@bot.message_handler(func=lambda message: message.text == '⬅️ Назад' and message.from_user.id in ADMINS)
def admin_back(message):
    
    cooldown_ok, remaining = check_cooldown(message.from_user.id)
    if not cooldown_ok:
        bot.send_message(message.chat.id, f"⏳ Подождите {remaining:.1f} секунд перед следующим действием")
        return
        
    bot.send_message(message.chat.id, "⬅️ Возврат в главное меню", reply_markup=main_keyboard())


@bot.callback_query_handler(func=lambda call: call.data == 'transaction_history')
def transaction_history(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    user_id = call.from_user.id
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT type, crypto_symbol, amount, price, total, fee, date 
    FROM transactions 
    WHERE user_id = ? 
    ORDER BY date DESC 
    LIMIT 10
    ''', (user_id,))
    
    transactions = cursor.fetchall()
    conn.close()
    
    text = "📋 *История транзакций*\n\n"
    
    if not transactions:
        text += "История транзакций пуста"
    else:
        for i, (t_type, crypto_symbol, amount, price, total, fee, date) in enumerate(transactions, 1):
            emoji = "📈" if amount > 0 else "📉"
            action = "Покупка" if t_type == 'BUY' else "Продажа" if t_type == 'SELL' else t_type
            text += f"{i}. {emoji} {action} {crypto_symbol}\n"
            text += f"   Сумма: {amount:.6f} | Цена: ${price:.4f}\n"
            if fee > 0:
                text += f"   Комиссия: ${fee:.2f} | "
            text += f"Всего: ${total:.2f} | {date[:16]}\n\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'referral_system')
def referral_system(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    user_id = call.from_user.id
    user = cache.get_user(user_id)
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,))
    referral_count = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COALESCE(SUM(total), 0) 
    FROM transactions 
    WHERE user_id = ? AND type = 'REFERRAL_BONUS'
    ''', (user_id,))
    
    referral_earnings = cursor.fetchone()[0]
    conn.close()
    
    referral_link = f"https://t.me/{BOT_NAME}?start={user['referral_code']}"
    
    text = f"""
👥 *Реферальная система*

*🔗 Ваша реферальная ссылка:*
`{referral_link}`

*📊 Статистика:*
• Приглашено пользователей: {referral_count}
• Заработано с рефералов: ${referral_earnings:.2f}

*💰 Награды:*
• За каждого приглашенного: $10.00
• Реферал получает: $100.00

*📣 Поделитесь ссылкой с друзьями и зарабатывайте!*
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'notifications')
def toggle_notifications(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    user_id = call.from_user.id
    user = cache.get_user(user_id)
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    new_status = 0 if user['notifications_enabled'] else 1
    cursor.execute('UPDATE users SET notifications_enabled = ? WHERE user_id = ?', (new_status, user_id))
    conn.commit()
    conn.close()
    
    cache.invalidate_cache('user', user_id)
    
    status = "включены" if new_status else "отключены"
    bot.answer_callback_query(call.id, f"🔔 Уведомления {status}")

@bot.callback_query_handler(func=lambda call: call.data == 'refresh_profile')
def refresh_profile(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    user_id = call.from_user.id
    user = cache.get_user(user_id)
    
    if user:
        cache.invalidate_cache('user', user_id)
        cache.invalidate_cache('portfolio', user_id)
        bot.answer_callback_query(call.id, "✅ Профиль обновлен")
        profile(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка обновления")

@bot.callback_query_handler(func=lambda call: call.data == 'reset_account')
def reset_account(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    user_id = call.from_user.id
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ Да, обнулить", callback_data='confirm_reset'),
        types.InlineKeyboardButton("❌ Отмена", callback_data='cancel_reset')
    )
    
    bot.edit_message_text(
        "🗑️ *Обнуление аккаунта*\n\n"
        "⚠️ *Внимание!* Это действие:\n"
        "• Сбросит ваш баланс до $100.00\n"
        "• Очистит весь ваш портфель\n"
        "• Удалит историю транзакций\n"
        "• *Действие необратимо!*\n\n"
        "Вы уверены, что хотите обнулить аккаунт?",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'confirm_reset')
def confirm_reset(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    user_id = call.from_user.id
    
    success = UserManager.reset_account(user_id)
    
    if success:
        bot.edit_message_text(
            "✅ *Аккаунт успешно обнулен!*\n\n"
            "• Баланс восстановлен до $100.00\n"
            "• Портфель очищен\n"
            "• История транзакций удалена\n\n"
            "Можете начать с чистого листа!",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        profile(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка при обнулении аккаунта")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_reset')
def cancel_reset(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    bot.edit_message_text(
        "❌ *Обнуление отменено*\n\n"
        "Ваши данные сохранены.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'refresh_exchange')
def refresh_exchange(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    cache.invalidate_cache('cryptos')
    bot.answer_callback_query(call.id, "✅ Курсы обновлены")
    exchange(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('info_'))
def crypto_info(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    crypto_symbol = call.data.split('_')[1]
    cryptos = cache.get_all_cryptocurrencies()
    
    if crypto_symbol not in cryptos:
        bot.answer_callback_query(call.id, "❌ Криптовалюта не найдена")
        return
    
    crypto_data = cryptos[crypto_symbol]
    
    text = f"""
{crypto_data['emoji']} *{crypto_symbol} - {crypto_data['name']}*

*💵 Цена:* `${crypto_data['price']:.4f}`
*🔢 Общее количество:* `{crypto_data['supply']:,}`
*💰 Рыночная капитализация:* `${crypto_data['market_cap']:,.2f}`
*📅 Дата создания:* {crypto_data['created_date'][:10]}

*📊 Статистика:*
• Волатильность: {'Высокая' if crypto_symbol not in ['BTC', 'ETH'] else 'Средняя'}
• Статус: {'Активна' if crypto_data['is_active'] else 'Неактивна'}
• Комиссия при продаже криптовалют: 10%
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_exchange')
def back_to_exchange(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    exchange(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call):
    
    cooldown_ok, remaining = check_cooldown(call.from_user.id)
    if not cooldown_ok:
        bot.answer_callback_query(call.id, f"⏳ Подождите {remaining:.1f} секунд", show_alert=True)
        return
        
    bot.edit_message_text("Возврат в главное меню", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Главное меню", reply_markup=main_keyboard())

# Запуск бота
if __name__ == '__main__':
    logger.info(f"Starting {BOT_NAME}...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")