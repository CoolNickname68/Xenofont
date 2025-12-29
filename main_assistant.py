# main_assistant.py
import speech_recognition as sr
import datetime
import webbrowser
import requests
import time
import random
import os
import asyncio
from urllib.parse import quote
from gtts import gTTS
import playsound3 as playsound

# Импорт модулей
from config import ALIASES, TBR, COMMANDS, OLLAMA_BASE_URL, DEFAULT_MODEL
from ollama_client import ask_llama_stream, ask_llama_fast, client
from system_launcher import launch_program

# Инициализация
r = sr.Recognizer()
m = sr.Microphone()

# Проверяем наличие пакетов
try:
    import queue
    audio_queue = queue.Queue()
except ImportError:
    audio_queue = None

def speak(text):
    """Озвучивание текста"""
    print(f"🤖 Ксенофонт: {text}")
    try:
        tts = gTTS(text=text, lang='ru')
        filename = "temp_speech.mp3"
        tts.save(filename)
        playsound.playsound(filename)
        os.remove(filename)
    except Exception as e:
        print(f"⚠️ Ошибка озвучки: {e}")

async def speak_streaming(stream_generator):
    """Озвучивание потокового ответа по предложениям"""
    try:
        async for sentence in stream_generator:
            if sentence and sentence.strip():
                speak(sentence.strip())
                # Небольшая пауза между предложениями для естественности
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"⚠️ Ошибка потоковой озвучки: {e}")
        speak("Произошла ошибка при обработке ответа")

