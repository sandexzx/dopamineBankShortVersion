#!/bin/bash

# Скрипт для развертывания Dopamine Bank на Ubuntu 24.04
# Автор: Крутой кодер

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для красивого вывода
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка наличия необходимых утилит
check_dependencies() {
    log_info "Проверка зависимостей системы..."
    
    # Массив требуемых инструментов
    tools=("git" "python3" "python3-venv" "python3-pip")
    
    # Проверяем, установлен ли каждый инструмент
    for tool in "${tools[@]}"; do
        if ! dpkg -l | grep -q $tool; then
            log_info "Устанавливаем $tool..."
            apt update
            apt install -y $tool
            if [ $? -ne 0 ]; then
                log_error "Не удалось установить $tool. Прерываем установку."
                exit 1
            fi
        fi
    done
}

# Определение пользователя для сервиса
setup_user() {
    # Проверяем, запущен ли скрипт от имени root
    if [ "$(id -u)" -eq 0 ]; then
        log_info "Скрипт запущен от имени root."
        
        # Проверяем, существует ли пользователь dopaminebot
        if ! id "dopaminebot" &>/dev/null; then
            log_info "Создаем пользователя dopaminebot для запуска сервиса..."
            useradd -m -s /bin/bash dopaminebot
        fi
        
        SERVICE_USER="dopaminebot"
    else
        # Если скрипт запущен не от root, используем текущего пользователя
        SERVICE_USER="$USER"
    fi
    
    log_info "Сервис будет запущен от имени пользователя: $SERVICE_USER"
}

# Задаем пути установки
INSTALL_DIR="/opt/dopamine_bank"
BACKUP_DIR="/opt/dopamine_bank_backup"
SERVICE_NAME="dopamine_bank"
REPO_URL="https://github.com/sandexzx/dopamineBankShortVersion.git"

# Создание бэкапа данных, если бот уже установлен
backup_data() {
    if [ -d "$INSTALL_DIR" ]; then
        log_info "Обнаружена существующая установка. Создаю резервную копию данных..."
        
        # Создаем директорию для бэкапа, если её нет
        mkdir -p $BACKUP_DIR
        
        # Копируем файлы данных
        if [ -f "$INSTALL_DIR/users.json" ]; then
            cp "$INSTALL_DIR/users.json" "$BACKUP_DIR/"
        fi
        
        if [ -f "$INSTALL_DIR/rewards.json" ]; then
            cp "$INSTALL_DIR/rewards.json" "$BACKUP_DIR/"
        fi
        
        log_info "Бэкап данных создан в $BACKUP_DIR"
    else
        log_info "Существующая установка не обнаружена. Выполняется новая установка."
    fi
}

# Остановка сервиса, если существует
stop_service() {
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "Останавливаю сервис $SERVICE_NAME..."
        systemctl stop $SERVICE_NAME
    fi
}

# Скачивание или обновление репозитория
get_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        log_info "Обновляю исходный код из репозитория..."
        cd $INSTALL_DIR
        git pull
    else
        log_info "Клонирую репозиторий..."
        mkdir -p $INSTALL_DIR
        git clone $REPO_URL $INSTALL_DIR
    fi
    
    # Устанавливаем правильные права доступа
    if [ "$(id -u)" -eq 0 ]; then
        chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    fi
}

# Создание виртуального окружения и установка зависимостей
setup_venv() {
    log_info "Настраиваю виртуальное окружение Python..."
    
    # Переключаемся на нужного пользователя для создания venv (если запущено от root)
    if [ "$(id -u)" -eq 0 ]; then
        cd $INSTALL_DIR
        
        # Создаем виртуальное окружение, если его нет
        if [ ! -d "$INSTALL_DIR/venv" ]; then
            su -c "python3 -m venv $INSTALL_DIR/venv" $SERVICE_USER
        fi
        
        # Устанавливаем зависимости
        su -c "source $INSTALL_DIR/venv/bin/activate && pip install --upgrade pip && pip install -r $INSTALL_DIR/requirements.txt && deactivate" $SERVICE_USER
    else
        # Если скрипт запущен не от root
        cd $INSTALL_DIR
        
        # Создаем виртуальное окружение, если его нет
        if [ ! -d "$INSTALL_DIR/venv" ]; then
            python3 -m venv venv
        fi
        
        # Устанавливаем зависимости
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        deactivate
    fi
}

# Восстановление баз данных из бэкапа
restore_data() {
    # Восстанавливаем файлы данных, если есть бэкап
    if [ -f "$BACKUP_DIR/users.json" ]; then
        log_info "Восстанавливаю данные пользователей из бэкапа..."
        cp "$BACKUP_DIR/users.json" "$INSTALL_DIR/"
    fi
    
    if [ -f "$BACKUP_DIR/rewards.json" ]; then
        log_info "Восстанавливаю данные наград из бэкапа..."
        cp "$BACKUP_DIR/rewards.json" "$INSTALL_DIR/"
    fi
    
    # Устанавливаем правильные права доступа для восстановленных файлов
    if [ "$(id -u)" -eq 0 ]; then
        chown $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR/users.json" 2>/dev/null
        chown $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR/rewards.json" 2>/dev/null
    fi
}

# Создание systemd сервиса
create_service() {
    log_info "Создаю systemd сервис..."
    
    # Используем sudo только если не root
    if [ "$(id -u)" -eq 0 ]; then
        SUDO_CMD=""
    else
        SUDO_CMD="sudo"
    fi
    
    $SUDO_CMD tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOL
[Unit]
Description=Dopamine Bank Telegram Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

    # Перезагружаем systemd и включаем сервис
    $SUDO_CMD systemctl daemon-reload
    $SUDO_CMD systemctl enable $SERVICE_NAME
}

# Запуск сервиса
start_service() {
    log_info "Запускаю сервис $SERVICE_NAME..."
    
    # Используем sudo только если не root
    if [ "$(id -u)" -eq 0 ]; then
        SUDO_CMD=""
    else
        SUDO_CMD="sudo"
    fi
    
    $SUDO_CMD systemctl start $SERVICE_NAME
    
    # Проверка статуса сервиса
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "Сервис $SERVICE_NAME успешно запущен! 🚀"
    else
        log_error "Не удалось запустить сервис $SERVICE_NAME. Проверьте логи: journalctl -u $SERVICE_NAME"
    fi
}

# Вывод информации о статусе бота
show_status() {
    log_info "==========================="
    log_info "✅ Установка завершена!"
    log_info "==========================="
    log_info "📁 Директория установки: $INSTALL_DIR"
    log_info "🤖 Имя сервиса: $SERVICE_NAME"
    log_info "👤 Пользователь сервиса: $SERVICE_USER"
    log_info "📊 Проверить статус: systemctl status $SERVICE_NAME"
    log_info "📝 Логи: journalctl -u $SERVICE_NAME -f"
    log_info "🔄 Перезапуск: systemctl restart $SERVICE_NAME"
    log_info "==========================="
}

# Основная функция установки
main() {
    log_info "🚀 Начинаю установку/обновление Dopamine Bank..."
    
    # Настраиваем пользователя для запуска сервиса
    setup_user
    
    # Запускаем все шаги установки
    check_dependencies
    backup_data
    stop_service
    get_repo
    setup_venv
    restore_data
    create_service
    start_service
    show_status
}

# Запускаем скрипт
main