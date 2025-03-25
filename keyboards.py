from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Основное меню
def main_menu():
    kb = [
        [KeyboardButton(text="🚀 Начать задачу")],
        [KeyboardButton(text="🎁 Магазин наград"), KeyboardButton(text="📊 Статистика")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Меню выбора сложности задачи
def difficulty_menu():
    kb = [
        [KeyboardButton(text="Очень простая")],
        [KeyboardButton(text="Простая")],
        [KeyboardButton(text="Стандартная")],
        [KeyboardButton(text="Повышенной сложности")],
        [KeyboardButton(text="Сложная")],
        [KeyboardButton(text="Катастрофическая")],
        [KeyboardButton(text="❌ Отменить задачу")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Меню магазина наград
def rewards_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="🛍️ Список наград")],
        [KeyboardButton(text="➡️ Главное меню")]
    ]
    
    if is_admin:
        kb.insert(1, [KeyboardButton(text="➕ Добавить награду")])
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Инлайн клавиатура для наград
def rewards_inline_keyboard(rewards, user_points):
    buttons = []
    
    for reward_id, reward in rewards.items():
        affordable = "✅ " if user_points >= reward["cost"] else "❌ "
        buttons.append([InlineKeyboardButton(
            text=f"{affordable}{reward['name']} - {reward['cost']} баллов",
            callback_data=f"buy_{reward_id}"
        )])
        
        # Добавляем кнопки редактирования и удаления
        edit_delete_row = [
            InlineKeyboardButton(
                text="✏️ Изменить",
                callback_data=f"edit_{reward_id}"
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"delete_{reward_id}"
            )
        ]
        buttons.append(edit_delete_row)
    
    buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="back_to_rewards_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Подтверждение покупки
def confirm_purchase(reward_id):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_buy_{reward_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_purchase")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Подтверждение удаления
def confirm_delete(reward_id):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete_{reward_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура управления таймером
def timer_control_menu():
    kb = [
        [KeyboardButton(text="✅ Завершить задачу")],
        [KeyboardButton(text="❌ Отменить задачу")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Инлайн-клавиатура для управления таймером
def timer_control_inline():
    buttons = [
        [
            InlineKeyboardButton(text="✅ Завершить", callback_data="finish_task"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_task")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)