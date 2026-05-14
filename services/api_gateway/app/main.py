from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, Response
import httpx
import os


# CORS

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     app.state.http_client = httpx.AsyncClient(timeout=10.0)
#     yield
#     await app.state.http_client.aclose()
#
# Module-level fallback — always available
_http_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    _http_client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = _http_client
    yield
    await _http_client.aclose()

app = FastAPI(title="Chatbot API Gateway", version="1.0.0", lifespan=lifespan)


# app = FastAPI(title="Chatbot API Gateway", version="1.0.0") #,lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:3001" ],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8001")
BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://bot_service:8002")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin_service:8003")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics_service:8004")
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge_service:8006")


@app.get("/")
async def root():
    return {"message": "Chatbot API Gateway", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Proxy routes to services
# @app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
# async def proxy_auth(path: str, request: Request):
#     async with httpx.AsyncClient() as client:
#         url = f"{AUTH_SERVICE_URL}/{path}"
#         response = await client.request(
#             method=request.method,
#             url=url,
#             headers=dict(request.headers),
#             content=await request.body()
#         )
#         return JSONResponse(content=response.json(), status_code=response.status_code)

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
}

# Shared client with timeout — created once at startup

@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_auth(path: str, request: Request):
    url = f"{AUTH_SERVICE_URL}/{path}"

    # Forward all headers except hop-by-hop
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP
    }

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
        )
    except httpx.TimeoutException:
        return Response(content="Auth service timeout", status_code=504)
    except httpx.RequestError:
        return Response(content="Auth service unreachable", status_code=502)

    # Forward response headers (drop hop-by-hop)
    response_headers = {
        k: v for k, v in resp.headers.multi_items()
        if k.lower() not in HOP_BY_HOP
    }

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return JSONResponse(
            content=resp.json(),
            status_code=resp.status_code,
            headers=response_headers,
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=content_type or None,
        headers=response_headers,
    )
# HOP_BY_HOP = {
#     "connection",
#     "keep-alive",
#     "proxy-authenticate",
#     "proxy-authorization",
#     "te",
#     "trailer",
#     "transfer-encoding",
#     "upgrade",
#     "host",
#     "content-length",
# }
#
# @app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
# async def proxy_auth(path: str, request: Request):
#     url = f"{AUTH_SERVICE_URL}/{path}"
#
#     # Keep only safe headers; MOST IMPORTANT: authorization
#     headers = {}
#     for k, v in request.headers.items():
#         lk = k.lower()
#         if lk in HOP_BY_HOP:
#             continue
#         if lk in {"authorization", "content-type", "accept", "user-agent"}:
#             headers[k] = v
#
#     async with httpx.AsyncClient() as client:
#         resp = await client.request(
#             method=request.method,
#             url=url,
#             headers=headers,
#             params=request.query_params,
#             content=await request.body(),
#         )
#
#     # Не всегда JSON (например 204), поэтому безопаснее:
#     content_type = resp.headers.get("content-type", "")
#     if "application/json" in content_type:
#         return JSONResponse(content=resp.json(), status_code=resp.status_code)
#     return Response(content=resp.content, status_code=resp.status_code, media_type=content_type or None)

@app.api_route("/bot/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_bot(path: str, request: Request):
    async with httpx.AsyncClient(timeout=20.0) as client:
        url = f"{BOT_SERVICE_URL}/{path}"
        response = await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            params=request.query_params,
            content=await request.body()
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)


@app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_admin(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        url = f"{ADMIN_SERVICE_URL}/{path}"
        response = await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            params=request.query_params,
            content=await request.body()
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)


@app.api_route("/analytics/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_analytics(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        url = f"{ANALYTICS_SERVICE_URL}/{path}"
        response = await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            params=request.query_params,
            content=await request.body()
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)


@app.api_route("/knowledge/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_analytics(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        url = f"{KNOWLEDGE_SERVICE_URL}/{path}"
        response = await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            params=request.query_params,
            content=await request.body()
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)
