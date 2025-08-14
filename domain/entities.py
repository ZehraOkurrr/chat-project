from dataclasses import dataclass
from typing import Optional, Set
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    TEXT = "text"
    SYSTEM = "system"

@dataclass(frozen=True)
class User:
    """Chat kullanıcısı"""
    username: str
    connection_id: str
    joined_at: datetime

@dataclass
class Message:
    """Chat mesajı"""
    content: str
    sender: User
    message_type: MessageType
    timestamp: datetime
    room_id: str

@dataclass
class Room:
    """Chat odası"""
    room_id: str
    password: Optional[str]
    users: Set[User]
    created_at: datetime
    is_active: bool = True
    
    @property
    def user_count(self) -> int:
        return len(self.users)
    
    def can_join(self, password: Optional[str] = None) -> bool:
        if not self.password:
            return True
        return self.password == password
    
    def add_user(self, user: User) -> None:
        self.users.add(user)
    
    def remove_user(self, user: User) -> None:
        self.users.discard(user)
        if self.user_count <= 1:
            self.is_active = False
