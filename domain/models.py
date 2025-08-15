from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from enum import Enum

Base = declarative_base()

class MessageType(str, Enum):
    TEXT = "text"
    SYSTEM = "system"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    connection_id = Column(String(100), unique=True, nullable=False)
    joined_at = Column(DateTime, default=datetime.now)
    
    # İlişkiler
    messages = relationship("Message", back_populates="sender")
    room_memberships = relationship("RoomMembership", back_populates="user")
    sessions = relationship("Session", back_populates="user")

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    
    # İlişkiler
    messages = relationship("Message", back_populates="room")
    memberships = relationship("RoomMembership", back_populates="room")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Foreign Keys
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    # İlişkiler
    sender = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")

class RoomMembership(Base):
    __tablename__ = "room_memberships"
    
    id = Column(Integer, primary_key=True, index=True)
    joined_at = Column(DateTime, default=datetime.now)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    # İlişkiler
    user = relationship("User", back_populates="room_memberships")
    room = relationship("Room", back_populates="memberships")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, default=lambda: datetime.now() + timedelta(hours=24))
    is_active = Column(Boolean, default=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(String(50), nullable=False)
    
    # İlişkiler
    user = relationship("User", back_populates="sessions")
