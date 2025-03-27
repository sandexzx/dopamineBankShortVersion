import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from handlers import register_handlers, shutdown_timers
import database

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

async def close_all_sessions():
    """Закрываем все активные сессии aiohttp"""
    sessions = [session for task in asyncio.all_tasks() 
               for session in [getattr(task, '_session', None)] 
               if session is not None]
    
    for session in sessions:
        if not session.closed:
            await session.close()
    
    # Даем время на закрытие соединений
    await asyncio.sleep(0.25)

# Инициализируем бота и диспетчер
async def main():
    # Создаем бота с токеном (вставьте свой токен)
    bot = Bot(token="6122819236:AAGTZozyMnGx7sn1vk2fJEgcNOgZbuzA9d8")
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
    
    try:
        await dp.start_polling(bot)
    finally:
        # Закрываем все активные таймеры при завершении
        await shutdown_timers()
        
        # Закрываем все сессии aiohttp
        await close_all_sessions()
        
        # Закрываем сессию бота
        await bot.session.close()
        logging.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())