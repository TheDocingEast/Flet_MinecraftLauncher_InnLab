import flet as ft
import subprocess
import sys
import json
import os
import shutil
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('launcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration loading, validation, and saving."""
    
    DEFAULT_CONFIG = {
        "ram": 4,
        "skin": "",
        "nickname": "Player",
        "theme": "dark",
        "auto_update": True,
        "java_path": "",
        "window_width": 1200,
        "window_height": 800
    }
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                if not isinstance(config, dict):
                    logger.warning("Invalid config format, using defaults")
                    return ConfigManager.DEFAULT_CONFIG.copy()
                
                # Validate and sanitize config values
                validated_config = ConfigManager.DEFAULT_CONFIG.copy()
                
                # Validate RAM
                ram = config.get("ram", 4)
                if isinstance(ram, (int, float)) and 2 <= ram <= 32:
                    validated_config["ram"] = ram
                
                # Validate skin path
                skin = config.get("skin", "")
                if isinstance(skin, str):
                    validated_config["skin"] = skin
                
                # Validate nickname
                nickname = config.get("nickname", "Player")
                if isinstance(nickname, str) and len(nickname.strip()) > 0:
                    validated_config["nickname"] = nickname.strip()
                
                # Validate other settings
                for key in ["theme", "java_path"]:
                    if key in config and isinstance(config[key], str):
                        validated_config[key] = config[key]
                
                for key in ["auto_update"]:
                    if key in config and isinstance(config[key], bool):
                        validated_config[key] = config[key]
                
                for key in ["window_width", "window_height"]:
                    if key in config and isinstance(config[key], (int, float)):
                        validated_config[key] = max(600, int(config[key]))
                
                return validated_config
                
        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            logger.error(f"Error loading config: {e}")
        
        return ConfigManager.DEFAULT_CONFIG.copy()
    
    @staticmethod
    def save_config(config_path: str, config: Dict[str, Any]) -> bool:
        """Save configuration to file with validation."""
        try:
            # Validate config before saving
            validated_config = {}
            
            # Validate RAM
            ram = config.get("ram", 4)
            if isinstance(ram, (int, float)) and 2 <= ram <= 32:
                validated_config["ram"] = ram
            else:
                validated_config["ram"] = 4
            
            # Validate other fields
            for key, default in ConfigManager.DEFAULT_CONFIG.items():
                if key == "ram":
                    continue
                value = config.get(key, default)
                if isinstance(value, type(default)):
                    validated_config[key] = value
                else:
                    validated_config[key] = default
            
            # Ensure directory exists
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(validated_config, f, ensure_ascii=False, indent=2)
            
            # Copy skin file if specified
            skin_path = validated_config.get("skin", "")
            if skin_path and Path(skin_path).is_file():
                try:
                    minecraft_dir = Path("minecraft")
                    minecraft_dir.mkdir(exist_ok=True)
                    shutil.copy2(skin_path, minecraft_dir / "skin.png")
                    logger.info(f"Skin copied to minecraft/skin.png")
                except (IOError, OSError) as e:
                    logger.error(f"Error copying skin: {e}")
            
            return True
            
        except (IOError, UnicodeEncodeError) as e:
            logger.error(f"Error saving config: {e}")
            return False

def load_config(config_path):
    """Legacy function for backward compatibility."""
    return ConfigManager.load_config(config_path)

def save_config(config_path, ram_value, skin_value, nickname_value="Player"):
    """Legacy function for backward compatibility."""
    config = {
        "ram": ram_value,
        "skin": skin_value,
        "nickname": nickname_value
    }
    return ConfigManager.save_config(config_path, config)

class ModpackCard:
    """Represents a modpack card with improved error handling and validation."""
    
    def __init__(self, page: ft.Page, icon: str, name: str, description: str, version: str, last_update: int, index: int):
        self.page = page
        self.name = str(name).strip() if name else "Unnamed Modpack"
        self.desc = str(description).strip() if description else "No description available"
        self.ver = str(version).strip() if version else "Unknown"
        self.update = int(last_update) if isinstance(last_update, (int, float)) else 0
        self.index = int(index) if isinstance(index, (int, float)) else 0
        self.iconname = str(icon).strip() if icon else "default"
        
        # Validate inputs
        if len(self.name) > 50:
            self.name = self.name[:47] + "..."
        if len(self.desc) > 200:
            self.desc = self.desc[:197] + "..."

    def create_card(self, show_main_screen, show_settings_screen):
        def open_modpack_window(e):
            def show_modpack_screen(ev=None):
                try:
                    self.page.clean()
                    try:
                        self.page.add(
                            ft.Container(
                                content=(
                                    ft.Image(
                                        src="background.png",
                                        fit=ft.ImageFit.COVER
                                    )
                                )
                            )
                        )
                    except Exception as e:
                        print(f"Ошибка отображения окна модпака: {e}")
                        # Fallback UI без фона
                        self.page.add(
                            ft.Container(
                                padding=ft.padding.all(30),
                                bgcolor=ft.Colors.GREY_900,  # Тёмный фон
                                expand=True
                            )
                        )
                    # Получаем текущий ник из конфига
                    config = load_config("config.json")
                    current_nickname = config.get("nickname", "Player")
                    
                    # Прогресс бар для запуска Minecraft
                    launch_progress = ft.ProgressBar(
                        width=400,
                        height=4,
                        value=0,
                        color=ft.Colors.PURPLE_400,
                        bgcolor=ft.Colors.PURPLE_200,
                        visible=False
                    )
                    
                    def update_launch_progress(progress_value: float, status_text: str = ""):
                        """Обновляет прогресс бар запуска"""
                        try:
                            launch_progress.value = progress_value
                            launch_progress.visible = progress_value > 0
                            if hasattr(self.page, 'bottom_appbar') and self.page.bottom_appbar:
                                # Обновляем текст статуса кнопки "Играть"
                                # Ищем в структуре Column -> Row -> кнопки
                                content = self.page.bottom_appbar.content
                                if hasattr(content, 'controls') and len(content.controls) > 1:
                                    row_controls = content.controls[1]  # Вторая строка с кнопками
                                    if hasattr(row_controls, 'controls'):
                                        for control in row_controls.controls:
                                            if hasattr(control, 'text') and control.text in ["Играть", "Подготовка...", "Проверка файлов...", "Загрузка модов...", "Инициализация Java...", "Запуск Minecraft...", "Запущено!"]:
                                                if progress_value > 0 and progress_value < 1:
                                                    control.text = status_text if status_text else f"Запуск... {int(progress_value * 100)}%"
                                                else:
                                                    control.text = "Играть"
                                                break
                            self.page.update()
                        except Exception as e:
                            logger.error(f"Ошибка обновления прогресса: {e}")
                    
                    def launch_game(ev):
                        try:
                            # Показываем прогресс запуска
                            update_launch_progress(0.1, "Подготовка...")
                            
                            # Симуляция этапов запуска
                            def launch_process():
                                try:
                                    update_launch_progress(0.2, "Проверка файлов...")
                                    time.sleep(0.5)
                                    
                                    update_launch_progress(0.4, "Загрузка модов...")
                                    time.sleep(0.8)
                                    
                                    update_launch_progress(0.6, "Инициализация Java...")
                                    time.sleep(0.5)
                                    
                                    update_launch_progress(0.8, "Запуск Minecraft...")
                                    time.sleep(0.3)
                                    
                                    # Запускаем игру
                                    self.launch_minecraft()
                                    
                                    update_launch_progress(1.0, "Запущено!")
                                    time.sleep(1)
                                    
                                    # Скрываем прогресс бар
                                    update_launch_progress(0, "")
                                    
                                    print(f"Запуск игры для {current_nickname} в сборке {self.name}")
                                except Exception as ex:
                                    update_launch_progress(0, "")
                                    print(f"Ошибка запуска игры: {ex}")
                            
                            # Запускаем в ��тдельном потоке
                            threading.Thread(target=launch_process, daemon=True).start()
                            
                        except Exception as ex:
                            update_launch_progress(0, "")
                            print(f"Ошибка запуска игры: {ex}")
                    
                    def check_updates(ev):
                        try:
                            print(f"Проверка обновлений для сборки {self.name}")
                            # Здесь можно добавить логику проверки обновлений
                        except Exception as ex:
                            print(f"Ошибка проверки обновлений: {ex}")
                    
                    def open_minecraft_folder(ev):
                        try:
                            minecraft_path = os.path.abspath("minecraft")
                            if os.path.exists(minecraft_path):
                                if sys.platform == "win32":
                                    os.startfile(minecraft_path)
                                elif sys.platform == "darwin":
                                    subprocess.run(["open", minecraft_path])
                                else:
                                    subprocess.run(["xdg-open", minecraft_path])
                            else:
                                print("Папка minecraft не найдена")
                        except Exception as ex:
                            print(f"Ошибка открытия папки: {ex}")
                    
                    def open_settings(ev):
                        # Очищаем AppBar и BottomAppBar при переходе в настройки
                        self.page.appbar = None
                        self.page.bottom_appbar = None
                        # Передаём функцию возврата в окно сборки
                        show_settings_screen(return_to_modpack=show_modpack_screen)
                    
                    def back_to_main(ev):
                        # Очищаем AppBar и BottomAppBar при возврате
                        self.page.appbar = None
                        self.page.bottom_appbar = None
                        show_main_screen()
                    
                    def show_logs_dialog(ev):
                        """Показывает диалог с логами в реальном времени"""
                        try:
                            # Создаем текстовый элемент для логов
                            log_text = ft.Text(
                                "Загрузка логов...",
                                selectable=True,
                                size=11,
                                color=ft.Colors.PURPLE_200,
                                font_family="Consolas"
                            )
                            
                            # Контейнер для прокрутки
                            log_container = ft.Column([log_text], scroll=ft.ScrollMode.AUTO, height=450, width=750)
                            
                            # Переменные для управления обновлением
                            update_active = True
                            
                            def read_file_safe(file_path):
                                """Безопасное чтение файла с обработкой кодировок"""
                                if not os.path.exists(file_path):
                                    return None
                                
                                # Расширенный список кодировок для Windows
                                encodings = ['utf-8', 'cp1251', 'cp866', 'windows-1251', 'latin-1', 'utf-8-sig', 'ascii']
                                
                                for encoding in encodings:
                                    try:
                                        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                                            content = f.read()
                                            # Дополнительная очистка проблемных символов
                                            content = content.replace('\x00', '')  # Удаляем null байты
                                            return content
                                    except (UnicodeDecodeError, UnicodeError):
                                        continue
                                    except Exception:
                                        break
                                
                                # Если ничего не сработало, читаем как бинарный и декодируем с заменой ошибок
                                try:
                                    with open(file_path, 'rb') as f:
                                        content = f.read()
                                        # Пробуем разные кодировки для бинарных данных
                                        for encoding in ['utf-8', 'cp1251', 'cp866']:
                                            try:
                                                decoded = content.decode(encoding, errors='replace')
                                                return decoded.replace('\x00', '')
                                            except:
                                                continue
                                        return content.decode('utf-8', errors='replace').replace('\x00', '')
                                except Exception as e:
                                    return f"Ошибка чтения файла {file_path}: {str(e)}"
                            
                            def update_logs():
                                """Обновляет содержимое логов"""
                                nonlocal update_active
                                
                                while update_active:
                                    try:
                                        log_content = ""
                                        log_files = ["launcher.log", "minecraft_launcher.log", "latest.log"]
                                        
                                        for log_file in log_files:
                                            if os.path.exists(log_file):
                                                try:
                                                    content = read_file_safe(log_file)
                                                    if content and content.strip():
                                                        # Ограничиваем размер лога для производительности
                                                        lines = content.split('\n')
                                                        if len(lines) > 1000:
                                                            lines = ["... (показаны последние 1000 строк) ..."] + lines[-1000:]
                                                            content = '\n'.join(lines)
                                                        
                                                        log_content += f"=== {log_file} ===\n{content}\n\n"
                                                    elif content is not None:
                                                        log_content += f"=== {log_file} (пустой) ===\n\n"
                                                    
                                                except Exception as e:
                                                    log_content += f"=== Ошибка чтения {log_file} ===\n{str(e)}\n\n"
                                            else:
                                                log_content += f"=== {log_file} (файл не найден) ===\n\n"
                                        
                                        if not log_content.strip():
                                            log_content = "Логи не найдены или пусты."
                                        
                                        # Добавляем временную метку
                                        timestamp = time.strftime("%H:%M:%S")
                                        log_content = f"Последнее обновление: {timestamp}\n\n{log_content}"
                                        
                                        # Обновляем текст
                                        log_text.value = log_content
                                        
                                        # Обновляем страницу
                                        try:
                                            self.page.update()
                                        except:
                                            break
                                        
                                        time.sleep(2)  # Обновляем каждые 2 секунды
                                        
                                    except Exception as e:
                                        print(f"Ошибка обновления логов: {e}")
                                        time.sleep(3)
                            
                            def close_dialog(e):
                                nonlocal update_active
                                update_active = False
                                self.page.close(logs_dialog)
                            
                            def manual_refresh(e):
                                """Принудительное обновление логов"""
                                try:
                                    log_content = ""
                                    log_files = ["launcher.log", "minecraft_launcher.log", "latest.log"]
                                    
                                    for log_file in log_files:
                                        content = read_file_safe(log_file)
                                        if content and content.strip():
                                            lines = content.split('\n')
                                            if len(lines) > 1000:
                                                lines = ["... (показаны последние 1000 строк) ..."] + lines[-1000:]
                                                content = '\n'.join(lines)
                                            log_content += f"=== {log_file} ===\n{content}\n\n"
                                        elif content is not None:
                                            log_content += f"=== {log_file} (пустой) ===\n\n"
                                        else:
                                            log_content += f"=== {log_file} (файл не найден) ===\n\n"
                                    
                                    timestamp = time.strftime("%H:%M:%S")
                                    log_content = f"Принудительное обновление: {timestamp}\n\n{log_content}"
                                    log_text.value = log_content
                                    self.page.update()
                                except Exception as ex:
                                    print(f"Ошибка принудительного обновления: {ex}")
                            
                            # Создаем диалог с логами
                            logs_dialog = ft.AlertDialog(
                                modal=True,
                                title=ft.Row([
                                    ft.Text("Логи лаунчера", color=ft.Colors.PURPLE_100, size=16, weight=ft.FontWeight.BOLD),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.REFRESH,
                                            tooltip="Обновить сейчас",
                                            on_click=manual_refresh,
                                            icon_color=ft.Colors.GREEN_400,
                                            icon_size=20
                                        )
                                    ])
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                content=ft.Container(
                                    content=log_container,
                                    bgcolor=ft.Colors(0.98, ft.Colors.BLACK),
                                    padding=ft.padding.all(15),
                                    border_radius=ft.border_radius.all(8),
                                    border=ft.border.all(1, ft.Colors.PURPLE_400)
                                ),
                                actions=[
                                    ft.Row([
                                        ft.Text("Автообновление каждые 2 сек", size=11, color=ft.Colors.GREEN_300),
                                        ft.TextButton(
                                            "Закрыть",
                                            on_click=close_dialog,
                                            style=ft.ButtonStyle(color=ft.Colors.PURPLE_300)
                                        )
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                ],
                                bgcolor=ft.Colors(0.98, ft.Colors.BLACK),
                                actions_alignment=ft.MainAxisAlignment.END
                            )
                            
                            # Запускаем поток обновления логов
                            log_thread = threading.Thread(target=update_logs, daemon=True)
                            log_thread.start()
                            
                            self.page.open(logs_dialog)
                            
                        except Exception as e:
                            print(f"Ошибка открытия логов: {e}")
                    
                    # TextField для ввода ника
                    nickname_input = ft.TextField(
                        value=current_nickname,
                        hint_text="Введите ник",
                        width=500,
                        height=40,
                        text_size=14,
                        color=ft.Colors.PURPLE_100,
                        bgcolor=ft.Colors.BLACK,
                        border_color=ft.Colors.PURPLE_300,
                        focused_border_color=ft.Colors.PURPLE_200,
                        offset=ft.Offset(0.03,0.1)
                    )
                    
                    def save_nickname(ev):
                        try:
                            new_nickname = nickname_input.value if nickname_input.value else "Player"
                            save_config("config.json", config.get("ram", 4), config.get("skin", ""), new_nickname)
                            print(f"Ник изменён на: {new_nickname}")
                        except Exception as ex:
                            print(f"Ошибка сохранения ника: {ex}")
                    
                    nickname_input.on_submit = save_nickname
                    nickname_input.on_blur = save_nickname
                    
                    # Устанавливаем AppBar с TextField для ника и кнопкой логов
                    self.page.appbar = ft.AppBar(
                        leading=nickname_input,
                        title=ft.Text(f"Сборка: {self.name}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_100,overflow=ft.TextOverflow.ELLIPSIS),
                        center_title=False,
                        actions=[
                            ft.IconButton(
                                icon=ft.Icons.ARTICLE,
                                tooltip="Логи (реальное время)",
                                on_click=show_logs_dialog,
                                icon_color=ft.Colors.PURPLE_300
                            ),
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                tooltip="Назад",
                                on_click=back_to_main,
                                icon_color=ft.Colors.PURPLE_300
                            )
                        ],
                        leading_width=300,
                        adaptive=True,
                        bgcolor="#1a0d26",
                        toolbar_height=60# Очень тёмно-фиолетовый
                    )
                    
                    # Устанавливаем BottomAppBar с прогресс баром сверху
                    self.page.bottom_appbar = ft.BottomAppBar(
                        content=ft.Column([
                            # Прогресс бар сверху
                            ft.Container(
                                content=launch_progress,
                                padding=ft.padding.only(left=20, right=20, top=5),
                                alignment=ft.alignment.center
                            ),
                            # Кнопки снизу
                            ft.Row([
                                ft.ElevatedButton(
                                    text="Обновления",
                                    icon=ft.Icons.UPDATE,
                                    on_click=check_updates,
                                    style=ft.ButtonStyle(
                                        bgcolor="#2d1b3d",  # Очень тёмно-фиолетовый
                                        color=ft.Colors.PURPLE_100
                                    )
                                ),
                                ft.ElevatedButton(
                                    text="Папка игры",
                                    icon=ft.Icons.FOLDER_OPEN,
                                    on_click=open_minecraft_folder,
                                    style=ft.ButtonStyle(
                                        bgcolor="#2d1b3d",  # Очень тёмно-фиолетовый
                                        color=ft.Colors.PURPLE_100
                                    )
                                ),
                                ft.ElevatedButton(
                                    text="Настройки",
                                    icon=ft.Icons.SETTINGS,
                                    on_click=open_settings,
                                    style=ft.ButtonStyle(
                                        bgcolor="#2d1b3d",  # Очень тёмно-фиолетовый
                                        color=ft.Colors.PURPLE_100
                                    )
                                ),
                                ft.ElevatedButton(
                                    text="Играть",
                                    icon=ft.Icons.PLAY_ARROW,
                                    on_click=launch_game,
                                    style=ft.ButtonStyle(
                                        bgcolor="#2d1b3d",  # Очень тёмно-фиолетовый
                                        color=ft.Colors.PURPLE_100
                                    )
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_EVENLY)
                        ],
                        spacing=0,
                        tight=True),
                        bgcolor="#1a0d26",  # Очень тёмно-фиолетовый
                    )
                    
                    self.page.update()
                except Exception as e:
                    print(f"Ошибка в show_modpack_screen: {e}")
                    show_main_screen()
            
            show_modpack_screen()
        
        # Безопасные размеры карточек
        try:
            page_height = getattr(self.page, 'height', 600)
            card_width = min(300, max(200, page_height // 2))
            card_height = min(500, max(400, int(page_height * 0.8)))
        except:
            card_width = 250
            card_height = 450
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column([
                        ft.Container(
                            content=ft.Image(
                                src=f"{self.iconname}" if self.iconname else "icon.png",
                                width=140,
                                height=140,
                                fit=ft.ImageFit.COVER,
                                error_content=ft.Container(
                                    width=140,
                                    height=140,
                                    bgcolor=ft.Colors.GREY_900,  # Тёмный фон
                                    content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color=ft.Colors.PURPLE_300)
                                )
                            ),
                            width=140,
                            height=140,
                            border_radius=ft.border_radius.all(70),
                            clip_behavior=ft.ClipBehavior.HARD_EDGE
                        ),
                        ft.Text(self.name, weight=ft.FontWeight.BOLD, size=20, text_align=ft.TextAlign.CENTER, width=150, color=ft.Colors.PURPLE_100),
                        ft.Text(f"Описание: {self.desc}", size=14, text_align=ft.TextAlign.CENTER, width=150, color=ft.Colors.PURPLE_200),
                        ft.Text(f"Версия майнкрафт: {self.ver}", size=14, text_align=ft.TextAlign.CENTER, width=150, color=ft.Colors.PURPLE_200)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Column([
                        ft.IconButton(
                            icon=ft.Icons.PLAY_CIRCLE,
                            icon_color=ft.Colors.PURPLE_400,
                            icon_size=70,
                            on_click=open_modpack_window,
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            border=ft.border.all(2, "#492058"),  # Очень тёмная фи��летовая граница
            border_radius=ft.border_radius.all(8),
            padding=ft.padding.all(20),
            width=card_width,
            height=card_height,
            bgcolor=ft.Colors.TRANSPARENT,
            blur=ft.Blur(2,2,ft.BlurTileMode.MIRROR)
        )

    def launch_minecraft(self):
        try:
            if os.path.exists('src/launcher.py'):
                subprocess.Popen([sys.executable, 'src/launcher.py'])
            else:
                print("Файл launcher.py не найден")
        except Exception as e:
            print(f"Ошибка запуска Minecraft: {e}")

def main(page: ft.Page):
    try:
        page.padding=2
        page.title = "InnLab³ Launcher"
        page.window.width=800
        page.window.height=600
        page.window.resizable=False
        page.window.icon="InnLabIcon.png"
        pagebg = ft.Container(
                content=ft.Image(
                    src="InnLabIconMax.png",
                    fit=ft.ImageFit.CONTAIN
                ),
                alignment=ft.alignment.center,
                width=150,
                height=150,
                border_radius=150,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,

        )
        config_path = "config.json"
        config = load_config(config_path)

        ram_slider = ft.Slider(
            min=2, max=16, divisions=14, value=float(config.get("ram", 4)), label="RAM: {value} ГБ", width=300
        )
        skin_path = ft.TextField(
            label="Путь к скину (png)", value=config.get("skin", ""), width=300, read_only=True
        )
        nickname_field = ft.TextField(
            label="Ник в игре", value=config.get("nickname", "Player"), width=300
        )
        skin_file_picker = ft.FilePicker()
        
        def pick_skin_result(e):
            try:
                if skin_file_picker.result and skin_file_picker.result.files:
                    file = skin_file_picker.result.files[0]
                    skin_path.value = file.path
                    page.update()
            except Exception as ex:
                print(f"Ошибка выбора скина: {ex}")
        
        skin_file_picker.on_result = pick_skin_result
        page.overlay.append(skin_file_picker)

        def open_skin_picker(e):
            try:
                skin_file_picker.pick_files(allow_multiple=False, allowed_extensions=["png"])
            except Exception as ex:
                print(f"Ошибка открытия диалога выбора файла: {ex}")

        def show_settings_screen(e=None, return_to_modpack=None):
            try:
                page.clean()
                # Очищаем AppBar и BottomAppBar в настройках
                page.appbar = None
                page.bottom_appbar = None
                
                # Определяем функцию возврата
                if return_to_modpack:
                    back_function = return_to_modpack
                else:
                    back_function = show_main_screen
                
                save_btn = ft.ElevatedButton(
                    "Сохранить",
                    on_click=lambda e: (save_config(config_path, ram_slider.value, skin_path.value, nickname_field.value), back_function()),
                    style=ft.ButtonStyle(bgcolor="#2d1b3d", color=ft.Colors.PURPLE_100)  # Очень тёмно-фиолетовый
                )
                back_btn = ft.TextButton("Назад", on_click=lambda e: back_function(), style=ft.ButtonStyle(bgcolor="#2d1b3d", color=ft.Colors.PURPLE_100))
                page.add(
                    ft.Container(
                        ft.Column([
                            ft.Text("Настройки Minecraft", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_100),
                            nickname_field,
                            ram_slider,
                            ft.Row([
                                skin_path,
                                ft.IconButton(icon=ft.Icons.UPLOAD_FILE, on_click=open_skin_picker, icon_color=ft.Colors.PURPLE_300)
                            ]),
                            ft.Row([save_btn, back_btn], alignment=ft.MainAxisAlignment.END)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20
                        ),
                        padding=30,
                        alignment=ft.alignment.center,
                        bgcolor=ft.Colors.GREY_900  # Тёмный фон
                    )
                )
                page.update()
            except Exception as ex:
                print(f"Ошибка в show_settings_screen: {ex}")

        def show_main_screen(e=None):
            try:
                page.clean()
                # Очищаем AppBar и BottomAppBar на главном экране
                page.appbar = None
                page.bottom_appbar = None
                
                # --- Карточки ---
                cards = [
                    ModpackCard(page, "icon.png", "ArcanaTech", "Main mods:\nCreate\nMana and Artiface\nArs Noveau", '1.20.1', 20250630, 1),
                ]
                
                page.add(
                    ft.Container(
                        ft.Stack([
                        pagebg,
                        ft.Container(
                            ft.Row(
                            [card.create_card(show_main_screen, show_settings_screen) for card in cards],
                            spacing=50,
                            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            scroll=ft.ScrollMode.AUTO,
                            offset=ft.Offset(0.1,0),
                            expand=True
                            ),
                            alignment=ft.alignment.center_left,
                            blur=ft.Blur(2,2,ft.BlurTileMode.MIRROR)
                        )
                        ],
                    alignment=ft.alignment.center,
                    expand=True
                    ),
                    bgcolor=ft.Colors.TRANSPARENT,
                    expand=True
                    )  
                ) 
                
                page.update()
            except Exception as ex:
                print(f"Ошибка в show_main_screen: {ex}")

        show_main_screen()
    except Exception as e:
        print(f"Критическая ошибка в main: {e}")

if __name__ == "__main__":
    ft.app(target=main, name="InnLab³", assets_dir="assets")