import logging
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

import keyboards
import database
from datetime import datetime, timedelta
from contextlib import suppress
import asyncio

# Словарь для хранения задач секундомеров для пользователей
active_timers = {}

# Определение состояний FSM
class RewardStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_cost = State()

class EditRewardStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_cost = State()

class SetPointsStates(StatesGroup):
    waiting_for_points = State()

# Создаем роутер
router = Router()

# Функция для регистрации всех обработчиков
def register_handlers(dp):
    dp.include_router(router)

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Получаем или создаем пользователя
    user = database.get_user(message.from_user.id)
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! Это бот Дофаминового Банка.\n"
        f"Здесь ты можешь отслеживать свои задачи и получать за них виртуальные баллы.\n"
        f"У тебя сейчас {user['points']} баллов.",
        reply_markup=keyboards.main_menu()
    )

# Обработчик начала задачи
@router.message(F.text == "🚀 Начать задачу")
async def start_task(message: Message):
    user = database.get_user(message.from_user.id)
    
    # Проверяем, нет ли уже активной задачи
    if user["active_task"]:
        start_time = datetime.fromtimestamp(user["active_task"]["start_time"])
        elapsed = datetime.now() - start_time
        minutes, seconds = divmod(elapsed.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        
        await message.answer(
            f"У тебя уже есть активная задача!\n"
            f"Прошло времени: {time_str}\n"
            f"Для завершения выбери сложность задачи:",
            reply_markup=keyboards.difficulty_menu()
        )
        return
    
    # Начинаем новую задачу
    task = database.start_task(message.from_user.id)
    
    # Отправляем сообщение с секундомером
    timer_message = await message.answer(
        "⏱️ Секундомер: 00:00:00\n💰 Баллы: 0",
        reply_markup=keyboards.timer_control_inline()
    )

    # Запускаем обновление секундомера
    user_id = message.from_user.id
    if user_id in active_timers:
        active_timers[user_id].cancel()

    active_timers[user_id] = asyncio.create_task(
        update_timer(user_id, timer_message.message_id, message.chat.id)
    )

# Словарь для преобразования названий сложности в ключи БД
difficulty_map = {
    "Очень простая": "very_easy",
    "Простая": "easy",
    "Стандартная": "standard",
    "Повышенной сложности": "high",
    "Сложная": "hard",
    "Катастрофическая": "catastrophic"
}

# Обработчик завершения задачи по выбору сложности
@router.message(F.text.in_(difficulty_map.keys()))
async def end_task(message: Message):
    user = database.get_user(message.from_user.id)
    
    # Проверяем, есть ли активная задача
    if not user["active_task"]:
        await message.answer(
            "У тебя нет активной задачи! Нажми '🚀 Начать задачу', чтобы начать.",
            reply_markup=keyboards.main_menu()
        )
        return
    
    # Получаем ключ сложности для БД
    difficulty = difficulty_map[message.text]
    
    # Завершаем задачу
    result = database.end_task(message.from_user.id, difficulty)
    
    if not result:
        await message.answer(
            "Что-то пошло не так. Попробуй еще раз.",
            reply_markup=keyboards.main_menu()
        )
        return
    
    # Форматируем время
    time_delta = timedelta(seconds=result["seconds"])
    hours, remainder = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
    
    # Отправляем результат
    await message.answer(
        f"Задача завершена! 🎉\n\n"
        f"⏱️ Время выполнения: {time_str}\n"
        f"🔢 Базовые баллы: {result['base_points']}\n"
        f"📊 Сложность: {message.text} (x{result['multiplier']})\n"
        f"💰 Итоговые баллы: {result['final_points']}\n\n"
        f"Всего у тебя: {user['points']} баллов",
        reply_markup=keyboards.main_menu()
    )

# Обработчик отмены задачи
@router.message(F.text == "❌ Отменить задачу")
async def cancel_task(message: Message):
    user = database.get_user(message.from_user.id)
    
    if not user["active_task"]:
        await message.answer(
            "У тебя нет активной задачи!",
            reply_markup=keyboards.main_menu()
        )
        return
    
    user["active_task"] = None
    database.save_users()
    
    await message.answer(
        "Задача отменена!",
        reply_markup=keyboards.main_menu()
    )

# Обработчик меню статистики
@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    user = database.get_user(message.from_user.id)
    
    difficulty_names = {
        "very_easy": "Очень простая",
        "easy": "Простая",
        "standard": "Стандартная",
        "high": "Повышенной сложности",
        "hard": "Сложная",
        "catastrophic": "Катастрофическая"
    }
    
    # Формируем статистику по сложности
    difficulty_stats = "\n".join([
        f"- {difficulty_names[diff]}: {count} задач" 
        for diff, count in user["difficulty_stats"].items() 
        if count > 0
    ]) or "Пока нет данных"
    
    stats_text = (
        f"📊 Твоя статистика:\n\n"
        f"🔢 Выполнено задач: {user['tasks_completed']}\n"
        f"💰 Накоплено баллов: {user['points']}\n\n"
        f"📋 Статистика по сложности:\n{difficulty_stats}\n"
    )
    
    await message.answer(
        stats_text,
        reply_markup=keyboards.main_menu()
    )

# Обработчик меню магазина наград
@router.message(F.text == "🎁 Магазин наград")
async def rewards_menu_handler(message: Message):
    # Определяем, является ли пользователь админом (для простоты считаем вас и вашу девушку админами)
    # В реальном боте нужно хранить список админов в БД или конфиге
    is_admin = True  # Временно делаем всех админами для тестирования
    
    await message.answer(
        "🎁 Магазин наград\n\n"
        "Здесь ты можешь потратить накопленные баллы на награды или управлять доступными наградами.",
        reply_markup=keyboards.rewards_menu(is_admin)
    )

# Обработчик списка наград
@router.message(F.text == "🛍️ Список наград")
async def list_rewards(message: Message):
    rewards = database.get_rewards()
    user = database.get_user(message.from_user.id)
    
    if not rewards:
        await message.answer(
            "В магазине пока нет наград. Создайте их!",
            reply_markup=keyboards.rewards_menu(True)
        )
        return
    
    await message.answer(
        f"Доступные награды (у тебя {user['points']} баллов):\n"
        f"✅ - доступно для покупки\n"
        f"❌ - недостаточно баллов",
        reply_markup=keyboards.rewards_inline_keyboard(rewards, user["points"])
    )

# Обработчик возврата в главное меню
@router.message(F.text == "➡️ Главное меню")
async def back_to_main_menu(message: Message):
    await message.answer(
        "Вернулись в главное меню",
        reply_markup=keyboards.main_menu()
    )

# Обработчик добавления награды
@router.message(F.text == "➕ Добавить награду")
async def add_reward_handler(message: Message, state: FSMContext):
    await state.set_state(RewardStates.waiting_for_name)
    
    await message.answer(
        "Введите название новой награды:",
        reply_markup=None
    )

# Обработчик ввода названия награды
@router.message(StateFilter(RewardStates.waiting_for_name))
async def process_reward_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RewardStates.waiting_for_cost)
    
    await message.answer(
        "Теперь введите стоимость награды (в баллах, только число):"
    )

