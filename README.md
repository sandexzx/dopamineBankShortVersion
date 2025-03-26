

# 🏦 Dopamine Bank

Dopamine Bank - это Telegram бот для геймификации ваших задач и повышения продуктивности. Выполняйте задачи, получайте виртуальные баллы и обменивайте их на награды!

## 🚀 Функционал

- **Отслеживание задач**: Запускайте таймер при начале выполнения задачи
- **Система баллов**: Получайте баллы в зависимости от времени и сложности задачи
- **Магазин наград**: Создавайте и покупайте кастомные награды за заработанные баллы
- **Статистика**: Отслеживайте свой прогресс и историю выполненных задач
- **Настраиваемая сложность**: Выбирайте сложность задачи от "Очень простой" до "Катастрофической"

## 📱 Скриншоты

_Здесь будут скриншоты интерфейса бота_

## 🛠️ Установка

### Быстрая установка на Ubuntu 24.04

Выполните одну команду для полной установки:

```bash
curl -s https://raw.githubusercontent.com/sandexzx/dopamineBankShortVersion/main/deploy.sh | bash
```

Скрипт автоматически:
- Установит все необходимые зависимости
- Настроит виртуальное окружение Python
- Создаст systemd-сервис для автозапуска
- Сохранит данные при обновлении

### Ручная установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/sandexzx/dopamineBankShortVersion.git
cd dopamineBankShortVersion
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Запустите бота:
```bash
python main.py
```

## 🔧 Настройка

В файле `main.py` вы можете изменить токен бота на свой:

```python
# Создаем бота с токеном (вставьте свой токен)
bot = Bot(token="ВАШ_ТОКЕН_БОТА")
```

## 📊 Системные требования

- Python 3.8+
- Ubuntu 24.04 (рекомендуется)
- Минимум 512 МБ оперативной памяти
- 1 ГБ свободного места на диске

## 🧑‍💻 Технический стек

- Python 3
- aiogram 3.4.1
- systemd (для деплоя)

## 🔄 Обновление

Для обновления уже установленного бота просто повторно запустите скрипт установки:

```bash
curl -s https://raw.githubusercontent.com/sandexzx/dopamineBankShortVersion/main/deploy.sh | bash
```

Скрипт автоматически создаст резервную копию ваших данных перед обновлением.

## 🤝 Вклад в проект

Пул-реквесты приветствуются! Для крупных изменений, пожалуйста, сначала откройте issue, чтобы обсудить желаемое изменение.

## 📝 To-Do

- [ ] Добавить уведомления о задачах
- [ ] Реализовать командную работу
- [ ] Добавить еженедельную и ежемесячную статистику
- [ ] Интеграция с календарями