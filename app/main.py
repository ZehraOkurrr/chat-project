from typing import Dict, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json

class RoomInfo:
    def __init__(self, password: Optional[str] = None):
        self.connections: Set[WebSocket] = set()
        self.password = password
        self.is_private = password is not None

class ConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[str, RoomInfo] = {}

    async def connect(self, room: str, ws: WebSocket, password: Optional[str] = None):
        # Oda yoksa oluştur
        if room not in self.active_rooms:
            self.active_rooms[room] = RoomInfo(password)
        
        room_info = self.active_rooms[room]
        
        # Private oda kontrolü
        if room_info.is_private and room_info.password != password:
            await ws.send_text(json.dumps({
                "type": "error",
                "message": "Yanlış şifre!"
            }))
            await ws.close()
            return False
        
        room_info.connections.add(ws)
        return True

    def disconnect(self, room: str, ws: WebSocket):
        if room in self.active_rooms:
            room_info = self.active_rooms[room]
            if ws in room_info.connections:
                room_info.connections.remove(ws)
                
                # Eğer odada 1 kişi veya daha az kaldıysa odayı kapat
                if len(room_info.connections) <= 1:
                    # Kalan kişilere oda kapandı mesajı gönder
                    for remaining_ws in list(room_info.connections):
                        try:
                            remaining_ws.send_text(json.dumps({
                                "type": "room_closed",
                                "message": "Odada yeterli kişi kalmadığı için oda kapatıldı."
                            }))
                            remaining_ws.close()
                        except:
                            pass
                    self.active_rooms.pop(room, None)

    async def broadcast(self, room: str, message: str, exclude_ws: WebSocket = None):
        if room in self.active_rooms:
            room_info = self.active_rooms[room]
            for ws in list(room_info.connections):
                if ws != exclude_ws:
                    try:
                        await ws.send_text(json.dumps({
                            "type": "message",
                            "content": message
                        }))
                    except Exception:
                        self.disconnect(room, ws)

    def get_room_user_count(self, room: str) -> int:
        if room in self.active_rooms:
            return len(self.active_rooms[room].connections)
        return 0

manager = ConnectionManager()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(ws: WebSocket, room: str, username: str):
    # İlk mesaj olarak şifre bekliyoruz
    await ws.accept()
    
    try:
        # Şifre mesajını bekle
        password_data = await ws.receive_text()
        password_info = json.loads(password_data)
        password = password_info.get("password")
        
        # Bağlantıyı kur
        if not await manager.connect(room, ws, password):
            return
        
        # Başarılı bağlantı mesajı
        await ws.send_text(json.dumps({
            "type": "connected",
            "message": f"Odaya başarıyla katıldınız! Odada {manager.get_room_user_count(room)} kişi var."
        }))
        
        # Diğer kullanıcılara katılım mesajı
        await manager.broadcast(room, f"{username} odaya katıldı!", exclude_ws=ws)
        
        while True:
            data = await ws.receive_text()
            message_data = json.loads(data)
            message_content = message_data.get("message", "")
            
            if message_content:
                await manager.broadcast(room, f"{username}: {message_content}", exclude_ws=ws)

    except WebSocketDisconnect:
        manager.disconnect(room, ws)
        await manager.broadcast(room, f"{username} odadan ayrıldı!")
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(room, ws)

app.mount("/", StaticFiles(directory="static", html=True), name="static")