import json
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from domain.use_cases import ChatUseCase

class WebSocketHandler:
    """WebSocket bağlantılarını yöneten handler"""
    
    def __init__(self, chat_use_case: ChatUseCase):
        self.chat_use_case = chat_use_case
    
    async def handle_connection(self, websocket: WebSocket, room_id: str, username: str):
        """WebSocket bağlantısını kabul et ve yönet"""
        await websocket.accept()
        
        # Benzersiz bağlantı ID'si oluştur
        connection_id = str(uuid.uuid4())
        
        try:
            # İlk mesaj olarak şifre bekliyoruz
            password_data = await websocket.receive_text()
            password_info = json.loads(password_data)
            password = password_info.get("password")
            
            # None değerini boş string yap
            if password is None:
                password = ""
            
            # Chat use case'e bağlantıyı ekle
            self.chat_use_case.add_connection(connection_id, websocket)
            
            # Odaya katıl
            room = await self.chat_use_case.join_room(
                username=username,
                connection_id=connection_id,
                room_id=room_id,
                password=password if password else None
            )
            
            # Başarılı bağlantı mesajı
            await websocket.send_text(json.dumps({
                "type": "connected",
                "content": f"Odaya başarıyla katıldınız! Odada {room.user_count} kişi var."
            }))
            
            # Mesaj döngüsü
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                message_content = message_data.get("message", "")
                
                if message_content:
                    await self.chat_use_case.send_message(
                        connection_id=connection_id,
                        room_id=room_id,
                        content=message_content
                    )
                    
        except WebSocketDisconnect:
            # Bağlantı koptu
            await self.chat_use_case.leave_room(connection_id, room_id)
        except ValueError as e:
            # Hata durumu (örn: yanlış şifre)
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": str(e)
            }))
            await websocket.close()
        except Exception as e:
            # Genel hata
            print(f"WebSocket error: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "Bir hata oluştu!"
            }))
            await websocket.close()
        finally:
            # Bağlantıyı temizle
            self.chat_use_case.remove_connection(connection_id)
