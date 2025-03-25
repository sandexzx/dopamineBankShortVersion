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
    global users, rewards
    
    # Загружаем данные пользователей
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = {}
        save_users()
    
    # Загружаем данные наград
    if os.path.exists(REWARDS_FILE):
        with open(REWARDS_FILE, 'r', encoding='utf-8') as f:
            rewards = json.load(f)
    else:
        # Создаем начальные награды
        rewards = {
            "1": {"name": "Чашка кофе", "cost": 100},
            "2": {"name": "Просмотр фильма", "cost": 300},
            "3": {"name": "Выходной день", "cost": 1000}
        }
        save_rewards()

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
            "active_task": None
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

def end_task(user_id, difficulty):
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
    user["active_task"] = None
    
    save_users()
    
    # Возвращаем информацию о завершенной задаче
    return {
        "seconds": int(seconds),
        "base_points": int(base_points),
        "multiplier": multiplier,
        "final_points": final_points
    }

def get_rewards():
    """Получение списка наград"""
    return rewards

def add_reward(name, cost):
    """Добавление новой награды"""
    reward_id = str(max(map(int, rewards.keys()), default=0) + 1)
    rewards[reward_id] = {
        "name": name,
        "cost": cost
    }
    save_rewards()
    return reward_id

def update_reward(reward_id, name=None, cost=None):
    """Обновление награды"""
    if reward_id not in rewards:
        return False
    
    if name:
        rewards[reward_id]["name"] = name
    if cost is not None:
        rewards[reward_id]["cost"] = cost
    
    save_rewards()
    return True

def delete_reward(reward_id):
    """Удаление награды"""
    if reward_id not in rewards:
        return False
    
    del rewards[reward_id]
    save_rewards()
    return True

def buy_reward(user_id, reward_id):
    """Покупка награды"""
    user = get_user(user_id)
    if reward_id not in rewards:
        return False, "Награда не найдена"
    
    reward = rewards[reward_id]
    if user["points"] < reward["cost"]:
        return False, "Недостаточно баллов"
    
    user["points"] -= reward["cost"]
    save_users()
    return True, f"Вы купили {reward['name']} за {reward['cost']} баллов"