def listen_command():
    """Слушаем голосовую команду"""
    try:
        with m as source:
            print("🎤 >>> Слушаю...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
        
        try:
            command = r.recognize_google(audio, language="ru-RU").lower()
            print(f"👤 Вы сказали: {command}")
            return command
        except sr.UnknownValueError:
            print("Я вас не понял")
            return None
        except sr.RequestError:
            speak("Ошибка соединения с сервисом распознавания")
            return None
    except sr.WaitTimeoutError:
        return None
    except Exception as e:
        print(f"⚠️ Ошибка при прослушивании: {e}")
        return None

def extract_command(text):
    """Извлечение команды из текста с учетом алиасов"""
    text = text.lower()
    
    # Проверяем алиасы
    for alias in ALIASES:
        if alias in text:
            # Убираем алиас из текста
            text = text.replace(alias, '').strip()
            break
    
    # Проверяем TBR (to be removed) слова
    for word in TBR:
        if text.startswith(word):
            text = text.replace(word, '', 1).strip()
            break
    
    return text

async def handle_llama_request(command):
    """Обработка запроса через Ollama"""
    try:
        speak("Думаю...")
        
        # Используем потоковый режим для более естественного ответа
        stream_generator = ask_llama_stream(command)
        
        # Запускаем потоковую озвучку
        await speak_streaming(stream_generator)
        
    except Exception as e:
        print(f"⚠️ Ошибка при обращении к Ollama: {e}")
        # Пробуем быстрый запрос как fallback
        try:
            response = await ask_llama_fast(command)
            speak(response)
        except:
            speak("Извините, не могу получить ответ от языковой модели")

async def process_command(command):
    """Обработка команд"""
    if not command:
        return False
    
    # Извлекаем чистую команду
    clean_command = extract_command(command)
    
    # Команды выхода
    exit_words = ['стоп', 'выход', 'пока', 'до свидания', 'заверши работу']
    if any(word in clean_command for word in exit_words):
        speak("До свидания! Рад был помочь")
        await client.close()
        return True
    
    # Приветствие
    if any(word in clean_command for word in ['привет', 'здравствуй', 'добрый день', 'доброе утро']):
        greetings = [
            "Привет! Чем могу помочь?",
            "Здравствуйте! Готов к вашим командам.",
            "Приветствую! Слушаю вас."
        ]
        speak(random.choice(greetings))
    
    # Как дела
    elif any(phrase in clean_command for phrase in ['как дела', 'как ты', 'как настроение']):
        responses = [
            "У меня всё отлично, спасибо что спросили!",
            "Работаю в штатном режиме!",
            "Всё хорошо, готов помогать!",
            "Как у цифрового ассистента - отлично!"
        ]
        speak(random.choice(responses))
    
    # Время
    elif any(phrase in clean_command for phrase in ['время', 'который час', 'сколько времени']):
        now = datetime.datetime.now()
        speak(f"Сейчас {now.hour} часов {now.minute} минут")
    
    # Поиск
    elif any(word in clean_command for word in ['найди', 'ищи', 'поиск', 'найти']):
        query = clean_command
        for word in ['найди', 'ищи', 'поиск', 'найти']:
            query = query.replace(word, '').strip()
        
        if query:
            speak(f"Ищу информацию о {query}")
            url = f'https://ru.wikipedia.org/wiki/{quote(query)}'
            webbrowser.open(url)
            time.sleep(0.5)
            speak("Открываю результаты поиска")
        else:
            speak("Что именно вы хотите найти?")
    
    # Браузер
    elif any(phrase in clean_command for phrase in ['открой браузер', 'браузер', 'интернет']):
        speak("Открываю браузер")
        webbrowser.open("https://www.google.com")
    
    # Музыка
    elif any(phrase in clean_command for phrase in ['включи музыку', 'музыку', 'радио', 'песни']):
        speak("Включаю музыку")
        webbrowser.open("https://www.youtube.com")
    
    # Анекдот
    elif any(word in clean_command for word in ['анекдот', 'шутку', 'рассмеши', 'пошути']):
        jokes = [
            "Почему программист всегда мокрый? Потому что он постоянно в бассейне с кодом!",
            "Какой язык программирования самый романтичный? Java, потому что у него всегда есть кофе!",
            "Почему Python не хочет идти на вечеринку? Потому что у него слишком много скобок!",
            "Что сказал один байт другому? Я тебя bit!"
        ]
        speak(random.choice(jokes))
    
    # Запуск программ
    elif any(word in clean_command for word in ['запусти', 'открой программу', 'открой приложение']):
        # Извлекаем название программы
        program_name = clean_command
        for word in ['запусти', 'открой программу', 'открой приложение', 'программу', 'приложение']:
            program_name = program_name.replace(word, '').strip()
        
        if program_name:
            result = launch_program(program_name)
            speak(result)
        else:
            speak("Какую программу запустить?")
    
    # Благодарность
    elif 'спасибо' in clean_command:
        speak("Всегда пожалуйста!")
    
    # Имя
    elif any(phrase in clean_command for phrase in ['твое имя', 'зовут', 'как зовут']):
        speak("Меня зовут Ксенофонт")
    
    # Погода (пример расширения)
    elif 'погода' in clean_command:
        speak("К сожалению, функция погоды пока не реализована")
    
    # Если команда не распознана - используем Ollama
    else:
        await handle_llama_request(clean_command)
    
    return False

async def main_async():
    """Асинхронная основная функция"""
    speak("Привет! Я голосовой помощник Ксенофонт.")
    time.sleep(1)
    speak("Готов к работе! Вы можете сказать мне команду.")
    
    # Главный цикл
    while True:
        try:
            # Слушаем команду
            command = listen_command()
            
            if command:
                should_exit = await process_command(command)
                if should_exit:
                    break
            
            # Небольшая пауза между прослушиваниями
            await asyncio.sleep(0.1)
            
        except KeyboardInterrupt:
            speak("Завершаю работу")
            await client.close()
            break
        except Exception as e:
            print(f"⚠️ Критическая ошибка: {e}")
            time.sleep(2)

def main():
    """Точка входа"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nПрограмма завершена")
    except Exception as e:
        print(f"Ошибка при запуске: {e}")

# Запуск программы
if __name__ == "__main__":
    main()