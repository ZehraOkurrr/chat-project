from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Domain katmanı
from domain.use_cases import ChatUseCase

# Infrastructure katmanı
from infrastructure.websocket_handler import WebSocketHandler

# FastAPI uygulamasını oluştur
app = FastAPI(title="Basit Chat Uygulaması")

# CORS middleware ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat use case ve handler oluştur
chat_use_case = ChatUseCase()
websocket_handler = WebSocketHandler(chat_use_case)

# WebSocket endpoint'i
@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await websocket_handler.handle_connection(websocket, room, username)

# Static dosyaları serve et
app.mount("/", StaticFiles(directory="static", html=True), name="static")