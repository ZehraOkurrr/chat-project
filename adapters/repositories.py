from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from domain.models import User, Room, Message, RoomMembership, MessageType
from domain.entities import User as UserEntity, Room as RoomEntity, Message as MessageEntity
from datetime import datetime

class PostgresUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_user(self, user: UserEntity) -> None:
        db_user = User(
            username=user.username,
            connection_id=user.connection_id,
            joined_at=user.joined_at
        )
        self.session.add(db_user)
        await self.session.commit()
    
    async def get_user(self, connection_id: str) -> Optional[UserEntity]:
        result = await self.session.execute(
            select(User).where(User.connection_id == connection_id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            return UserEntity(
                username=db_user.username,
                connection_id=db_user.connection_id,
                joined_at=db_user.joined_at
            )
        return None
    
    async def delete_user(self, connection_id: str) -> None:
        result = await self.session.execute(
            select(User).where(User.connection_id == connection_id)
        )
        db_user = result.scalar_one_or_none()
        if db_user:
            await self.session.delete(db_user)
            await self.session.commit()

class PostgresRoomRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_room(self, room: RoomEntity) -> None:
        # Önce odayı kontrol et
        result = await self.session.execute(
            select(Room).where(Room.room_id == room.room_id)
        )
        db_room = result.scalar_one_or_none()
        
        if db_room:
            # Mevcut odayı güncelle
            db_room.password = room.password
            db_room.is_active = room.is_active
        else:
            # Yeni oda oluştur
            db_room = Room(
                room_id=room.room_id,
                password=room.password,
                created_at=room.created_at,
                is_active=room.is_active
            )
            self.session.add(db_room)
        
        await self.session.commit()
    
    async def get_room(self, room_id: str) -> Optional[RoomEntity]:
        result = await self.session.execute(
            select(Room).options(selectinload(Room.memberships).selectinload(RoomMembership.user))
            .where(Room.room_id == room_id)
        )
        db_room = result.scalar_one_or_none()
        
        if db_room:
            # Kullanıcıları topla
            users = set()
            for membership in db_room.memberships:
                user_entity = UserEntity(
                    username=membership.user.username,
                    connection_id=membership.user.connection_id,
                    joined_at=membership.user.joined_at
                )
                users.add(user_entity)
            
            return RoomEntity(
                room_id=db_room.room_id,
                password=db_room.password,
                users=users,
                created_at=db_room.created_at,
                is_active=db_room.is_active
            )
        return None
    
    async def delete_room(self, room_id: str) -> None:
        result = await self.session.execute(
            select(Room).where(Room.room_id == room_id)
        )
        db_room = result.scalar_one_or_none()
        if db_room:
            await self.session.delete(db_room)
            await self.session.commit()
    
    async def add_user_to_room(self, room_id: str, user: UserEntity) -> None:
        # Odayı bul
        result = await self.session.execute(
            select(Room).where(Room.room_id == room_id)
        )
        db_room = result.scalar_one_or_none()
        
        if db_room:
            # Kullanıcıyı bul veya oluştur
            user_result = await self.session.execute(
                select(User).where(User.connection_id == user.connection_id)
            )
            db_user = user_result.scalar_one_or_none()
            
            if not db_user:
                db_user = User(
                    username=user.username,
                    connection_id=user.connection_id,
                    joined_at=user.joined_at
                )
                self.session.add(db_user)
                await self.session.flush()
            
            # Üyelik oluştur
            membership = RoomMembership(
                user_id=db_user.id,
                room_id=db_room.id
            )
            self.session.add(membership)
            await self.session.commit()
    
    async def remove_user_from_room(self, room_id: str, connection_id: str) -> None:
        # Kullanıcıyı bul
        user_result = await self.session.execute(
            select(User).where(User.connection_id == connection_id)
        )
        db_user = user_result.scalar_one_or_none()
        
        if db_user:
            # Odayı bul
            room_result = await self.session.execute(
                select(Room).where(Room.room_id == room_id)
            )
            db_room = room_result.scalar_one_or_none()
            
            if db_room:
                # Üyeliği sil
                membership_result = await self.session.execute(
                    select(RoomMembership).where(
                        and_(
                            RoomMembership.user_id == db_user.id,
                            RoomMembership.room_id == db_room.id
                        )
                    )
                )
                membership = membership_result.scalar_one_or_none()
                
                if membership:
                    await self.session.delete(membership)
                    await self.session.commit()

class PostgresMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_message(self, message: MessageEntity) -> None:
        # Gönderen kullanıcıyı bul
        user_result = await self.session.execute(
            select(User).where(User.connection_id == message.sender.connection_id)
        )
        db_user = user_result.scalar_one_or_none()
        
        # Odayı bul
        room_result = await self.session.execute(
            select(Room).where(Room.room_id == message.room_id)
        )
        db_room = room_result.scalar_one_or_none()
        
        if db_user and db_room:
            db_message = Message(
                content=message.content,
                message_type=message.message_type.value,
                timestamp=message.timestamp,
                sender_id=db_user.id,
                room_id=db_room.id
            )
            self.session.add(db_message)
            await self.session.commit()
    
    async def get_room_messages(self, room_id: str, limit: int = 50) -> List[MessageEntity]:
        result = await self.session.execute(
            select(Message).options(selectinload(Message.sender))
            .join(Room).where(Room.room_id == room_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        
        message_entities = []
        for msg in messages:
            sender_entity = UserEntity(
                username=msg.sender.username,
                connection_id=msg.sender.connection_id,
                joined_at=msg.sender.joined_at
            )
            
            message_entity = MessageEntity(
                content=msg.content,
                sender=sender_entity,
                message_type=MessageType(msg.message_type),
                timestamp=msg.timestamp,
                room_id=room_id
            )
            message_entities.append(message_entity)
        
        return message_entities[::-1]  # Eski mesajlar önce