# Обработчик ввода стоимости награды
@router.message(StateFilter(RewardStates.waiting_for_cost))
async def process_reward_cost(message: Message, state: FSMContext):
    try:
        cost = int(message.text)
        
        if cost <= 0:
            await message.answer(
                "Стоимость должна быть положительным числом. Попробуйте снова:"
            )
            return
            
        data = await state.get_data()
        name = data["name"]
        
        # Добавляем награду
        reward_id = database.add_reward(name, cost)
        
        await message.answer(
            f"Награда '{name}' с ценой {cost} баллов успешно добавлена!",
            reply_markup=keyboards.rewards_menu(True)
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число для стоимости награды:"
        )

# Обработчик покупки награды
@router.callback_query(F.data.startswith("buy_"))
async def buy_reward_handler(callback: CallbackQuery):
    reward_id = callback.data.split("_")[1]
    rewards = database.get_rewards()
    
    if reward_id not in rewards:
        await callback.answer("Эта награда больше не доступна")
        return
    
    reward = rewards[reward_id]
    user = database.get_user(callback.from_user.id)
    
    if user["points"] < reward["cost"]:
        await callback.answer("У вас недостаточно баллов для покупки этой награды!")
        return
    
    await callback.message.edit_text(
        f"Вы уверены, что хотите купить '{reward['name']}' за {reward['cost']} баллов?",
        reply_markup=keyboards.confirm_purchase(reward_id)
    )
    await callback.answer()

