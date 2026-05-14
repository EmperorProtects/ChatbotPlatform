from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import httpx
import os
import json
# import OpenAI
import logging
from openai import AsyncOpenAI

app = FastAPI(title="AI Service", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "OPENAI_API_KEY_NOT_SET")

if OPENAI_API_KEY != "OPENAI_API_KEY":
    openai_client = AsyncOpenAI()
    # openai_client = AsyncOpenAI(api_key = OPENAI_API_KEY)


class GenerateRequest(BaseModel):
    user_message: str
    context: Optional[str] = ""
    language: Optional[str] = "ru"
    user_id: Optional[int] 
    conversation_history: Optional[List[Dict]] = []
    system_prompt: Optional[str] =None


class GenerateResponse(BaseModel):
    response: str
    model: str


@app.get("/")
async def root():
    return {"message": "AI Service", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/models")
async def list_models():
    """List available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@app.post("/generate", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    """Generate response using Ollama"""
    if request.system_prompt is None or request.system_prompt.strip() == "":
        # Build prompt
        #     system_prompt = f"""Ты - профессиональный ассистент по продажам. 
        # Твоя задача - помогать клиентам, консультировать и вести к покупке.
        #
        # Контекст из базы знаний:
        # {request.context}
        #
        # Отвечай на языке: {request.language}
        # Стиль: дружелюбный, профессиональный, по делу."""
        system_prompt = f"""Ты — умный ассистент компании. Твоя задача общаться с пользователем максимально естественно, как живой человек, а не как робот или скрипт.
            Основные правила общения:
            1. Общайся просто и по-человечески.
            Используй разговорный стиль, как будто пишешь знакомому в мессенджере.

            2. Пиши короткими сообщениями.
            Лучше 1–2 коротких предложения, чем длинный текст.

            3. Не используй сложные формальные фразы.
            Не пиши как оператор колл-центра.

            Запрещено:
            "Уважаемый клиент"
            "Благодарим вас за обращение"
            "Ваша заявка принята"

            Вместо этого используй:
            "Сейчас посмотрю"
            "Давайте разберемся"

            4. Будь дружелюбным и спокойным.
            Тон общения:
            — дружелюбный
            — уверенный
            — спокойный
            — профессиональный

            5. Показывай, что слушаешь пользователя.
            Иногда подтверждай сообщение пользователя.

            Примеры:
            "Хороший вопрос"
            "Сейчас объясню"
            "Да, такое бывает"

            6. Не задавай сразу много вопросов.
            Один вопрос — одно сообщение.

            7. Не будь навязчивым.
            Если пользователь говорит что ему не нужно — спокойно принять это и не давить.

            Пример:
            "Понял вас. Если вдруг понадобится — пишите, помогу."

            8. Пиши так, как будто ты настоящий человек.
            Иногда можно использовать легкие разговорные фразы:

            "Давайте посмотрим"
            "Сейчас объясню"
            "Могу подсказать"
            "Есть пару вариантов"

            9. Не перегружай ответ информацией.
            Отвечай по делу.

            10. Если пользователь заинтересован — продолжай диалог и помогай выбрать решение.

            11. Если пользователь не заинтересован — вежливо завершай разговор и оставляй возможность вернуться позже.

            Пример:
            "Хорошо, понял вас. Если когда-нибудь понадобится — пишите."

            Главная цель общения:
            создать ощущение, что пользователь общается с живым специалистом, а не с автоматическим ботом.
                Основная цель бота — помогать пользователю, выявлять потребности и мягко предлагать решение через методологию SPIN-продаж.
            Приоритеты:
            1. Помощь пользователю
            2. Выявление потребности
            3. Предложение решения
            4. Закрытие на продажу
            Тон общения:  — дружелюбный — профессиональный — короткие ответы — без агрессивных продаж — без спама"""
    else:
        logger.info("Using custom system prompt" + request.system_prompt)
        system_prompt = request.system_prompt 
        
    # Build conversation context
    conversation = ""
    for msg in request.conversation_history: 
        conversation += f"{msg.get('role', 'user')}: {msg.get('content', '')}\\n"
    logger.info(f"Conversation history: {conversation}")
    
    full_prompt = f"""{system_prompt}

Контекст диалога: {request.context}

Отвечай на языке клиента

История диалога:
{conversation}

Пользователь: {request.user_message}

Ассистент:"""

    if OPENAI_API_KEY != "OPENAI_API_KEY_NOT_SET":
        try:
            logger.info("Using OpenAI API for response generation")
            response = await openai_client.responses.create(
                model="gpt-5.2",
                instructions=full_prompt,
                input=request.user_message,
            )

            # result = json.loads(response.text)
            bot_responce = response.output[0].content[0].text.strip()
            return GenerateResponse(
                response=bot_responce,
                model="gpt-5.2"
            )
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            pass

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": DEFAULT_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            
            result = response.json()
            bot_response = result.get("output", "").strip()
            
            return GenerateResponse(
                response=bot_response,
                model=DEFAULT_MODEL
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@app.post("/embeddings")
async def generate_embeddings(text: str, model: str = "nomic-embed-text"):
    """Generate embeddings for text"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                }
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")
