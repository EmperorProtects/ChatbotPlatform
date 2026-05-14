from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
import json
import os
from datetime import datetime

app = FastAPI(title="Web Adapter", version="1.0.0", description="Web chat adapter for chatbot platform")

# Configuration
BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://bot_service:8002")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/5")

# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()


# Models
class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"
    brief_id: str = "1"  # Default brief
    language: Optional[str] = "ru"

@app.get("/")
async def root():
    return {
        "message": "Web Adapter", 
        "version": "1.0.0",
        "description": "Web chat adapter for chatbot platform",
        "endpoints": {
            "chat_page": "/chat",
            "chat_api": "/api/chat",
            "websocket": "/ws",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "connected_users": len(manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """Simple chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chatbot</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .chat-container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            .chat-header { background: #007bff; color: white; padding: 15px; border-radius: 10px 10px 0 0; text-align: center; }
            .chat-messages { height: 400px; overflow-y: auto; padding: 20px; border-bottom: 1px solid #ddd; }
            .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .user-message { background: #007bff; color: white; margin-left: 20%; text-align: right; }
            .bot-message { background: #e9ecef; color: #333; margin-right: 20%; }
            .chat-input { display: flex; padding: 20px; }
            .chat-input input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; }
            .chat-input button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            .chat-input button:hover { background: #0056b3; }
            .status { padding: 10px; text-align: center; color: #666; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h2>AI Chatbot</h2>
            </div>
            <div class="chat-messages" id="messages"></div>
            <div class="status" id="status">Connected</div>
            <div class="chat-input">
                <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            const messages = document.getElementById('messages');
            const messageInput = document.getElementById('messageInput');
            const status = document.getElementById('status');
            
            ws.onopen = function() {
                status.textContent = 'Connected';
                status.style.color = 'green';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addMessage(data.message, 'bot-message');
            };
            
            ws.onclose = function() {
                status.textContent = 'Disconnected';
                status.style.color = 'red';
            };
            
            ws.onerror = function() {
                status.textContent = 'Connection Error';
                status.style.color = 'red';
            };
            
            function addMessage(text, className) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${className}`;
                messageDiv.textContent = text;
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            }
            
            function sendMessage() {
                const message = messageInput.value.trim();
                if (message) {
                    addMessage(message, 'user-message');
                    ws.send(JSON.stringify({message: message, user_id: 'web_user_' + Date.now()}));
                    messageInput.value = '';
                }
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }
        </script>
    </body>
    </html>
    """
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get('message', '')
            user_id = message_data.get('user_id', 'anonymous')
            brief_id = message_data.get('brief_id', '1')
            
            if user_message.strip():
                # Send to bot service
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{BOT_SERVICE_URL}/incoming",
                            json={
                                "user_id": user_id,
                                "brief_id": brief_id,
                                "text": user_message,
                                "channel": "web",
                                "language": "ru"
                            }
                        )
                        
                        if response.status_code == 200:
                            bot_response = response.json()
                            await manager.send_personal_message(
                                json.dumps({"message": bot_response.get('text', 'No response')}),
                                websocket
                            )
                        else:
                            await manager.send_personal_message(
                                json.dumps({"message": "Sorry, I'm having trouble processing your request."}),
                                websocket
                            )
                except Exception as e:
                    await manager.send_personal_message(
                        json.dumps({"message": "Sorry, I'm currently unavailable. Please try again later."}),
                        websocket
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/chat")
async def chat_api(chat_message: ChatMessage):
    """REST API for chat functionality"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BOT_SERVICE_URL}/incoming",
                json={
                    "user_id": chat_message.user_id,
                    "brief_id": chat_message.brief_id,
                    "text": chat_message.message,
                    "channel": "web",
                    "language": chat_message.language
                }
            )
            
            if response.status_code == 200:
                bot_response = response.json()
                return {
                    "status": "success",
                    "user_message": chat_message.message,
                    "bot_response": bot_response.get('text', 'No response'),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Bot service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
