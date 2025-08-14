import json
from typing import Optional, List, Dict
from datetime import datetime
from .entities import User, Room, Message, MessageType

class ChatUseCase:
    """Chat iş mantığı"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.rooms: Dict[str, Room] = {}
        self.messages: Dict[str, List[Message]] = {}
        self.connections: Dict[str, any] = {}
    
    def add_connection(self, connection_id: str, websocket) -> None:
        """WebSocket bağlantısını ekle"""
        self.connections[connection_id] = websocket
    
    def remove_connection(self, connection_id: str) -> None:
        """WebSocket bağlantısını kaldır"""
        self.connections.pop(connection_id, None)
    
    async def join_room(self, username: str, connection_id: str, room_id: str, password: Optional[str] = None) -> Room:
        """Kullanıcıyı odaya katıldır"""
        # Kullanıcı oluştur
        user = User(
            username=username,
            connection_id=connection_id,
            joined_at=datetime.now()
        )
        self.users[connection_id] = user
        
        # Oda kontrolü
        room = self.rooms.get(room_id)
        if not room:
            room = Room(
                room_id=room_id,
                password=password if password and password.strip() else None,
                users=set(),
                created_at=datetime.now()
            )
            self.rooms[room_id] = room
        
        # Şifre kontrolü
        if not room.can_join(password):
            raise ValueError("Yanlış şifre!")
        
        # Kullanıcıyı odaya ekle
        room.add_user(user)
        
        # Diğer kullanıcılara bildir
        await self._notify_room(room, f"{username} odaya katıldı!", exclude_user=user)
        
        return room
    
    async def leave_room(self, connection_id: str, room_id: str) -> None:
        """Kullanıcıyı odadan çıkar"""
        user = self.users.get(connection_id)
        room = self.rooms.get(room_id)
        
        if user and room:
            room.remove_user(user)
            self.users.pop(connection_id, None)
            
            if room.is_active:
                await self._notify_room(room, f"{user.username} odadan ayrıldı!")
            else:
                await self._notify_room(room, "Odada yeterli kişi kalmadığı için oda kapatıldı.")
                self.rooms.pop(room_id, None)
    
    async def send_message(self, connection_id: str, room_id: str, content: str) -> Message:
        """Mesaj gönder"""
        user = self.users.get(connection_id)
        room = self.rooms.get(room_id)
        
        if not user or not room:
            raise ValueError("Kullanıcı veya oda bulunamadı!")
        
        # Mesaj oluştur
        message = Message(
            content=content,
            sender=user,
            message_type=MessageType.TEXT,
            timestamp=datetime.now(),
            room_id=room_id
        )
        
        # Mesajı kaydet
        if room_id not in self.messages:
            self.messages[room_id] = []
        self.messages[room_id].append(message)
        
        # Diğer kullanıcılara bildir
        await self._notify_room(room, f"{user.username}: {content}", exclude_user=user)
        
        return message
    
    async def _notify_room(self, room: Room, message: str, exclude_user: Optional[User] = None) -> None:
        """Odadaki tüm kullanıcılara bildirim gönder"""
        for user in room.users:
            if exclude_user and user.connection_id == exclude_user.connection_id:
                continue
            
            websocket = self.connections.get(user.connection_id)
            if websocket:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "content": message
                    }))
                except Exception:
                    self.remove_connection(user.connection_id)
    
    async def notify_user(self, user: User, message: str) -> None:
        """Kullanıcıya bildirim gönder"""
        websocket = self.connections.get(user.connection_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps({
                    "type": "system",
                    "content": message
                }))
            except Exception:
                self.remove_connection(user.connection_id)
