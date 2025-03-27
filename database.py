import json
import os
from datetime import datetime

# Файлы для хранения данных
USERS_FILE = "users.json"
REWARDS_FILE = "rewards.json"

# Структура данных
users = {}
rewards = {}

def init():
    """Инициализация базы данных"""
    global users
    
    # Загружаем данные пользователей
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = {}
        save_users()
    
    # Перенос данных из старого формата в новый (если нужно)
    migrate_rewards_if_needed()

def migrate_rewards_if_needed():
    """Миграция наград из старого формата в новый"""
    global users
    
    # Проверяем, существует ли старый файл с наградами
    if os.path.exists(REWARDS_FILE):
        # Загружаем старые награды
        with open(REWARDS_FILE, 'r', encoding='utf-8') as f:
            old_rewards = json.load(f)
        
        # Проверяем всех существующих пользователей
        for user_id, user_data in users.items():
            # Если у пользователя еще нет поля rewards, создаем его
            if "rewards" not in user_data:
                user_data["rewards"] = {}
                
            # Если у пользователя нет наград, копируем дефолтные
            if len(user_data["rewards"]) == 0:
                user_data["rewards"] = old_rewards.copy()
        
        # Сохраняем изменения
        save_users()
        
        # Переименовываем старый файл, чтобы не использовать его снова
        os.rename(REWARDS_FILE, REWARDS_FILE + ".backup")

def save_users():
    """Сохранение данных пользователей"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def save_rewards():
    """Сохранение данных наград"""
    with open(REWARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(rewards, f, ensure_ascii=False, indent=4)

def get_user(user_id):
    """Получение данных пользователя"""
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "points": 0,
            "tasks_completed": 0,
            "difficulty_stats": {
                "very_easy": 0,
                "easy": 0,
                "standard": 0,
                "high": 0,
                "hard": 0,
                "catastrophic": 0
            },
            "active_task": None,
            "tasks_history": [],  # Добавляем историю задач
            "rewards": {}  # Добавляем персональные награды
        }
        save_users()
    return users[user_id_str]

def start_task(user_id):
    """Начало задачи"""
    user = get_user(user_id)
    user["active_task"] = {
        "start_time": datetime.now().timestamp(),
        "points": 0
    }
    save_users()
    return user["active_task"]

def end_task(user_id, difficulty, task_name="Задача"):
    """Завершение задачи"""
    user = get_user(user_id)
    if not user["active_task"]:
        return None
    
    # Рассчитываем время в секундах
    end_time = datetime.now().timestamp()
    start_time = user["active_task"]["start_time"]
    seconds = end_time - start_time
    
    # Расчет базовых очков (1 балл за 5 секунд)
    base_points = seconds / 5
    
    # Коэффициенты сложности
    difficulty_multipliers = {
        "very_easy": 0.5,
        "easy": 0.8,
        "standard": 1.0,
        "high": 1.2,
        "hard": 1.5,
        "catastrophic": 2.0
    }
    
    # Применяем коэффициент сложности
    multiplier = difficulty_multipliers.get(difficulty, 1.0)
    final_points = int(base_points * multiplier)
    
    # Обновляем статистику пользователя
    user["points"] += final_points
    user["tasks_completed"] += 1
    user["difficulty_stats"][difficulty] += 1
    
    # Сохраняем задачу в историю
    task_id = user["tasks_completed"]  # ID задачи = порядковый номер
    task_history_entry = {
        "id": task_id,
        "name": task_name,
        "difficulty": difficulty,
        "start_time": start_time,
        "end_time": end_time,
        "duration": seconds,
        "points": final_points,
        "date": datetime.fromtimestamp(end_time).strftime("%Y-%m-%d")
    }
    user["tasks_history"].append(task_history_entry)
    
    # Очищаем активную задачу
    user["active_task"] = None
    
    save_users()
    
    # Возвращаем информацию о завершенной задаче
    return {
        "seconds": int(seconds),
        "base_points": int(base_points),
        "multiplier": multiplier,
        "final_points": final_points,
        "task_id": task_id
    }

def get_rewards(user_id):
    """Получение списка наград пользователя"""
    user = get_user(user_id)
    return user["rewards"]

def add_reward(user_id, name, cost):
    """Добавление новой награды для пользователя"""
    user = get_user(user_id)
    rewards = user["rewards"]
    
    # Генерируем новый ID для награды
    reward_id = str(max(map(int, rewards.keys()), default=0) + 1)
    
    rewards[reward_id] = {
        "name": name,
        "cost": cost
    }
    save_users()
    return reward_id

def update_reward(user_id, reward_id, name=None, cost=None):
    """Обновление награды пользователя"""
    user = get_user(user_id)
    rewards = user["rewards"]
    
    if reward_id not in rewards:
        return False
    
    if name:
        rewards[reward_id]["name"] = name
    if cost is not None:
        rewards[reward_id]["cost"] = cost
    
    save_users()
    return True

def delete_reward(user_id, reward_id):
    """Удаление награды пользователя"""
    user = get_user(user_id)
    rewards = user["rewards"]
    
    if reward_id not in rewards:
        return False
    
    del rewards[reward_id]
    save_users()
    return True

def buy_reward(user_id, reward_id):
    """Покупка награды"""
    user = get_user(user_id)
    rewards = user["rewards"]
    
    if reward_id not in rewards:
        return False, "Награда не найдена"
    
    reward = rewards[reward_id]
    if user["points"] < reward["cost"]:
        return False, "Недостаточно баллов"
    
    user["points"] -= reward["cost"]
    save_users()
    return True, f"Вы купили {reward['name']} за {reward['cost']} баллов"

def update_user_points(user_id, points):
    """Обновление баланса баллов пользователя"""
    user = get_user(user_id)
    user["points"] = points
    save_users()
    return user["points"]

def get_today_tasks(user_id):
    """Получение задач за сегодняшний день"""
    user = get_user(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Фильтруем задачи по сегодняшней дате
    today_tasks = [task for task in user["tasks_history"] if task["date"] == today]
    
    # Сортируем по времени завершения (от новых к старым)
    today_tasks.sort(key=lambda x: x["end_time"], reverse=True)
    
    return today_tasks