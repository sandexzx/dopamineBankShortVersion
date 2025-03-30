#!/bin/bash

# =============================================
# Скрипт автоматизированного деплоя Telegram-бота на Ubuntu 24.04
# Поддерживает новые установки и обновления с резервным копированием
# =============================================

# Настройка цветов для читаемого вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # Сброс цвета

# Параметры по умолчанию
SCRIPT_VERSION="1.0.0"
INSTALL_DIR="/opt/dopamine_bank"
BACKUP_DIR="/opt/dopamine_bank_backups"
SERVICE_NAME="dopamine_bank"
SERVICE_USER="dopamine_bot"
PYTHON_VERSION="3.12"
MAX_BACKUPS=5
MODE="auto"
ROLLBACK_VERSION=""
LOG_FILE="/var/log/dopamine_bank_deploy.log"
REPO_URL="https://github.com/sandexzx/dopamineBankShortVersion.git"

# Функции для логирования
log() {
    local level=$1
    local message=$2
    local color=$NC
    local prefix=""

    case $level in
        "INFO")
            color=$GREEN
            prefix="[INFO]"
            ;;
        "WARNING")
            color=$YELLOW
            prefix="[WARNING]"
            ;;
        "ERROR")
            color=$RED
            prefix="[ERROR]"
            ;;
        "STEP")
            color=$BLUE
            prefix="[STEP]"
            ;;
    esac

    # Вывод в консоль
    echo -e "${color}${prefix}${NC} $(date '+%Y-%m-%d %H:%M:%S') - $message"
    
    # Запись в лог-файл
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $prefix $message" >> $LOG_FILE
}

# Функция проверки успешности команды
check_result() {
    if [ $? -ne 0 ]; then
        log "ERROR" "$1"
        if [ "$2" == "exit" ]; then
            exit 1
        fi
    fi
}

# Функция отображения справки
show_help() {
    echo "Скрипт для автоматизированного деплоя Telegram-бота на Ubuntu 24.04"
    echo ""
    echo "Использование: $0 [опции]"
    echo ""
    echo "Опции:"
    echo "  -m, --mode MODE       Режим установки: auto (определить автоматически), install (новая установка), update (обновление)"
    echo "  -d, --dir DIR         Директория установки (по умолчанию: $INSTALL_DIR)"
    echo "  -b, --backup DIR      Директория для резервных копий (по умолчанию: $BACKUP_DIR)"
    echo "  -s, --service NAME    Имя службы systemd (по умолчанию: $SERVICE_NAME)"
    echo "  -u, --user USER       Пользователь для запуска службы (по умолчанию: $SERVICE_USER)"
    echo "  -r, --rollback VER    Откат к резервной копии с указанным временным штампом"
    echo "  -k, --keep NUM        Количество сохраняемых резервных копий (по умолчанию: $MAX_BACKUPS)"
    echo "  -h, --help            Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 --mode install     Выполнить новую установку"
    echo "  $0 --mode update      Выполнить обновление существующей установки"
    echo "  $0 --rollback 20240330_120145  Откатиться к указанной версии"
    echo ""
}

# Обработка аргументов командной строки
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -m|--mode)
            MODE="$2"
            shift
            shift
            ;;
        -d|--dir)
            INSTALL_DIR="$2"
            shift
            shift
            ;;
        -b|--backup)
            BACKUP_DIR="$2"
            shift
            shift
            ;;
        -s|--service)
            SERVICE_NAME="$2"
            shift
            shift
            ;;
        -u|--user)
            SERVICE_USER="$2"
            shift
            shift
            ;;
        -r|--rollback)
            ROLLBACK_VERSION="$2"
            shift
            shift
            ;;
        -k|--keep)
            MAX_BACKUPS="$2"
            shift
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log "ERROR" "Неизвестный параметр: $1"
            show_help
            exit 1
            ;;
    esac
done

# Проверка наличия прав суперпользователя
if [ "$(id -u)" -ne 0 ]; then
    log "ERROR" "Этот скрипт должен быть запущен с правами суперпользователя (sudo)!"
    exit 1
fi

# Подготовка директорий для логов
mkdir -p $(dirname "$LOG_FILE")
touch $LOG_FILE
chmod 644 $LOG_FILE

