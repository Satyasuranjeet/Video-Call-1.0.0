#!/usr/bin/env python3
"""
WebRTC Signaling Server - WORKING VERSION
This server handles WebSocket connections and WebRTC signaling
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
from typing import Dict, Set
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VideoCall Signaling Server", version="1.0.0")

# Enable CORS for all origins (in production, specify your domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        # Room ID -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> Room ID
        self.user_rooms: Dict[WebSocket, str] = {}
        # WebSocket -> User info
        self.user_info: Dict[WebSocket, dict] = {}
        
        logger.info("🚀 Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, room_id: str, user_data: dict):
        """Handle new user connection"""
        await websocket.accept()
        logger.info(f"🔌 User '{user_data['name']}' connecting to room '{room_id}'")
        
        # Initialize room if it doesn't exist
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
            logger.info(f"🏠 Created new room: {room_id}")
        
        # Store user information
        self.user_rooms[websocket] = room_id
        self.user_info[websocket] = user_data
        
        # Get existing participants before adding new user
        existing_participants = []
        for conn in self.active_connections[room_id]:
            if conn in self.user_info:
                existing_participants.append(self.user_info[conn])
        
        # Add user to room
        self.active_connections[room_id].add(websocket)
        
        # Send room_joined message to new user
        await self.send_to_user(websocket, {
            "type": "room_joined",
            "room_id": room_id,
            "user_id": user_data["id"],
            "participants": existing_participants
        })
        
        # Notify existing participants about new user
        if existing_participants:
            await self.broadcast_to_room(room_id, {
                "type": "user_joined",
                "user": user_data,
                "room_id": room_id
            }, exclude=websocket)
        
        logger.info(f"✅ User '{user_data['name']}' joined room '{room_id}'. Total participants: {len(self.active_connections[room_id])}")
    
    def disconnect(self, websocket: WebSocket):
        """Handle user disconnection"""
        if websocket not in self.user_rooms:
            return
            
        room_id = self.user_rooms[websocket]
        user_data = self.user_info.get(websocket, {})
        user_name = user_data.get('name', 'Unknown')
        
        logger.info(f"🔌 User '{user_name}' disconnecting from room '{room_id}'")
        
        # Remove from room
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            
            # Notify other participants
            if user_data:
                asyncio.create_task(self.broadcast_to_room(room_id, {
                    "type": "user_left",
                    "user": user_data
                }, exclude=websocket))
            
            # Remove empty room
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                logger.info(f"🗑️ Removed empty room: {room_id}")
        
        # Clean up user data
        del self.user_rooms[websocket]
        if websocket in self.user_info:
            del self.user_info[websocket]
        
        logger.info(f"👋 User '{user_name}' disconnected from room '{room_id}'")
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude: WebSocket = None):
        """Broadcast message to all users in a room"""
        if room_id not in self.active_connections:
            logger.warning(f"⚠️ Attempted to broadcast to non-existent room: {room_id}")
            return
        
        message_text = json.dumps(message)
        disconnected = []
        sent_count = 0
        
        for connection in self.active_connections[room_id]:
            if connection != exclude:
                try:
                    await connection.send_text(message_text)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"❌ Error sending message: {e}")
                    disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.active_connections[room_id].discard(conn)
        
        logger.debug(f"📡 Broadcasted {message['type']} to {sent_count} users in room {room_id}")
    
    async def send_to_user(self, websocket: WebSocket, message: dict):
        """Send message to specific user"""
        try:
            await websocket.send_text(json.dumps(message))
            logger.debug(f"📤 Sent {message['type']} to user")
        except Exception as e:
            logger.error(f"❌ Error sending message to user: {e}")
            self.disconnect(websocket)
    
    def get_room_info(self, room_id: str):
        """Get information about a room"""
        if room_id not in self.active_connections:
            return None
        
        participants = []
        for conn in self.active_connections[room_id]:
            if conn in self.user_info:
                user = self.user_info[conn]
                participants.append({
                    "id": user["id"],
                    "name": user["name"],
                    "joined_at": user.get("joined_at")
                })
        
        return {
            "room_id": room_id,
            "participant_count": len(self.active_connections[room_id]),
            "participants": participants,
            "created_at": datetime.now().isoformat()
        }

# Global connection manager
manager = ConnectionManager()

@app.get("/")
async def root():
    """Server status endpoint"""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "message": "VideoCall Signaling Server is running",
        "status": "healthy",
        "version": "1.0.0",
        "active_rooms": len(manager.active_connections),
        "total_connections": total_connections,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "status": "healthy",
        "active_rooms": len(manager.active_connections),
        "total_connections": total_connections,
        "uptime": "running"
    }

@app.get("/rooms")
async def list_rooms():
    """List all active rooms"""
    rooms = []
    for room_id in manager.active_connections:
        room_info = manager.get_room_info(room_id)
        if room_info:
            rooms.append(room_info)
    
    return {
        "rooms": rooms,
        "total_rooms": len(rooms)
    }

@app.get("/rooms/{room_id}")
async def get_room_info(room_id: str):
    """Get information about a specific room"""
    room_info = manager.get_room_info(room_id)
    if room_info:
        return room_info
    else:
        return {
            "room_id": room_id,
            "exists": False,
            "participant_count": 0,
            "participants": []
        }

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, name: str = "Anonymous"):
    """WebSocket endpoint for video calling"""
    
    # Create user data
    user_data = {
        "id": str(uuid.uuid4()),
        "name": name,
        "joined_at": datetime.now().isoformat()
    }
    
    logger.info(f"🔌 New WebSocket connection: {name} -> room {room_id}")
    
    try:
        # Connect user to room
        await manager.connect(websocket, room_id, user_data)
        
        # Handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type", "unknown")
                logger.info(f"📨 Received {message_type} from {name} in room {room_id}")
                
                # Handle different message types
                if message_type in ["offer", "answer", "ice-candidate"]:
                    await handle_webrtc_message(websocket, room_id, message)
                
                elif message_type == "media-state":
                    await handle_media_state(websocket, room_id, message)
                
                elif message_type == "chat":
                    await handle_chat_message(websocket, room_id, message)
                
                else:
                    logger.warning(f"❓ Unknown message type: {message_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON received: {e}")
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {name}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {name}: {e}")
    finally:
        manager.disconnect(websocket)

async def handle_webrtc_message(websocket: WebSocket, room_id: str, message: dict):
    """Handle WebRTC signaling messages (offer, answer, ice-candidate)"""
    sender_info = manager.user_info[websocket]
    target_user_id = message.get("target")
    message_type = message["type"]
    
    # Add sender information
    message["sender"] = sender_info["id"]
    message["sender_name"] = sender_info["name"]
    
    if target_user_id:
        # Send to specific user
        target_websocket = None
        for conn in manager.active_connections.get(room_id, []):
            if conn in manager.user_info and manager.user_info[conn]["id"] == target_user_id:
                target_websocket = conn
                break
        
        if target_websocket:
            await manager.send_to_user(target_websocket, message)
            logger.info(f"📤 Forwarded {message_type} from {sender_info['name']} to {manager.user_info[target_websocket]['name']}")
        else:
            logger.warning(f"❌ Target user {target_user_id} not found in room {room_id}")
    else:
        # Broadcast to all users in room (for initial offers)
        await manager.broadcast_to_room(room_id, message, exclude=websocket)
        logger.info(f"📡 Broadcasted {message_type} from {sender_info['name']} to room {room_id}")

async def handle_media_state(websocket: WebSocket, room_id: str, message: dict):
    """Handle media state changes (mute/unmute, video on/off)"""
    sender_info = manager.user_info[websocket]
    
    media_message = {
        "type": "media-state",
        "user": sender_info,
        "audio_enabled": message.get("audio_enabled", True),
        "video_enabled": message.get("video_enabled", True)
    }
    
    await manager.broadcast_to_room(room_id, media_message, exclude=websocket)
    logger.info(f"🎛️ Media state from {sender_info['name']}: audio={message.get('audio_enabled')}, video={message.get('video_enabled')}")

async def handle_chat_message(websocket: WebSocket, room_id: str, message: dict):
    """Handle chat messages"""
    sender_info = manager.user_info[websocket]
    
    chat_message = {
        "type": "chat",
        "user": sender_info,
        "message": message["message"],
        "timestamp": datetime.now().isoformat()
    }
    
    await manager.broadcast_to_room(room_id, chat_message)
    logger.info(f"💬 Chat from {sender_info['name']}: {message['message']}")

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 STARTING VIDEOCALL SIGNALING SERVER")
    print("=" * 60)
    print("📡 Server URL: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/ws/{room_id}?name={user_name}")
    print("📊 Health Check: http://localhost:8000/health")
    print("🏠 Room List: http://localhost:8000/rooms")
    print("=" * 60)
    print("✅ Server is ready for connections!")
    print("💡 Open your React app at http://localhost:3000")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
