import minecraft_launcher_lib as mclib
import subprocess
import logging
# Импортируем необходимые функции из main
from main import load_config, max_progress_bar, current_progress_bar, status_progress_bar
from threading import Lock
import os
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import sys
import time
# Изменяем импорт для правильного доступа к функциям
from main import load_config

# Initialize progress tracking
_progress_max = 0
_progress_status = ""
_progress_current = 0

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(levelname)s: %(message)s', 
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('minecraft_launcher.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MinecraftLauncher:
    """Enhanced Minecraft launcher with better error handling and configuration management."""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        self.game_lock = Lock()
        self.is_game_running = False
        self.game_process: Optional[subprocess.Popen] = None
        self.log_file = Path('minecraft_latest.log')
        
        # Initialize log file
        self._init_log_file()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with defaults."""
        default_config = {
            'username': 'Player',
            'minecraft_version': '1.20.1',
            'memory_gb': 4,
            'minecraft_dir': 'minecraft',
            'loader': 'fabric',
            'java_path': '',
            'auto_update': True
        }
        
        try:
            config_data = load_config("config.json")
            actual_username = config_data.get("nickname", USERNAME)
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    
                # Merge with defaults
                config = default_config.copy()
                config.update(file_config)
                
                # Validate critical values
                if not isinstance(config['memory_gb'], (int, float)) or config['memory_gb'] < 1:
                    config['memory_gb'] = 4
                if config['memory_gb'] > 32:
                    config['memory_gb'] = 32
                    
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def _init_log_file(self):
        """Initialize the log file."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f'=== Minecraft Launcher Log Started at {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n')
        except Exception as e:
            logger.error(f"Failed to initialize log file: {e}")
    
    def _check_java_installation(self) -> bool:
        """Check if Java is available."""
        java_path = self.config.get('java_path', 'java')
        try:
            result = subprocess.run([java_path, '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"Java found: {java_path}")
                return True
        except Exception as e:
            logger.error(f"Java check failed: {e}")
        
        # Try common Java paths on Windows
        if sys.platform == 'win32':
            common_paths = [
                r'C:\Program Files\Java\jre*\bin\java.exe',
                r'C:\Program Files (x86)\Java\jre*\bin\java.exe',
                r'C:\Program Files\Eclipse Adoptium\jdk*\bin\java.exe'
            ]
            
            import glob
            for pattern in common_paths:
                matches = glob.glob(pattern)
                if matches:
                    java_path = matches[-1]  # Use latest version
                    try:
                        result = subprocess.run([java_path, '-version'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            logger.info(f"Java found at: {java_path}")
                            self.config['java_path'] = java_path
                            return True
                    except Exception:
                        continue
        
        logger.error("Java not found. Please install Java or specify java_path in config.")
        return False

# Legacy global variables for backward compatibility
USERNAME = 'TheDocingEast'
MINECRAFT_VERSION = '1.20.1'
MEMORY_GB = 4
MINECRAFT_DIR = 'minecraft'
LOADER = 'fabric'
LOG_FILE = 'latest.log'

# Legacy global state
game_lock = Lock()
is_game_running = False
game_process = None

def ensure_customskinloader(minecraft_dir, mc_version='1.20.1', loader='fabric'):
    """Безопасная установка CustomSkinLoader с обработкой ошибок."""
    mods_dir = os.path.join(minecraft_dir, 'mods')
    os.makedirs(mods_dir, exist_ok=True)
    api_url = 'https://api.modrinth.com/v2/project/customskinloader/version'
    try:
        logger.info('Запрос к Modrinth API для поиска CustomSkinLoader...')
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        versions = response.json()
        for v in versions:
            if mc_version in v['game_versions'] and loader in v['loaders']:
                for file in v['files']:
                    if file['filename'].endswith('.jar'):
                        jar_url = file['url']
                        jar_path = os.path.join(mods_dir, file['filename'])
                        if not os.path.isfile(jar_path):
                            logger.info(f'Скачивание CustomSkinLoader: {jar_url}')
                            r = requests.get(jar_url, timeout=30)
                            with open(jar_path, 'wb') as f:
                                f.write(r.content)
                            logger.info('CustomSkinLoader скачан.')
                        else:
                            logger.info('CustomSkinLoader уже установлен.')
                        return
        logger.error(f'Не удалось найти подходящую версию CustomSkinLoader для вашей версии Minecraft и лоадера {loader}.')
    except Exception as e:
        logger.error(f'Ошибка при работе с Modrinth API: {e}')

def get_fabric_loader_version_safe():
    """Безопасное получение версии Fabric loader с fallback."""
    # Список известных стабильных версий Fabric loader
    FALLBACK_FABRIC_VERSIONS = [
        "0.15.11",  # Последняя стабильная на момент написания
        "0.15.10",
        "0.15.9",
        "0.15.7",
        "0.14.25"
    ]
    
    try:
        logger.info('Попытка получить последнюю версию Fabric loader...')
        fabric_loader = mclib.fabric.get_latest_loader_version()
        logger.info(f'Получена версия Fabric loader: {fabric_loader}')
        return fabric_loader
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, 
            requests.exceptions.Timeout, Exception) as e:
        logger.warning(f'Не удалось получить последнюю версию Fabric loader: {e}')
        logger.info('Используем резервную версию Fabric loader...')
        
        # Пробуем исполь��овать fallback версии
        for version in FALLBACK_FABRIC_VERSIONS:
            try:
                logger.info(f'Попытка использовать Fabric loader версии: {version}')
                return version
            except Exception:
                continue
        
        # Если ничего не работает, используем самую стабильную версию
        fallback_version = FALLBACK_FABRIC_VERSIONS[0]
        logger.info(f'Используем резервную версию Fabric loader: {fallback_version}')
        return fallback_version

def launch_game():
    global is_game_running, game_process
    try:
        with game_lock:
            if is_game_running:
                logger.warning('Игра уже запущена!')
                return
            is_game_running = True

        # Автоматически скачиваем CustomSkinLoader через Modrinth API с учётом лоадера
        try:
            ensure_customskinloader(MINECRAFT_DIR, MINECRAFT_VERSION, LOADER)
        except Exception as e:
            logger.warning(f'Не удалось установить CustomSkinLoader: {e}')

        # Получаем актуальный никнейм из конфига
        try:
            config_data = load_config("config.json")
            actual_username = config_data.get("nickname", USERNAME)
        except Exception as e:
            logger.warning(f"Не удалось загрузить конфиг: {e}")
            actual_username = USERNAME
        logger.info(f'Запуск Minecraft для пользователя: {actual_username}')
        
        # Безопасное пол��чение версии Fabric loader
        fabric_loader = get_fabric_loader_version_safe()
        
        logger.info(f'Установка Fabric Loader: {fabric_loader} для версии {MINECRAFT_VERSION}')
        
        # Безопасная установка Fabric
        try:
            mclib.fabric.install_fabric(
                MINECRAFT_VERSION,
                loader_version=fabric_loader,
                minecraft_directory=MINECRAFT_DIR
            )
            logger.info('Fabric успешно установлен')
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout) as e:
            logger.warning(f'Ошибка SSL/сети при установке Fabric: {e}')
            logger.info('Пропускаем установку Fabric, возможно он уже установлен...')
        except Exception as e:
            logger.warning(f'Ошибка при установке Fabric: {e}')
        
        # Безопасная установка Minecraft
        try:
            mclib.install.install_minecraft_version(
                f"fabric-loader-{fabric_loader}-{MINECRAFT_VERSION}",
                minecraft_directory=MINECRAFT_DIR
            )
            logger.info('Minecraft с Fabric успешно установлен')
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout) as e:
            logger.warning(f'Ошибка SSL/сети при установке Minecraft: {e}')
            logger.info('Пропускаем установку Minecraft, возможно он уже установлен...')
        except Exception as e:
            logger.warning(f'Ошибка при установке Minecraft: {e}')
        
        # Загружаем никнейм из конфига через импортированную функцию
        try:
            config_data = load_config("config.json")
            nickname = config_data.get("nickname", USERNAME)
            ram_value = config_data.get("ram", MEMORY_GB)
        except Exception as ex:
            logger.warning(f"Не удалось загрузить конфиг, используем значения по умолчанию: {ex}")
            nickname = USERNAME
            ram_value = MEMORY_GB
        
        options = {
            "username": nickname,
            "username": USERNAME,
            "uuid": "",
            "token": "",
            "executablePath": "java",
            "jvmArguments": [f"-Xmx{MEMORY_GB * 1024}M"],
            "launcherVersion": "0.0.1"
        }
        
        # Безопасное создание команды запуска
        try:
            command = mclib.command.get_minecraft_command(
                f"fabric-loader-{fabric_loader}-{MINECRAFT_VERSION}",
                MINECRAFT_DIR,
                options
            )
            logger.info('Команда запуска с Fabric создана успешно')
        except Exception as e:
            logger.warning(f'Ошибка создания команды с Fabric: {e}')
            logger.info('Попытка запуска vanilla вер��ии...')
            try:
                # Устанавливаем vanilla версию если Fabric не работает
                mclib.install.install_minecraft_version(
                    MINECRAFT_VERSION,
                    minecraft_directory=MINECRAFT_DIR,
                    callback = {
                        "setStatus": lambda value: status_progress_bar(None, value),
                        "setProgress": lambda value: current_progress_bar(None, value),
                        "setMax": lambda value: max_progress_bar(None, value)
                    }
                )
                command = mclib.command.get_minecraft_command(
                    MINECRAFT_VERSION,
                    MINECRAFT_DIR,
                    options,
                )
                logger.info('Команда запуска vanilla создана успешно')
            except Exception as e2:
                logger.error(f'Не удалось создать команду запуска даже для vanilla: {e2}')
                raise e2
        
        logger.info(f'Команда запуска: {command}')
        game_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Логирование вывода процесса
        with open(LOG_FILE, 'a', encoding='utf-8') as logf:
            while game_process.poll() is None:
                output = game_process.stdout.readline()
                if output == '' and game_process.poll() is not None:
                    break
                if output:
                    logger.info(output.strip())
                    logf.write(output)
        logger.info('Minecraft завершил работу.')
    except Exception as ex:
        logger.exception(f'Ошибка запуска Minecraft: {ex}')
    finally:
        with game_lock:
            is_game_running = False
            game_process = None

def main():
    launch_game()

if __name__ == "__main__":
    main()