# Обработчик подтверждения покупки
@router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy_handler(callback: CallbackQuery):
    reward_id = callback.data.split("_")[2]
    
    success, message = database.buy_reward(callback.from_user.id, reward_id)
    
    if success:
        await callback.message.edit_text(
            f"{message}\n\nНаслаждайтесь своей наградой! 🎉"
        )
        
        # Отправляем новое сообщение с клавиатурой
        await callback.message.answer(
            "Что хотите сделать дальше?",
            reply_markup=keyboards.rewards_menu(True)
        )
    else:
        await callback.message.edit_text(
            f"Ошибка: {message}",
            reply_markup=keyboards.rewards_menu(True)
        )
    
    await callback.answer()

# Обработчик отмены покупки
@router.callback_query(F.data == "cancel_purchase")
async def cancel_purchase_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "Покупка отменена",
        reply_markup=None
    )
    
    # Отправляем новое сообщение с клавиатурой
    await callback.message.answer(
        "Что хотите сделать дальше?",
        reply_markup=keyboards.rewards_menu(True)
    )
    
    await callback.answer()

# Обработчик редактирования награды
@router.callback_query(F.data.startswith("edit_"))
async def edit_reward_handler(callback: CallbackQuery, state: FSMContext):
    reward_id = callback.data.split("_")[1]
    rewards = database.get_rewards()
    
    if reward_id not in rewards:
        await callback.answer("Эта награда больше не доступна")
        return
    
    reward = rewards[reward_id]
    
    await state.update_data(reward_id=reward_id)
    await state.set_state(EditRewardStates.waiting_for_name)
    
    await callback.message.edit_text(
        f"Введите новое название для награды '{reward['name']}' "
        f"(или 'пропустить', чтобы оставить прежнее):"
    )
    
    await callback.answer()

# Обработчик ввода нового названия
@router.message(StateFilter(EditRewardStates.waiting_for_name))
async def process_edit_name(message: Message, state: FSMContext):
    name = None if message.text.lower() == "пропустить" else message.text
    
    await state.update_data(new_name=name)
    await state.set_state(EditRewardStates.waiting_for_cost)
    
    await message.answer(
        "Теперь введите новую стоимость в баллах "
        "(или 'пропустить', чтобы оставить прежнюю):"
    )

# Обработчик ввода новой стоимости
@router.message(StateFilter(EditRewardStates.waiting_for_cost))
async def process_edit_cost(message: Message, state: FSMContext):
    try:
        cost = None
        
        if message.text.lower() != "пропустить":
            cost = int(message.text)
            if cost <= 0:
                await message.answer(
                    "Стоимость должна быть положительным числом. Попробуйте снова:"
                )
                return
        
        data = await state.get_data()
        reward_id = data["reward_id"]
        new_name = data.get("new_name")
        
        # Обновляем награду
        success = database.update_reward(reward_id, new_name, cost)
        
        if success:
            await message.answer(
                "Награда успешно обновлена!",
                reply_markup=keyboards.rewards_menu(True)
            )
        else:
            await message.answer(
                "Ошибка при обновлении награды",
                reply_markup=keyboards.rewards_menu(True)
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число для стоимости награды или 'пропустить':"
        )

# Обработчик удаления награды
@router.callback_query(F.data.startswith("delete_"))
async def delete_reward_handler(callback: CallbackQuery):
    reward_id = callback.data.split("_")[1]
    rewards = database.get_rewards()
    
    if reward_id not in rewards:
        await callback.answer("Эта награда больше не доступна")
        return
    
    reward = rewards[reward_id]
    
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить награду '{reward['name']}'?",
        reply_markup=keyboards.confirm_delete(reward_id)
    )
    
    await callback.answer()

# Обработчик подтверждения удаления
@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_handler(callback: CallbackQuery):
    reward_id = callback.data.split("_")[2]
    
    success = database.delete_reward(reward_id)
    
    if success:
        await callback.message.edit_text(
            "Награда успешно удалена!"
        )
        
        # Отправляем новое сообщение с клавиатурой
        await callback.message.answer(
            "Что хотите сделать дальше?",
            reply_markup=keyboards.rewards_menu(True)
        )
    else:
        await callback.message.edit_text(
            "Ошибка при удалении награды",
            reply_markup=keyboards.rewards_menu(True)
        )
    
    await callback.answer()

# Обработчик отмены удаления
@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "Удаление отменено"
    )
    
    # Отправляем новое сообщение с клавиатурой
    await callback.message.answer(
        "Что хотите сделать дальше?",
        reply_markup=keyboards.rewards_menu(True)
    )
    
    await callback.answer()

# Обработчик возврата в меню наград
@router.callback_query(F.data == "back_to_rewards_menu")
async def back_to_rewards_menu_handler(callback: CallbackQuery):
    await callback.message.delete()
    
    await callback.message.answer(
        "Вернулись в меню наград",
        reply_markup=keyboards.rewards_menu(True)
    )
    
    await callback.answer()

