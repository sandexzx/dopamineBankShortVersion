import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from handlers import register_handlers
import database

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
async def main():
    # Создаем бота с токеном (вставьте свой токен)
    bot = Bot(token="6122819236:AAGZoYhWGxuEjQcXe2z7EqeC9OgusIbU8fE")
    # Создаем диспетчер
    dp = Dispatcher(storage=MemoryStorage())
    
    # Добавляем middleware для обработки callback запросов
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    
    # Инициализируем базу данных
    database.init()
    
    # Регистрируем все обработчики
    register_handlers(dp)
    
    # Удаляем все старые веб-хуки и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())