# Запись информации о запуске
log "INFO" "====== НАЧАЛО ДЕПЛОЯ DOPAMINE BANK БОТА ======"
log "INFO" "Версия скрипта: $SCRIPT_VERSION"
log "INFO" "Режим: $MODE"
log "INFO" "Директория установки: $INSTALL_DIR"
log "INFO" "Директория резервных копий: $BACKUP_DIR"
log "INFO" "Имя сервиса: $SERVICE_NAME"
log "INFO" "Пользователь сервиса: $SERVICE_USER"

# Автоматическое определение главного файла для запуска
find_main_file() {
    local dir=$1
    # Ищем файл main.py в корне проекта
    if [ -f "$dir/main.py" ]; then
        echo "main.py"
        return 0
    fi
    
    # Ищем другие файлы Python с возможным вызовом Bot или Dispatcher
    local main_candidates=$(find "$dir" -type f -name "*.py" -exec grep -l "import.*Bot\|Dispatcher" {} \;)
    
    if [ -n "$main_candidates" ]; then
        # Выбираем первый найденный файл
        echo $(basename $(echo "$main_candidates" | head -n 1))
        return 0
    fi
    
    # Возвращаем пустую строку, если ничего не найдено
    echo ""
    return 1
}

# Выполнение отката, если указана опция
if [ ! -z "$ROLLBACK_VERSION" ]; then
    log "STEP" "Начинаю откат к версии $ROLLBACK_VERSION"
    
    # Проверка существования резервной копии
    BACKUP_PATH="$BACKUP_DIR/$ROLLBACK_VERSION"
    if [ ! -d "$BACKUP_PATH" ]; then
        log "ERROR" "Резервная копия $ROLLBACK_VERSION не найдена!"
        exit 1
    fi
    
    # Останавливаем сервис
    log "INFO" "Останавливаю сервис $SERVICE_NAME"
    systemctl stop $SERVICE_NAME
    check_result "Не удалось остановить сервис $SERVICE_NAME" "warning"
    
    # Создаем резервную копию текущей версии перед откатом
    CURRENT_BACKUP_TIME=$(date '+%Y%m%d_%H%M%S')
    CURRENT_BACKUP_DIR="$BACKUP_DIR/pre_rollback_$CURRENT_BACKUP_TIME"
    
    if [ -d "$INSTALL_DIR" ]; then
        log "INFO" "Создаю резервную копию текущей версии перед откатом: $CURRENT_BACKUP_DIR"
        mkdir -p "$CURRENT_BACKUP_DIR"
        cp -r "$INSTALL_DIR"/* "$CURRENT_BACKUP_DIR"/ 2>/dev/null
        check_result "Не удалось создать резервную копию текущей версии" "warning"
    fi
    
    # Восстанавливаем из резервной копии
    log "INFO" "Восстанавливаю файлы из резервной копии $ROLLBACK_VERSION"
    rm -rf "$INSTALL_DIR"/*
    cp -r "$BACKUP_PATH"/* "$INSTALL_DIR"/ 2>/dev/null
    check_result "Не удалось восстановить файлы из резервной копии" "exit"
    
    # Устанавливаем корректные разрешения
    log "INFO" "Настраиваю разрешения файлов"
    chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR"
    check_result "Не удалось настроить разрешения файлов" "warning"
    
    # Перезапускаем сервис
    log "INFO" "Запускаю сервис $SERVICE_NAME"
    systemctl start $SERVICE_NAME
    check_result "Не удалось запустить сервис $SERVICE_NAME" "warning"
    
    log "INFO" "Откат к версии $ROLLBACK_VERSION успешно выполнен!"
    log "INFO" "====== ЗАВЕРШЕНИЕ ДЕПЛОЯ DOPAMINE BANK БОТА ======"
    
    # Выводим информацию о статусе сервиса
    systemctl status $SERVICE_NAME --no-pager
    
    exit 0
fi

# Начинаем основной процесс установки/обновления
log "STEP" "Проверка системных зависимостей"

# Обновление списка пакетов
apt update
check_result "Не удалось обновить список пакетов" "warning"

# Установка необходимых зависимостей
log "INFO" "Установка необходимых пакетов"
apt install -y git python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip
check_result "Не удалось установить необходимые пакеты" "exit"

# Автоматическое определение режима установки (если не указан явно)
if [ "$MODE" == "auto" ]; then
    if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/main.py" ]; then
        MODE="update"
        log "INFO" "Автоматически определен режим: обновление существующей установки"
    else
        MODE="install"
        log "INFO" "Автоматически определен режим: новая установка"
    fi
fi

# Создаем пользователя, если его нет
if ! id "$SERVICE_USER" &>/dev/null; then
    log "INFO" "Создаю пользователя $SERVICE_USER для запуска сервиса"
    useradd -m -s /bin/bash "$SERVICE_USER"
    check_result "Не удалось создать пользователя $SERVICE_USER" "exit"
fi

# Создаем директории, если их нет
mkdir -p "$INSTALL_DIR"
mkdir -p "$BACKUP_DIR"
check_result "Не удалось создать необходимые директории" "exit"

# Выявление пользовательских данных (БД и конфигураций)
IMPORTANT_FILES=("users.json" "rewards.json" ".env" "*.db" "*.sqlite" "*.sqlite3" "config.ini" "config.yaml" "config.yml" "config.json")

# Если это обновление, создаем резервную копию
if [ "$MODE" == "update" ]; then
    log "STEP" "Создание резервной копии перед обновлением"
    
    # Создаем директорию для новой резервной копии с временным штампом
    BACKUP_TIME=$(date '+%Y%m%d_%H%M%S')
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_TIME"
    mkdir -p "$BACKUP_PATH"
    
    # Копируем все файлы из директории установки
    log "INFO" "Копирование файлов в $BACKUP_PATH"
    cp -r "$INSTALL_DIR"/* "$BACKUP_PATH"/ 2>/dev/null
    check_result "Не удалось создать резервную копию" "exit"
    
    # Ротация резервных копий - удаляем старые, если их больше MAX_BACKUPS
    log "INFO" "Ротация резервных копий (оставляем последние $MAX_BACKUPS)"
    ls -1dt "$BACKUP_DIR"/*/ 2>/dev/null | tail -n +$((MAX_BACKUPS+1)) | xargs -r rm -rf
    check_result "Не удалось выполнить ротацию резервных копий" "warning"
    
    # Останавливаем сервис перед обновлением
    log "INFO" "Останавливаю сервис $SERVICE_NAME"
    systemctl stop $SERVICE_NAME 2>/dev/null
    check_result "Не удалось остановить сервис $SERVICE_NAME" "warning"
    
    # Создаем временную директорию для хранения файлов данных
    TMP_DATA_DIR=$(mktemp -d)
    log "INFO" "Временная директория для данных: $TMP_DATA_DIR"
    
    # Сохраняем важные пользовательские файлы
    log "INFO" "Сохранение пользовательских данных"
    for pattern in "${IMPORTANT_FILES[@]}"; do
        # Ищем файлы по шаблону
        find "$INSTALL_DIR" -name "$pattern" -type f -exec cp {} "$TMP_DATA_DIR/" \; 2>/dev/null
    done