async def update_timer(user_id, message_id, chat_id):
    """Функция для обновления секундомера и баллов"""
    try:
        # Создаем бот с тем же токеном
        bot = Bot(token="6122819236:AAGZoYhWGxuEjQcXe2z7EqeC9OgusIbU8fE")
        
        while True:
            # Получаем текущие данные пользователя
            user = database.get_user(user_id)
            if not user["active_task"]:
                break
                
            # Рассчитываем время и баллы
            start_time = datetime.fromtimestamp(user["active_task"]["start_time"])
            elapsed = datetime.now() - start_time
            seconds = elapsed.total_seconds()
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Расчет базовых очков (1 балл за 5 секунд)
            base_points = int(elapsed.total_seconds() / 5)
            
            # Форматируем строку секундомера
            timer_str = f"⏱️ Секундомер: {hours:02}:{minutes:02}:{seconds:02}\n💰 Баллы: {base_points}"
            
            # Обновляем сообщение
            with suppress(Exception):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=timer_str,
                    reply_markup=keyboards.timer_control_inline()
                )
            
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Обработка отмены задачи
        pass
    except Exception as e:
        logging.error(f"Ошибка в обновлении таймера: {e}")

# Обработчик кнопки "Завершить задачу"
@router.message(F.text == "✅ Завершить задачу")
async def finish_task_handler(message: Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    # Проверяем, есть ли активная задача
    if not user["active_task"]:
        await message.answer(
            "У тебя нет активной задачи!",
            reply_markup=keyboards.main_menu()
        )
        return
    
    # Останавливаем таймер, если он запущен
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    # Запрашиваем выбор сложности
    await message.answer(
        "Выбери сложность выполненной задачи:",
        reply_markup=keyboards.difficulty_menu()
    )

# Обработчик кнопки отмены задачи в меню таймера
@router.message(F.text == "❌ Отменить задачу")
async def cancel_task_handler(message: Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user["active_task"]:
        await message.answer(
            "У тебя нет активной задачи!",
            reply_markup=keyboards.main_menu()
        )
        return
    
    # Останавливаем таймер, если он запущен
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    user["active_task"] = None
    database.save_users()
    
    await message.answer(
        "Задача отменена! 👀",
        reply_markup=keyboards.main_menu()
    )

# Обработчик кнопки "Завершить задачу" из инлайн-клавиатуры
@router.callback_query(F.data == "finish_task")
async def finish_task_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = database.get_user(user_id)
    
    # Проверяем, есть ли активная задача
    if not user["active_task"]:
        await callback.answer("У тебя нет активной задачи!")
        return
    
    # Останавливаем таймер, если он запущен
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    # Запрашиваем выбор сложности
    await callback.message.reply(
        "Выбери сложность выполненной задачи:",
        reply_markup=keyboards.difficulty_menu()
    )
    await callback.answer()

# Обработчик кнопки "Отменить задачу" из инлайн-клавиатуры
@router.callback_query(F.data == "cancel_task")
async def cancel_task_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = database.get_user(user_id)
    
    if not user["active_task"]:
        await callback.answer("У тебя нет активной задачи!")
        return
    
    # Останавливаем таймер, если он запущен
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    user["active_task"] = None
    database.save_users()
    
    await callback.message.reply(
        "Задача отменена! 👀",
        reply_markup=keyboards.main_menu()
    )
    await callback.answer()

# Обработчик кнопки изменения баланса
@router.message(F.text == "💰 Изменить баланс")
async def change_balance_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    await state.set_state(SetPointsStates.waiting_for_points)
    await message.answer(
        f"Твой текущий баланс: {user['points']} баллов.\n"
        f"Введи новое количество баллов:"
    )

# Обработчик ввода нового количества баллов
@router.message(StateFilter(SetPointsStates.waiting_for_points))
async def process_points(message: Message, state: FSMContext):
    try:
        points = int(message.text)
        
        if points < 0:
            await message.answer(
                "Количество баллов не может быть отрицательным. Введи положительное число:"
            )
            return
        
        user_id = message.from_user.id
        
        # Обновляем баланс пользователя
        new_balance = database.update_user_points(user_id, points)
        
        await message.answer(
            f"Твой баланс успешно обновлен! 🎉\n"
            f"Новый баланс: {new_balance} баллов.",
            reply_markup=keyboards.main_menu()
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Эй, введи корректное количество баллов (только циферки):"
        )