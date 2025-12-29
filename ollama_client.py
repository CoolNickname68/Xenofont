# ollama_client.py
import aiohttp
import asyncio
import json
from typing import AsyncGenerator, List
import re

class OllamaClient:
    def __init__(self, base_url: str = "http://192.168.1.155:11434/", default_model: str = "gemma2:2b"):
        self.base_url = base_url
        self.default_model = default_model
        self.session = None
        
    async def ensure_session(self):
        """Создает сессию если ее нет"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))
    
    async def close(self):
        """Закрывает сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def ask_stream(self, prompt: str, model: str = None) -> AsyncGenerator[str, None]:
        """
        Потоковый запрос с интеллектуальным разбиением на фразы
        Возвращает законченные фразы для озвучки
        """
        await self.ensure_session()
        
        url = f"{self.base_url}api/generate"
        model = model or self.default_model
        
        # Системный промпт для голосового ассистента
        system_prompt = """Ты - голосовой ассистент Ксенофонт. Отвечай ясно и кратко, 
        используй законченные предложения. Отвечай на русском языке.
        Если вопрос непонятен, уточни или предложи помощь."""
        
        full_prompt = f"{system_prompt}\n\nПользователь: {prompt}\nАссистент:"
        
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "num_predict": 500,
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        buffer = ""
        sentence_terminators = ['.', '!', '?', ';', ':', ',', '\n']
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    yield f"Ошибка API: {response.status}"
                    return
                
                async for line in response.content:
                    if line:
                        try:
                            decoded = line.decode('utf-8').strip()
                            if not decoded:
                                continue
                                
                            # Парсим JSON
                            if decoded.startswith('data: '):
                                data = json.loads(decoded[6:])
                            else:
                                data = json.loads(decoded)
                            
                            chunk = data.get("response", "")
                            
                            if chunk:
                                buffer += chunk
                                
                                # Проверяем, есть ли законченные предложения в буфере
                                for terminator in sentence_terminators:
                                    if terminator in buffer:
                                        # Разбиваем по терминаторам
                                        parts = re.split(f'([{re.escape("".join(sentence_terminators))}])', buffer)
                                        
                                        # Отдаем все законченные предложения
                                        i = 0
                                        while i < len(parts) - 1:
                                            sentence = parts[i] + parts[i+1]
                                            if sentence.strip():
                                                yield sentence.strip()
                                            i += 2
                                        
                                        # Оставляем незаконченную часть в буфере
                                        if i < len(parts):
                                            buffer = parts[i]
                                        else:
                                            buffer = ""
                                        break
                                
                                # Если ответ завершен, отдаем остаток
                                if data.get("done", False) and buffer.strip():
                                    yield buffer.strip()
                                    buffer = ""
                                    break
                                    
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"[OLLAMA] Ошибка обработки чанка: {e}")
                            continue
                            
        except asyncio.TimeoutError:
            yield "Извините, запрос занял слишком много времени"
        except Exception as e:
            print(f"[OLLAMA] Ошибка соединения: {e}")
            yield "Ошибка соединения с языковой моделью"
    
    async def ask_fast(self, prompt: str, model: str = None) -> str:
        """
        Быстрый запрос для коротких ответов
        """
        await self.ensure_session()
        
        url = f"{self.base_url}api/generate"
        model = model or self.default_model
        
        system_prompt = """Ты - голосовой ассистент Ксенофонт. 
        Отвечай кратко, но полно, 1-3 предложениями. 
        Не используй markdown-разметку. 
        Отвечай только на русском языке."""
        
        full_prompt = f"{system_prompt}\n\nВопрос: {prompt}\nОтвет:"
        
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": 300,
                "temperature": 0.3,
                "top_p": 0.8,
                "repeat_penalty": 1.1
            }
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get("response", "Нет ответа.").strip()
                    
                    # Очищаем ответ
                    answer = re.sub(r'\*\*(.*?)\*\*', r'\1', answer)
                    answer = re.sub(r'\*(.*?)\*', r'\1', answer)
                    answer = re.sub(r'`(.*?)`', r'\1', answer)
                    answer = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', answer)
                    answer = ' '.join(answer.split())
                    
                    return answer
                else:
                    error_text = await response.text()
                    print(f"[OLLAMA] Ошибка {response.status}: {error_text[:100]}")
                    return f"Ошибка API: {response.status}"
                    
        except asyncio.TimeoutError:
            return "Извините, запрос занял слишком много времени"
        except Exception as e:
            print(f"[OLLAMA] Ошибка: {e}")
            return f"Ошибка: {str(e)[:50]}"

# Создаем глобальный экземпляр клиента
client = OllamaClient()

# Функции для обратной совместимости
async def ask_llama_stream(prompt: str, model: str = None) -> AsyncGenerator[str, None]:
    async for chunk in client.ask_stream(prompt, model):
        yield chunk

async def ask_llama_fast(prompt: str, model: str = None) -> str:
    return await client.ask_fast(prompt, model)

ask_llama = ask_llama_fast