from __future__ import annotations

import os
import uuid
import logging
from io import BytesIO
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple

import httpx
import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException

from fastapi_utils.tasks import repeat_every

from fastapi import File, UploadFile
from pydantic import BaseModel, Field
import openpyxl

# ============================================================
# Logging
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge_service")

# ============================================================
# Env
# ============================================================
CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

BUSINESS_COLLECTION = os.getenv("BUSINESS_COLLECTION", "knowledge_base")
USER_COLLECTION = os.getenv("USER_COLLECTION", "user_memory")

# If true -> seed when collection is empty
SEED_ENABLED = os.getenv("SEED_ENABLED", "true").lower() in ("1", "true", "yes", "y")

DEFAULT_SYSTEM_PROMPT = f"""Ты — умный ассистент компании. Твоя задача общаться с пользователем максимально естественно, как живой человек, а не как робот или скрипт.
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
            "Понял вас"

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


# ============================================================
# Globals
# ============================================================
chroma_client: Optional[chromadb.HttpClient] = None
business_col = None
user_col = None

# ============================================================
# Seed Data (your original idea)
# ============================================================
CATEGORIES = ["faq", "product", "price", "objection", "company", "usp", "general"]

BRIEFS = [
    {
        "brief_id": 1,
        "name": "Hongqi Auto",
        "brief_data": {
            "company_name": "Hongqi Auto",
            # "business_description": "Компания продаёт премиальные электромобили Hongqi в Казахстане. Есть сервис и поддержка.",
            "system_prompt": DEFAULT_SYSTEM_PROMPT, 
            "products": [
                {
                    "id": "p1",
                    "name": "Hongqi EQM5",
                    "description": "Премиальный электромобиль для города и трассы. Комфортный салон, современная мультимедиа.",
                    "price": "от 25,000,000 тг",
                },
                {
                    "id": "p2",
                    "name": "Hongqi E-HS9",
                    "description": "Премиальный электрический SUV с расширенным набором опций и просторным салоном.",
                    "price": "по запросу",
                },
            ],
            "usp": "Есть сервис и запчасти в Алматы, консультация и сопровождение клиента, тест-драйв по записи.",
            "objections": [
                {
                    "id": "o1",
                    "objection_text": "Дорого",
                    "response_logic": "Объясняем ценность: безопасность, комфорт, экономия на обслуживании и топливе. Предлагаем варианты комплектаций.",
                },
                {
                    "id": "o2",
                    "objection_text": "Боюсь, что не будет запчастей",
                    "response_logic": "Подтверждаем наличие склада и сервиса, сроки поставки, гарантия и поддержка.",
                },
            ],
        },
        "extra_items": [
            ("faq", "Сколько времени занимает зарядка?", "Полная зарядка занимает 8–10 часов от обычной розетки. Быстрая зарядка зависит от станции."),
            ("price", "Цена Hongqi EQM5", "Hongqi EQM5 стоит от 25,000,000 тг (комплектация зависит от поставки)."),
            ("company", "Где находится сервис?", "Сервис и поддержка доступны в Алматы. По другим городам — по предварительному согласованию."),
            ("general", "Как оформить тест-драйв?", "Тест-драйв доступен по предварительной записи. Уточните удобное время и контактный номер."),
        ],
    },
]

USER_CONTEXTS = [
    {
        "user_id": 787785862952,
        "brief_id": 1,
        "context_items": [
            {"text": "Пользователь интересуется электромобилями для семьи. Живет в Алматы. Бюджет до 30 млн тенге."},
            {"text": "Пользователь спрашивал про зарядку Hongqi EQM5. Интересует время зарядки дома."},
        ],
    }
]

# deterministic UUID namespace (stable across restarts)
UUID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")

# ============================================================
# Pydantic models
# ============================================================
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    brief_id: Optional[int] = Field(None, description="Filter by brief_id")
    user_id: Optional[int] = Field(None, description="For user memory search")
    language: Optional[str] = Field("ru", description="Language: ru, kz, en")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    category: Optional[str] = Field(None, description="Filter by category (business)")

class SearchMetadataRequest(BaseModel):
    brief_id: Optional[int] = Field(None, description="Filter by brief_id")
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="Key-value pairs to filter metadata")


class SearchResult(BaseModel):
    text: str
    score: Optional[float] = 99.9
    metadata: Dict[str, Any]
    document_id: str
    collection: str  # "business" | "user"


class SearchResponse(BaseModel):
    context: str
    conversation_history: Optional[List[Dict[str, str]]] = None  # For user collection results
    sources: List[SearchResult]
    total_found: int


class AddKnowledgeRequest(BaseModel):
    text: Optional[str]= None 
    brief_id: Optional[int] = None
    company_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = Field("general", description="faq, product, price, objection, etc")
    title: Optional[str] = None


class AddUserKnowledgeRequest(BaseModel):
    user_id: int = Field(..., description="User ID for user collection")
    text: str = Field(..., min_length=3)
    brief_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = Field("user_context", description="user_context, user_pref, history, notes, etc")
    title: Optional[str] = None


class AddKnowledgeResponse(BaseModel):
    document_id: str
    status: str
    message: str


class BulkAddRequest(BaseModel):
    items: List[AddKnowledgeRequest]


class UpdateKnowledgeRequest(BaseModel):
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    title: Optional[str] = None


class DeleteResponse(BaseModel):
    deleted_count: int
    status: str


class CollectionStats(BaseModel):
    total_documents: int
    collection_name: str
    categories: Dict[str, int]
    briefs: Dict[str, int]


# ============================================================
# Helpers
# ============================================================
def parse_chroma_url(url: str) -> Tuple[str, int]:
    # supports http(s)://host:port[/...]
    u = url.replace("http://", "").replace("https://", "")
    hostport = u.split("/")[0]
    if ":" in hostport:
        host, port_s = hostport.split(":", 1)
        return host, int(port_s)
    return hostport, 8000


async def generate_embedding(text: str) -> List[float]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{OLLAMA_HOST}/api/embed",
                json={"model": EMBEDDING_MODEL, "input": text},
            )
        
            if r.status_code != 200:
                logger.error(f"Ollama embedding error: {r.status_code} - {r.text}")
                raise HTTPException(...)
                # raise HTTPException(status_code=500, detail=f"Ollama embedding failed: {r.text}")
            data =  r.json().get("embeddings")
            if len(data) == 0:
                return []
            emb = r.json().get("embeddings")[0]
            if not emb:
                raise HTTPException(status_code=500, detail="Empty embedding received from Ollama")
            return emb
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama request timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


def build_where_filter(
    brief_id: Optional[int] = None,
    category: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    clauses: Dict[str, Any] = []
    if brief_id is not None:
        clauses.append({"brief_id": brief_id})
    if category is not None:
        clauses.append({"category": category})
    if user_id is not None:
        clauses.append({"user_id": user_id})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return{"$and": clauses}


def format_context_from_sources(sources: List[SearchResult]) -> str:
    if not sources:
        return ""

    # user first, business second
    user_parts, business_parts = [], []
    for s in sources:
        cat = (s.metadata or {}).get("category", "general")
        prefix = ""
        if cat == "product":
            prefix = "Продукт: "
        elif cat == "price":
            prefix = "Цена: "
        elif cat == "faq":
            prefix = "FAQ: "
        elif cat == "objection":
            prefix = "Возражение: "
        # elif cat in ("user_context", "user_pref", "history", "notes"):
        #     prefix = "USER: "

        # if s.collection == "user":
        #     user_parts.append(f"{prefix}{s.text}")
        # else:
        #    business_parts.append(f"{prefix}{s.text}")
        business_parts.append(f"{prefix}{s.text}")

    return "\n\n".join(business_parts).strip()

def format_conversation_history(sources: List[SearchResult]) -> List[Dict[str, str]]:
    history = []
    for s in sources:
        role = "user" if s.collection == "user" else "bot"
        history.append({"role": role, "content": s.text})
    return history


def compute_stats(col, name: str) -> CollectionStats:
    count = col.count()
    results = col.get(include=["metadatas"])
    categories: Dict[str, int] = {}
    briefs: Dict[str, int] = {}

    for meta in results.get("metadatas", []) or []:
        cat = meta.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        bid = meta.get("brief_id")
        if bid is not None:
            briefs[str(bid)] = briefs.get(str(bid), 0) + 1

    return CollectionStats(
        total_documents=count,
        collection_name=name,
        categories=categories,
        briefs=briefs,
    )


def ensure_ready():
    if chroma_client is None or business_col is None or user_col is None:
        raise HTTPException(status_code=503, detail="Service not ready (collections not initialized)")


def stable_id(collection_kind: str, brief_id: Optional[int], category: str, title: Optional[str], text: str, user_id: Optional[int] = None) -> str:
    """
    Deterministic ID to avoid duplicates on restart.
    If you change text/category/title => ID changes (new record).
    """
    key = f"{collection_kind}|brief={brief_id}|user={user_id}|cat={category}|title={title or ''}|text={text}"
    return str(uuid.uuid5(UUID_NAMESPACE, key))


# ============================================================
# Seeding helpers
# ============================================================
def build_brief_items(brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    brief_id = brief["brief_id"]
    b = brief["brief_data"]
    items: List[Dict[str, Any]] = []


    # company
    if b.get("system_prompt"):
        items.append({
            "text": b["system_prompt"],
            "brief_id": brief_id,
            "category": "company",
            "title": "System Prompt",
            "metadata": {"source": "seed", "type": "system_prompt" ,"company_name": b.get("company_name")},

        })

    # products
    for p in b.get("products", []) or []:
        if isinstance(p, dict):
            text = f"{p.get('name','')}: {p.get('description','')} - {p.get('price','')}"
            items.append({
                "text": text,
                "brief_id": brief_id,
                "category": "product",
                "title": p.get("name", "Product"),
                "metadata": {"source": "seed", "product_id": p.get("id") ,"company_name": b.get("company_name")},
            })

    # usp
    if b.get("usp"):
        items.append({
            "text": f"Уникальное торговое предложение: {b['usp']}",
            "brief_id": brief_id,
            "category": "usp",
            "title": "USP",
            "metadata": {"source": "seed", "type": "usp" ,"company_name": b.get("company_name")},
        })

    # objections
    for o in b.get("objections", []) or []:
        if isinstance(o, dict):
            text = f"Возражение: {o.get('objection_text','')}. Ответ: {o.get('response_logic','')}"
            items.append({
                "text": text,
                "brief_id": brief_id,
                "category": "objection",
                "title": o.get("objection_text", "Objection"),
                "metadata": {"source": "seed", "objection_id": o.get("id") ,"company_name": b.get("company_name")},
            })

    # extra items
    for cat, title, content in brief.get("extra_items", []) or []:
        items.append({
            "text": f"{title}\n{content}",
            "brief_id": brief_id,
            "category": cat,
            "title": title,
            "metadata": {"source": "seed" ,"company_name": b.get("company_name")},
        })

    # ensure every category has at least one (optional)
    existing = {it["category"] for it in items}
    for cat in CATEGORIES:
        if cat not in existing:
            items.append({
                "text": f"Seed note for category={cat} (brief_id={brief_id}).",
                "brief_id": brief_id,
                "category": cat,
                "title": f"Seed {cat}",
                "metadata": {"source": "seed" ,"company_name": b.get("company_name")},
            })

    return items


def build_user_items(user_ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for c in user_ctx.get("context_items", []) or []:
        items.append({
            "text": c["text"],
            "brief_id": user_ctx.get("brief_id"),
            "user_id": user_ctx["user_id"],
            "category": "user_context",
            "title": "User context",
            "metadata": {
                "source": "seed-user",
                "context_type": "user_context",
            },
        })
    return items


async def seed_collections_if_empty():
    """
    Seeds only if collection is empty (to avoid duplicates).
    Also uses deterministic IDs so even if you call it twice, .add() won’t duplicate
    if you switch to .upsert() in future. For now: we seed only if empty.
    """
    ensure_ready()
    if not SEED_ENABLED:
        logger.info("Seeding disabled (SEED_ENABLED=false).")
        return

    b_count = business_col.count()
    u_count = user_col.count()

    if b_count > 0 and u_count > 0:
        logger.info(f"Seed skipped: business_count={b_count}, user_count={u_count}")
        return

    logger.info(f"Seeding start: business_count={b_count}, user_count={u_count}")

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        # ---- seed business ----
        if b_count == 0:
            total_added = 0
            for brief in BRIEFS:
                items = build_brief_items(brief)
                ids, docs, metas, embs = [], [], [], []
                for it in items:
                    text = it["text"]
                    brief_id = it.get("brief_id")
                    category = it.get("category", "general")
                    company_name = it.get("metadata", {}).get("company_name", "unknown")
                    title = it.get("title")
                    meta = dict(it.get("metadata") or {})
                    meta.setdefault("category", category)
                    if brief_id is not None:
                        meta["brief_id"] = brief_id
                    if title:
                        meta["title"] = title
                    if company_name:
                        meta["company_name"] = company_name
                    meta.setdefault("created_at", datetime.utcnow().isoformat())

                    # deterministic id
                    doc_id = stable_id("business", brief_id, category, title, text)

                    r = await http_client.post(
                        f"{OLLAMA_HOST}/api/embed",
                        json={"model": EMBEDDING_MODEL, "input": text},
                    )
                    r.raise_for_status()
                    emb = r.json().get("embeddings") or []
                    emb = emb[0]
                    
                    # for embeddings in emb:

                    if not emb:
                        raise RuntimeError("Empty embedding during seed (business).")

                    ids.append(doc_id)
                    docs.append(text)
                    metas.append(meta)
                    embs.append(emb)

                # If ids already exist, Chroma may error on add; but we seed only when empty.
                business_col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
                total_added += len(ids)
            logger.info(f"Seeded BUSINESS collection: added={total_added}")

        # ---- seed user ----
        if u_count == 0:
            total_added = 0
            for u in USER_CONTEXTS:
                items = build_user_items(u)
                ids, docs, metas, embs = [], [], [], []
                for it in items:
                    text = it["text"]
                    brief_id = it.get("brief_id")
                    user_id = it.get("user_id")
                    category = it.get("category", "user_context")
                    title = it.get("title")

                    meta = dict(it.get("metadata") or {})
                    meta.setdefault("category", category)
                    meta["user_id"] = user_id
                    if brief_id is not None:
                        meta["brief_id"] = brief_id
                    if title:
                        meta["title"] = title
                    meta.setdefault("created_at", datetime.utcnow().isoformat())

                    doc_id = stable_id("user", brief_id, category, title, text, user_id=user_id)

                    r = await http_client.post(
                        f"{OLLAMA_HOST}/api/embed",
                        json={"model": EMBEDDING_MODEL, "input": text},
                    )
                    r.raise_for_status()
                    emb = r.json().get("embeddings") or []
                    emb=emb[0]
                    if not emb:
                        raise RuntimeError("Empty embedding during seed (user).")

                    ids.append(doc_id)
                    docs.append(text)
                    metas.append(meta)
                    embs.append(emb)

                user_col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
                total_added += len(ids)

            logger.info(f"Seeded USER collection: added={total_added}")

    logger.info("Seeding done.")


# ============================================================
# Collection init
# ============================================================
async def initialize_collections(client: chromadb.HttpClient):
    """Get or create both collections."""
    global business_col, user_col

    try:
        business_col = client.get_collection(name=BUSINESS_COLLECTION)
        logger.info(f"Using existing business collection: {BUSINESS_COLLECTION}")
    except Exception:
        business_col = client.create_collection(
            name=BUSINESS_COLLECTION,
            metadata={"description": "Business knowledge base (briefs/products/prices/faq)"},
        )
        logger.info(f"Created business collection: {BUSINESS_COLLECTION}")

    try:
        user_col = client.get_collection(name=USER_COLLECTION)
        logger.info(f"Using existing user collection: {USER_COLLECTION}")
    except Exception:
        user_col = client.create_collection(
            name=USER_COLLECTION,
            metadata={"description": "User memory (preferences/history/context per user)"},
        )
        logger.info(f"Created user collection: {USER_COLLECTION}")

    # seed only if empty (optional)
    await seed_collections_if_empty()


# ============================================================
# Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global chroma_client
    logger.info("Starting Knowledge Service...")

    try:
        host, port = parse_chroma_url(CHROMA_URL)
        # print(host, port)
        # logger.info(host, port)
        chroma_client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        await initialize_collections(chroma_client)
        logger.info("Knowledge Service started successfully")
    except Exception as e:
        logger.error(f"Failed to init ChromaDB: {e}")
        raise

    yield
    logger.info("Shutting down Knowledge Service...")


app = FastAPI(
    title="Knowledge Service",
    version="1.0.0",
    description="RAG-powered knowledge management service (business + user collections)",
    lifespan=lifespan,
)

@app.on_event("startup")
@repeat_every(seconds=60*60*24*7, wait_first=True)  # every week 
async def auto_delete():
    ensure_ready()
    col, _ = pick_collection("user")

    try:
        col.delete(where={"metadata": {"$and": [{"category": "history"}, {"created_at": {"$lt": (datetime.utcnow() - timedelta(days=30)).isoformat()}}]}})
        return DeleteResponse(deleted_count=1, status="success")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# ============================================================
# Health & Info
# ============================================================
@app.get("/")
async def root():
    return {
        "message": "Knowledge Service",
        "version": "1.0.0",
        "ollama_host": OLLAMA_HOST,
        "embedding_model": EMBEDDING_MODEL,
        "business_collection": BUSINESS_COLLECTION,
        "user_collection": USER_COLLECTION,
        "seed_enabled": SEED_ENABLED,
    }


@app.get("/health")
async def health():
    ensure_ready()

    chroma_status = "healthy" if business_col is not None and user_col is not None else "unhealthy"

    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            ollama_status = "healthy" if r.status_code == 200 else "unhealthy"
    except Exception:
        ollama_status = "unhealthy"

    overall = "healthy" if chroma_status == "healthy" and ollama_status == "healthy" else "degraded"
    return {"status": overall, "chromadb": chroma_status, "ollama": ollama_status, "timestamp": datetime.utcnow().isoformat()}


# ============================================================
# Stats
# ============================================================
@app.get("/stats/business", response_model=CollectionStats)
async def stats_business():
    ensure_ready()
    try:
        return compute_stats(business_col, BUSINESS_COLLECTION)
    except Exception as e:
        logger.error(f"Stats business failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/stats/user", response_model=CollectionStats)
async def stats_user():
    ensure_ready()
    try:
        return compute_stats(user_col, USER_COLLECTION)
    except Exception as e:
        logger.error(f"Stats user failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================================
# Search
# ============================================================
@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    ensure_ready()
    try:

        query_emb = await generate_embedding(request.query)
        sources: List[SearchResult] = []
        user_sources: List[SearchResult] = []

        #-----------------------BUISNESS_SEARCH-------------------------------------

        # business search
        where_business = build_where_filter(brief_id=request.brief_id, category=request.category, user_id=None)
            
        buisness_kwargs = dict(
            query_embeddings=[query_emb],
            n_results=request.top_k,
            include=["documents", "metadatas", "distances"],
        )

        if where_business is not None:
            buisness_kwargs["where"] = where_business

        b = business_col.query(**buisness_kwargs)

        b_docs = (b.get("documents") or [[]])[0]
        b_metas = (b.get("metadatas") or [[]])[0]
        b_dists = (b.get("distances") or [[]])[0]
        b_ids = (b.get("ids") or [[]])[0]

        if len(b_dists) != len(b_docs) or len(b_dists) != len(b_metas) or len(b_dists) != len(b_ids):
            b_dists = [None] * len(b_docs)

        for doc, meta, dist, doc_id in zip(b_docs, b_metas, b_dists, b_ids):
            score = round(1 - dist, 4) if dist is not None else 0.0
            sources.append(
                SearchResult(
                    text=doc,
                    score=round(1 - dist, 4),
                    metadata=meta or {},
                    document_id=doc_id,
                    collection="business",
                )
            )

        sources.sort(key=lambda x: x.score, reverse=True)
        # user search (optional)
        if request.user_id:
            where_user = build_where_filter(brief_id=request.brief_id, category=None, user_id=request.user_id)
            
            user_kwargs = dict(
                query_embeddings=[query_emb],
                n_results=request.top_k,
                include=["documents", "metadatas", "distances"],
            )
            if where_user is not None:
                user_kwargs["where"] = where_user

            # u = user_col.query(**user_kwargs)
            u = user_col.get(where = where_user, include=["documents", "metadatas"])

            # u_docs = (u.get("documents") or [[]])[0]
            # u_metas = (u.get("metadatas") or [[]])[0]
            # u_dists = (u.get("distances") or [[]])[0]
            # u_ids = (u.get("ids") or [[]])[0]
            u_docs = u.get("documents", [])
            u_metas = u.get("metadatas", [])
            u_ids = u.get("ids", [])
            # if not isinstance(meta, dict):
            #     meta = {}
            for doc, meta, doc_id in zip(u_docs, u_metas, u_ids):
                user_sources.append(
                    SearchResult(
                        text=doc,
                        metadata={},
                        document_id=doc_id,
                        collection="user",
                    )
                )

            # if len(u_dists) != len(u_docs) or len(u_dists) != len(u_metas) or len(u_dists) != len(u_ids):
            #     u_dists = [None] * len(u_docs)
            #
            # for doc, meta, dist, doc_id in zip(u_docs, u_metas, u_dists, u_ids):
            #     user_sources.append(
            #         SearchResult(
            #             text=doc,
            #             score=round(1 - dist, 4) if dist is not None else 0.0,
            #             metadata=meta or {},
            #             document_id=doc_id,
            #             collection="user",
            #         )
            #     )

            # user_sources.sort(key=lambda x: x.score, reverse=True) 
            user_sources.sort(
                key=lambda x: x.metadata.get("timestamp", 0)
            )
            
        user_context =format_conversation_history(user_sources)

        context = format_context_from_sources(sources)
        return SearchResponse(context=context, conversation_history=user_context,  sources=sources, total_found=len(sources))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/search/similar/{document_id}")
async def similar(document_id: str, top_k: int = 5, which: str = "business"):
    ensure_ready()
    col = business_col if which == "business" else user_col

    try:
        got = col.get(ids=[document_id], include=["embeddings", "documents", "metadatas"])
        if not got.get("ids"):
            raise HTTPException(status_code=404, detail="Document not found")

        emb = got["embeddings"][0]
        res = col.query(
            query_embeddings=[emb],
            n_results=top_k + 1,
            include=["documents", "metadatas", "distances"],
        )

        out = []
        for doc, meta, dist, doc_id in zip(res["documents"][0], res["metadatas"][0], res["distances"][0], res["ids"][0]):
            if doc_id == document_id:
                continue
            out.append(
                SearchResult(
                    text=doc,
                    score=round(1 - dist, 4),
                    metadata=meta or {},
                    document_id=doc_id,
                    collection=which,
                )
            )
        return {"original_id": document_id, "collection": which, "similar_documents": out[:top_k]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/by_metadata")
async def search_by_metadata(request: SearchMetadataRequest, which: str = "business"):
    ensure_ready()
    col = business_col if which == "business" else user_col

    try:
        # where_filter = request.metadata_filters or {}
        # if request.brief_id is not None:
        #     where_filter["brief_id"] = request.brief_id
        filters = []

        if request.metadata_filters:
            for k, v in request.metadata_filters.items():
                filters.append({k: {"$eq": v}})

        if request.brief_id is not None:
            filters.append({"brief_id": {"$eq": request.brief_id}})

        where_filter = {"$and": filters} if filters else None

        res = col.get(where=where_filter, include=["documents", "metadatas" ])
        results = []
        for doc, meta, doc_id in zip(res.get("documents", []), res.get("metadatas", []), res.get("ids", [])):
            results.append(
                SearchResult(
                    text=doc,
                    score=0.0,
                    metadata=meta or {},
                    document_id=doc_id,
                    collection=which,
                )
            )
        return {"total_found": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metadata search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# Add (business)
# ============================================================
@app.post("/add/business", response_model=AddKnowledgeResponse)
async def add_business(req: AddKnowledgeRequest):
    ensure_ready()
    try:
        doc_id = str(uuid.uuid4())
        emb = await generate_embedding(req.text)

        meta = {
            "category": req.category,
            "created_at": datetime.utcnow().isoformat(),
            **(req.metadata or {}),
        }

        logger.info("generaed embedding for new business knowledge")
        if req.brief_id is not None:
            meta["brief_id"] = req.brief_id
        if req.title:
            meta["title"] = req.title

        if req.category == "system_prompt":
            id = business_col.get(where={"category": "system_prompt", "brief_id": req.brief_id})
            business_col.update(ids=id["ids"], embeddings=[emb], documents=[req.text], metadatas=[meta])
        business_col.add(ids=[doc_id], embeddings=[emb], documents=[req.text], metadatas=[meta])

        return AddKnowledgeResponse(document_id=doc_id, status="success", message="Added to business collection")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add business failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add: {str(e)}")

@app.post("/add/excel/business/products")
async def add_business_products(file: UploadFile = File(...), brief_id: int = 1):
    ensure_ready()
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files supported")
    try:
        contents = await file.read()
        logger.info(f"Received Excel file: {file.filename}, size={len(contents)} bytes")
        workbook = openpyxl.load_workbook(filename=BytesIO(contents), data_only=True)
        sheet = workbook.active

        items = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            name, description, price = row[:3]
            if not name or not description:
                continue
            text = f"{name}: {description} - {price}"
            items.append({
                "text": text,
                "brief_id": brief_id,
                "category": "product",
                "title": name,
                "metadata": {"source": "excel_seed", "type": "product"},
            })

        ids, docs, metas, embs = [], [], [], []
        for it in items:
            text = it["text"]
            category = it.get("category", "product")
            title = it.get("title")
            meta = dict(it.get("metadata") or {})
            meta.setdefault("category", category)
            if title:
                meta["title"] = title
            meta.setdefault("created_at", datetime.utcnow().isoformat())

            doc_id = stable_id("business", brief_id, category, title, text)

            emb = await generate_embedding(text)
            if not emb:
                raise RuntimeError("Empty embedding during Excel seed.")

            ids.append(doc_id)
            docs.append(text)
            metas.append(meta)
            embs.append(emb)

        business_col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
        return {"status": "success", "added_count": len(ids), "document_ids": ids}
    except Exception as e:
        logger.error(f"Excel add failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add from Excel: {str(e)}")
# ============================================================
# Add (user)
# ============================================================
@app.post("/add/user", response_model=AddKnowledgeResponse)
async def add_user(req: AddUserKnowledgeRequest):
    ensure_ready()
    try:
        doc_id = str(uuid.uuid4())
        emb = await generate_embedding(req.text)

        meta = {
            "category": req.category,
            "user_id": req.user_id,
            "created_at": datetime.utcnow().isoformat(),
            **(req.metadata or {}),
        }
        if req.brief_id is not None:
            meta["brief_id"] = req.brief_id
        if req.title:
            meta["title"] = req.title

        user_col.add(ids=[doc_id], embeddings=[emb], documents=[req.text], metadatas=[meta])

        return AddKnowledgeResponse(document_id=doc_id, status="success", message="Added to user collection")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add user failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add: {str(e)}")


# ============================================================
# Bulk add (business)
# ============================================================
@app.post("/add/business/bulk")
async def bulk_add_business(req: BulkAddRequest):
    ensure_ready()
    try:
        ids, embs, docs, metas = [], [], [], []
        for item in req.items:
            doc_id = str(uuid.uuid4())
            meta = {
                "category": item.category,
                "created_at": datetime.utcnow().isoformat(),
                **(item.metadata or {}),
            }
            if item.brief_id:
                meta["brief_id"] = item.brief_id
            if item.title:
                meta["title"] = item.title
            if item.company_name:
                meta["company_name"] = item.company_name
            if item.category == "system_prompt":
                id = business_col.get(where={
                    "$and":[
                        {"category": "system_prompt"},
                        { "brief_id": item.brief_id}
                    ] 
                    })
                if id.get("ids"):
                    business_col.update(ids=id["ids"], embeddings=[emb], documents=[item.text], metadatas=[meta])
                else:
                    if item.text and item.text.strip():
                        emb = await generate_embedding(item.text)
                    else:
                        emb = await generate_embedding(DEFAULT_SYSTEM_PROMPT)
                    business_col.add(ids=[doc_id], embeddings=[emb], documents=[item.text], metadatas=[meta])
                continue

            emb = await generate_embedding(item.text)
            ids.append(doc_id)
            embs.append(emb)
            docs.append(item.text)
            metas.append(meta)

        business_col.add(ids=ids, embeddings=embs, documents=docs, metadatas=metas)
        return {"status": "success", "added_count": len(ids), "document_ids": ids}
    except HTTPException:
        logger.error(f"Bulk add HTTP error")
        raise
    except Exception as e:
        logger.error(f"Bulk add failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk add failed: {str(e)}")

@app.delete("/briefs/{brief_id}")
async def bulk_delete_business(brief_id: int):
    ensure_ready()
    try:
        business_col.delete(where={"brief_id": brief_id})
    except HTTPException:
        logger.error(f"Bulk delete HTTP error")
        raise
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")



# ============================================================
# Update / Delete / Get / List (generic by collection)
# ============================================================
def pick_collection(which: str):
    which = (which or "").lower()
    if which in ("business", "b", "knowledge"):
        return business_col, "business"
    if which in ("user", "u", "memory"):
        return user_col, "user"
    raise HTTPException(status_code=400, detail="Invalid collection. Use which=business or which=user")


@app.put("/update/{document_id}")
async def update(document_id: str, req: UpdateKnowledgeRequest, which: str = "business"):
    ensure_ready()
    col, which_name = pick_collection(which)

    try:
        existing = col.get(ids=[document_id], include=["metadatas", "documents"])
        if not existing.get("ids"):
            raise HTTPException(status_code=404, detail="Document not found")

        update_data: Dict[str, Any] = {}
        if req.text is not None:
            update_data["documents"] = [req.text]
            update_data["embeddings"] = [await generate_embedding(req.text)]

        if req.metadata is not None or req.category is not None or req.title is not None:
            meta = (existing.get("metadatas") or [{}])[0] or {}
            if req.metadata is not None:
                meta.update(req.metadata)
            if req.category is not None:
                meta["category"] = req.category
            if req.title is not None:
                meta["title"] = req.title
            meta["updated_at"] = datetime.utcnow().isoformat()
            update_data["metadatas"] = [meta]

        if not update_data:
            return {"status": "success", "document_id": document_id, "message": "Nothing to update", "collection": which_name}

        col.update(ids=[document_id], **update_data)
        return {"status": "success", "document_id": document_id, "message": "Updated", "collection": which_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.delete("/delete/{document_id}", response_model=DeleteResponse)
async def delete(document_id: str, which: str = "business"):
    ensure_ready()
    col, _ = pick_collection(which)

    try:
        got = col.get(ids=[document_id])
        if not got.get("ids"):
            raise HTTPException(status_code=404, detail="Document not found")
        col.delete(ids=[document_id])
        return DeleteResponse(deleted_count=1, status="success")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@app.delete("/delete/user/cascade/{user_id}")
async def delete_user_cascade(user_id: int):
    ensure_ready()
    col = pick_collection("user")
    try:
        col.delete(where={"user_id": user_id})
        # got = user_col.get(where={"user_id": user_id})
        if not got.get("ids"):
            raise HTTPException(status_code=404, detail="User not found")
    except exception as e:
        logger.error(f"Delete user cascade failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete user cascade failed: {str(e)}")


@app.get("/get/{document_id}")
async def get(document_id: str, which: str = "business"):
    ensure_ready()
    col, which_name = pick_collection(which)

    try:
        got = col.get(ids=[document_id], include=["documents", "metadatas"])
        if not got.get("ids"):
            raise HTTPException(status_code=404, detail="Document not found")
        return {"id": got["ids"][0], "text": got["documents"][0], "metadata": got["metadatas"][0], "collection": which_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get failed: {str(e)}")


@app.get("/list")
async def list_items(
    which: str,
    brief_id: Optional[int] = None,
    category: Optional[str] = None,
    user_id: Optional[int] = None,  # mainly for user collection
    limit: int = 100,
    offset: int = 0,
):
    ensure_ready()
    col, which_name = pick_collection(which)

    try:
        where = build_where_filter(brief_id=brief_id, category=category, user_id=user_id)
        res = col.get(where=where, limit=limit, offset=offset, include=["documents", "metadatas"])
        items = []
        for _id, doc, meta in zip(res.get("ids") or [], res.get("documents") or [], res.get("metadatas") or []):
            items.append({"id": _id, "text": doc, "metadata": meta})
        return {"collection": which_name, "total": len(items), "items": items, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"List failed: {e}")
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


# ============================================================
# Utility
# ============================================================
@app.post("/test-embedding")
async def test_embedding(text: str):
    emb = await generate_embedding(text)
    return {"text": text, "embedding_size": len(emb), "embedding_sample": emb[:10], "model": EMBEDDING_MODEL}


@app.get("/categories")
async def categories(which: str = "business"):
    ensure_ready()
    col, which_name = pick_collection(which)
    try:
        if which_name == "user":
            res = col.get(include=["metadatas"])
            cats = set()
            for meta in res.get("metadatas", []) or []:
                if isinstance(meta, dict) and "user_id" in meta:
                    cats.add(meta["user_id"])
            return {"collection": which_name, "categories": sorted(list(cats)), "total": len(cats)}
        res = col.get(include=["metadatas"])
        cats = set()
        for meta in res.get("metadatas", []) or []:
            if isinstance(meta, dict) and "category" in meta:
                cats.add(meta["category"])
        return {"collection": which_name, "categories": sorted(list(cats)), "total": len(cats)}
    except Exception as e:
        logger.error(f"Categories failed: {e}")
        raise HTTPException(status_code=500, detail=f"Categories failed: {str(e)}")



@app.get("/briefs")
async def briefs(which: str = "business"):
    ensure_ready()
    col, which_name = pick_collection(which)
    res = col.get(include=["metadatas"])
    bids = set()
    company_names = dict()
    for meta in res.get("metadatas", []) or []:
        if isinstance(meta, dict) and "brief_id" in meta:
            bids.add(meta["brief_id"])
            # if meta["company_name"] is not None:
            if "company_name" in meta and meta["company_name"] is not None:
                company_names[meta["brief_id"]] = meta["company_name"]
    return {"collection": which_name, "brief_ids": sorted(list(bids)), "company_names":company_names, "total": len(bids)}


# ============================================================
# Admin
# ============================================================
@app.post("/admin/seed")
async def admin_seed(force: bool = False):
    """
    Seed manually.
    - force=false (default): seeds only if empty (same as on startup)
    - force=true: resets both collections then seeds
    """
    ensure_ready()
    try:
        if force:
            chroma_client.delete_collection(name=BUSINESS_COLLECTION)
            chroma_client.delete_collection(name=USER_COLLECTION)
            await initialize_collections(chroma_client)  # will seed-if-empty
            return {"status": "success", "message": "Reset + seeded successfully"}

        await seed_collections_if_empty()
        return {"status": "success", "message": "Seed attempted (skips if not empty)"}
    except Exception as e:
        logger.error(f"Admin seed failed: {e}")
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")


@app.post("/admin/reset")
async def reset(confirm: bool = False):
    ensure_ready()
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to reset collections")

    try:
        chroma_client.delete_collection(name=BUSINESS_COLLECTION)
        chroma_client.delete_collection(name=USER_COLLECTION)
        await initialize_collections(chroma_client)  # recreates + seeds-if-empty
        logger.warning("Reset completed")
        return {"status": "success", "message": "Collections reset successfully"}
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
