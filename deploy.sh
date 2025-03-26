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
            sudo apt update
            sudo apt install -y $tool
            if [ $? -ne 0 ]; then
                log_error "Не удалось установить $tool. Прерываем установку."
                exit 1
            fi
        fi
    done
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
        sudo systemctl stop $SERVICE_NAME
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
        sudo mkdir -p $INSTALL_DIR
        sudo git clone $REPO_URL $INSTALL_DIR
        sudo chown -R $USER:$USER $INSTALL_DIR
    fi
}

# Создание виртуального окружения и установка зависимостей
setup_venv() {
    log_info "Настраиваю виртуальное окружение Python..."
    
    # Создаем виртуальное окружение, если его нет
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        cd $INSTALL_DIR
        python3 -m venv venv
    fi
    
    # Устанавливаем зависимости
    cd $INSTALL_DIR
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
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
}

# Создание systemd сервиса
create_service() {
    log_info "Создаю systemd сервис..."
    
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOL
[Unit]
Description=Dopamine Bank Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

    # Перезагружаем systemd и включаем сервис
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
}

# Запуск сервиса
start_service() {
    log_info "Запускаю сервис $SERVICE_NAME..."
    sudo systemctl start $SERVICE_NAME
    
    # Проверка статуса сервиса
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "Сервис $SERVICE_NAME успешно запущен! 🚀"
    else
        log_error "Не удалось запустить сервис $SERVICE_NAME. Проверьте логи: sudo journalctl -u $SERVICE_NAME"
    fi
}

# Вывод информации о статусе бота
show_status() {
    log_info "==========================="
    log_info "✅ Установка завершена!"
    log_info "==========================="
    log_info "📁 Директория установки: $INSTALL_DIR"
    log_info "🤖 Имя сервиса: $SERVICE_NAME"
    log_info "📊 Проверить статус: sudo systemctl status $SERVICE_NAME"
    log_info "📝 Логи: sudo journalctl -u $SERVICE_NAME -f"
    log_info "🔄 Перезапуск: sudo systemctl restart $SERVICE_NAME"
    log_info "==========================="
}

# Основная функция установки
main() {
    log_info "🚀 Начинаю установку/обновление Dopamine Bank..."
    
    # Проверяем, запущен ли скрипт от имени root
    if [ "$(id -u)" -eq 0 ]; then
        log_error "Скрипт не должен запускаться от имени root. Используйте обычного пользователя с правами sudo."
        exit 1
    fi
    
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