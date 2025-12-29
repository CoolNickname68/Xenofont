# system_launcher.py
import subprocess
import sys
import os
from difflib import SequenceMatcher

# Расширенная картина программ
PROGRAM_MAP = {
    # Windows
    "блокнот": "notepad.exe",
    "калькулятор": "calc.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "браузер": "chrome.exe",  # или firefox.exe
    
    # Linux
    "текстовый редактор": "gedit",
    "терминал": "gnome-terminal",
    "файловый менеджер": "nautilus",
    "браузер хром": "google-chrome",
    "браузер файрфокс": "firefox",
    
    # Общие (попробуем найти)
    "проводник": "explorer.exe" if sys.platform == "win32" else "nautilus",
    "настройки": "control.exe" if sys.platform == "win32" else "gnome-control-center",
}

def find_best_match(user_input: str) -> str:
    """Находит лучший матч для ввода пользователя"""
    best_match = None
    best_ratio = 0.0
    
    for program_name in PROGRAM_MAP.keys():
        ratio = SequenceMatcher(None, user_input.lower(), program_name.lower()).ratio()
        if ratio > best_ratio and ratio > 0.6:  # Порог схожести
            best_ratio = ratio
            best_match = program_name
    
    return best_match

def launch_program(app_name: str) -> str:
    """
    Запускает программу по голосовому запросу.
    Возвращает строку-результат для озвучивания.
    """
    if not app_name or not app_name.strip():
        return "Не указано название программы"
    
    # Ищем лучший матч
    best_match = find_best_match(app_name)
    
    if not best_match:
        # Если точного совпадения нет, попробуем найти по частичному совпадению
        for key in PROGRAM_MAP.keys():
            if any(word in app_name.lower() for word in key.split()):
                best_match = key
                break
    
    if best_match:
        command = PROGRAM_MAP[best_match]
        try:
            if sys.platform == "win32":
                # Для Windows
                if os.path.exists(command) or command.endswith('.exe'):
                    subprocess.Popen(command, shell=True)
                else:
                    # Пробуем найти в PATH
                    subprocess.Popen(f'start {command}', shell=True)
            else:
                # Для Linux
                subprocess.Popen(command.split(), shell=False)
            
            return f"Запускаю {best_match}"
        except FileNotFoundError:
            return f"Не найден файл для {best_match}"
        except Exception as e:
            return f"Ошибка при запуске {best_match}: {e}"
    else:
        # Если программа не найдена, можно предложить добавить ее
        suggestions = []
        for key in PROGRAM_MAP.keys():
            if len(suggestions) < 3:  # Показываем только 3 варианта
                suggestions.append(key)
        
        return f"Не знаю, как запустить '{app_name}'. Доступные программы: {', '.join(suggestions)}"

# Дополнительная функция для добавления программ
def add_program_mapping(name: str, command: str):
    """Добавляет новую программу в карту"""
    PROGRAM_MAP[name.lower()] = command
    print(f"Добавлена программа: {name} -> {command}")