fi

# Клонирование или обновление кода из репозитория
log "STEP" "Получение исходного кода бота"

# Создаем временную директорию для клонирования
REPO_DIR=$(mktemp -d)
log "INFO" "Клонирование репозитория во временную директорию: $REPO_DIR"
git clone "$REPO_URL" "$REPO_DIR"
check_result "Не удалось клонировать репозиторий" "exit"

# Очищаем директорию установки (с сохранением данных, если это обновление)
if [ "$MODE" == "update" ]; then
    log "INFO" "Очистка директории установки с сохранением данных"
    find "$INSTALL_DIR" -type f -not -path "*/\.*" -delete
else
    log "INFO" "Подготовка директории для новой установки"
    rm -rf "$INSTALL_DIR"/*
fi

# Копируем файлы из репозитория в директорию установки
log "INFO" "Копирование файлов из репозитория в директорию установки"
cp -r "$REPO_DIR"/* "$INSTALL_DIR"/
check_result "Не удалось скопировать файлы из репозитория" "exit"

# Восстанавливаем пользовательские данные, если это обновление
if [ "$MODE" == "update" ]; then
    log "INFO" "Восстановление пользовательских данных"
    cp -f "$TMP_DATA_DIR"/* "$INSTALL_DIR"/ 2>/dev/null
    check_result "Не удалось восстановить пользовательские данные" "warning"
fi

# Настройка виртуального окружения Python
log "STEP" "Настройка виртуального окружения Python ${PYTHON_VERSION}"
cd "$INSTALL_DIR"

# Создаем виртуальное окружение, если его нет
if [ ! -d "$INSTALL_DIR/venv" ]; then
    log "INFO" "Создание нового виртуального окружения Python ${PYTHON_VERSION}"
    python${PYTHON_VERSION} -m venv venv
    check_result "Не удалось создать виртуальное окружение" "exit"
fi

# Установка зависимостей
log "INFO" "Установка зависимостей из requirements.txt"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
check_result "Не удалось обновить pip" "warning"

if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt
    check_result "Не удалось установить зависимости из requirements.txt" "exit"
else
    log "WARNING" "Файл requirements.txt не найден. Установка минимальных зависимостей."
    "$INSTALL_DIR/venv/bin/pip" install aiogram==3.19.0
    check_result "Не удалось установить минимальные зависимости" "exit"
fi

# Определение основного файла для запуска
log "INFO" "Определение основного файла для запуска"
MAIN_FILE=$(find_main_file "$INSTALL_DIR")
if [ -z "$MAIN_FILE" ]; then
    MAIN_FILE="main.py" # По умолчанию предполагаем main.py
    log "WARNING" "Не удалось автоматически определить основной файл. Используется $MAIN_FILE по умолчанию."
else
    log "INFO" "Определен основной файл: $MAIN_FILE"
fi

# Создание и настройка systemd сервиса
log "STEP" "Создание systemd сервиса"

# Формируем имя сервиса из имени директории, если не задано явно
if [ "$SERVICE_NAME" == "dopamine_bank" ]; then
    SERVICE_NAME=$(basename "$INSTALL_DIR" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    log "INFO" "Сгенерировано имя сервиса: $SERVICE_NAME"
fi

# Создаем службу systemd
log "INFO" "Создание файла службы systemd: /etc/systemd/system/${SERVICE_NAME}.service"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Dopamine Bank Telegram Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $MAIN_FILE
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

check_result "Не удалось создать файл службы systemd" "exit"

# Настройка прав доступа
log "INFO" "Настройка прав доступа для директории установки"
chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR"
chmod -R 750 "$INSTALL_DIR"
check_result "Не удалось настроить права доступа" "warning"

# Перезагрузка systemd и включение автозапуска
log "STEP" "Настройка автозапуска сервиса"
systemctl daemon-reload
check_result "Не удалось перезагрузить конфигурацию systemd" "warning"

systemctl enable "$SERVICE_NAME"
check_result "Не удалось включить автозапуск сервиса" "warning"

# Запуск сервиса
log "STEP" "Запуск сервиса"
systemctl start "$SERVICE_NAME"
check_result "Не удалось запустить сервис" "warning"

# Очистка временных файлов
log "INFO" "Очистка временных файлов"
rm -rf "$REPO_DIR"
if [ "$MODE" == "update" ]; then
    rm -rf "$TMP_DATA_DIR"
fi

# Вывод информации о статусе и завершение
log "INFO" "====== ДЕПЛОЙ DOPAMINE BANK БОТА УСПЕШНО ЗАВЕРШЕН ======"
log "INFO" "Информация о сервисе:"
systemctl status "$SERVICE_NAME" --no-pager

# Справка по управлению ботом
cat << EOF

=============================================
📱 УПРАВЛЕНИЕ DOPAMINE BANK БОТОМ 📱
=============================================

✅ Бот успешно развернут и запущен!

🚀 Основные команды управления:

- Проверить статус бота:
  sudo systemctl status $SERVICE_NAME

- Перезапустить бота:
  sudo systemctl restart $SERVICE_NAME

- Остановить бота:
  sudo systemctl stop $SERVICE_NAME

- Запустить бота:
  sudo systemctl start $SERVICE_NAME

- Просмотр логов бота:
  sudo journalctl -u $SERVICE_NAME -f

📂 Расположение файлов:

- Директория установки: $INSTALL_DIR
- Файлы баз данных: $INSTALL_DIR/users.json
- Логи деплоя: $LOG_FILE
- Резервные копии: $BACKUP_DIR

🔁 Для обновления бота выполните скрипт снова:
  sudo $(basename "$0") --mode update

⏪ Для отката к предыдущей версии выполните:
  sudo $(basename "$0") --rollback <версия>

💡 Список доступных резервных копий:
  ls -la $BACKUP_DIR

=============================================
EOF

exit 0