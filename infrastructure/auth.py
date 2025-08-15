import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.models import User, Session
from domain.entities import Session as SessionEntity

# JWT ayarları
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 saat

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """JWT token oluştur"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """JWT token doğrula"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token süresi dolmuş"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )
    
    async def create_session(self, user: User, room_id: str) -> SessionEntity:
        """Kullanıcı için session oluştur"""
        # JWT token oluştur
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "room_id": room_id,
            "connection_id": user.connection_id
        }
        token = self.create_access_token(token_data)
        
        # Session'ı veritabanına kaydet
        db_session = Session(
            session_id=token,
            user_id=user.id,
            room_id=room_id,
            expires_at=datetime.now() + timedelta(hours=24)
        )
        self.session.add(db_session)
        await self.session.commit()
        
        return SessionEntity(
            session_id=token,
            user_id=str(user.id),
            username=user.username,
            room_id=room_id,
            created_at=db_session.created_at,
            expires_at=db_session.expires_at
        )
    
    async def validate_session(self, token: str) -> Optional[SessionEntity]:
        """Session'ı doğrula ve kullanıcı bilgilerini getir"""
        # JWT token'ı doğrula
        payload = self.verify_token(token)
        
        # Veritabanından session'ı kontrol et
        result = await self.session.execute(
            select(Session).where(
                Session.session_id == token,
                Session.is_active == True
            )
        )
        db_session = result.scalar_one_or_none()
        
        if not db_session or db_session.is_expired():
            return None
        
        return SessionEntity(
            session_id=db_session.session_id,
            user_id=str(db_session.user_id),
            username=payload.get("username"),
            room_id=db_session.room_id,
            created_at=db_session.created_at,
            expires_at=db_session.expires_at
        )
    
    async def invalidate_session(self, token: str) -> None:
        """Session'ı geçersiz kıl"""
        result = await self.session.execute(
            select(Session).where(Session.session_id == token)
        )
        db_session = result.scalar_one_or_none()
        
        if db_session:
            db_session.is_active = False
            await self.session.commit()
    
    async def cleanup_expired_sessions(self) -> None:
        """Süresi dolmuş session'ları temizle"""
        expired_sessions = await self.session.execute(
            select(Session).where(
                Session.expires_at < datetime.now()
            )
        )
        
        for session in expired_sessions.scalars().all():
            await self.session.delete(session)
        
        await self.session.commit()

def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> dict:
    """Mevcut kullanıcıyı getir (dependency injection için)"""
    auth_service = AuthService(None)  # Session dependency injection ile değiştirilecek
    payload = auth_service.verify_token(credentials.credentials)
    return payload
