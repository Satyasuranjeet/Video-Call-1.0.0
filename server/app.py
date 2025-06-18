#!/usr/bin/env python3
"""
WebRTC Signaling Server - Vercel Compatible
Optimized for Vercel deployment with proper CORS and WebSocket handling
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

app = FastAPI(
    title="VideoCall Signaling Server", 
    version="1.0.0",
    description="WebRTC signaling server for video calling"
)

# Enable CORS for all origins (Vercel deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_rooms: Dict[WebSocket, str] = {}
        self.user_info: Dict[WebSocket, dict] = {}
        logger.info("🚀 Connection Manager initialized for Vercel")
    
    async def connect(self, websocket: WebSocket, room_id: str, user_data: dict):
        """Handle new user connection"""
        try:
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
                "participants": existing_participants,
                "server": "vercel"
            })
            
            # Notify existing participants about new user
            if existing_participants:
                await self.broadcast_to_room(room_id, {
                    "type": "user_joined",
                    "user": user_data,
                    "room_id": room_id
                }, exclude=websocket)
            
            logger.info(f"✅ User '{user_data['name']}' joined room '{room_id}'. Total participants: {len(self.active_connections[room_id])}")
            
        except Exception as e:
            logger.error(f"❌ Error connecting user: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket):
        """Handle user disconnection"""
        if websocket not in self.user_rooms:
            return
            
        room_id = self.user_rooms[websocket]
        user_data = self.user_info.get(websocket, {})
        user_name = user_data.get('name', 'Unknown')
        
        logger.info(f"🔌 User '{user_name}' disconnecting from room '{room_id}'")
        
        try:
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
            if websocket in self.user_rooms:
                del self.user_rooms[websocket]
            if websocket in self.user_info:
                del self.user_info[websocket]
            
            logger.info(f"👋 User '{user_name}' disconnected from room '{room_id}'")
            
        except Exception as e:
            logger.error(f"❌ Error during disconnect: {e}")
    
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
            self.disconnect(conn)
        
        logger.debug(f"📡 Broadcasted {message['type']} to {sent_count} users in room {room_id}")
    
    async def send_to_user(self, websocket: WebSocket, message: dict):
        """Send message to specific user"""
        try:
            await websocket.send_text(json.dumps(message))
            logger.debug(f"📤 Sent {message['type']} to user")
        except Exception as e:
            logger.error(f"❌ Error sending message to user: {e}")
            self.disconnect(websocket)

# Global connection manager
manager = ConnectionManager()

@app.get("/")
async def root():
    """Server status endpoint"""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "message": "VideoCall Signaling Server is running on Vercel",
        "status": "healthy",
        "version": "1.0.0",
        "platform": "vercel",
        "active_rooms": len(manager.active_connections),
        "total_connections": total_connections,
        "timestamp": datetime.now().isoformat(),
        "websocket_url": "wss://video-call-1-0-0.vercel.app/ws/{room_id}?name={user_name}"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Vercel"""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "status": "healthy",
        "platform": "vercel",
        "active_rooms": len(manager.active_connections),
        "total_connections": total_connections,
        "uptime": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/rooms")
async def list_rooms():
    """List all active rooms"""
    rooms = []
    for room_id in manager.active_connections:
        connections = manager.active_connections[room_id]
        participants = []
        
        for conn in connections:
            if conn in manager.user_info:
                user = manager.user_info[conn]
                participants.append({
                    "id": user["id"], 
                    "name": user["name"],
                    "joined_at": user.get("joined_at")
                })
        
        rooms.append({
            "room_id": room_id,
            "participant_count": len(connections),
            "participants": participants,
            "created_at": datetime.now().isoformat()
        })
    
    return {
        "rooms": rooms,
        "total_rooms": len(rooms),
        "platform": "vercel"
    }

@app.get("/rooms/{room_id}")
async def get_room_info(room_id: str):
    """Get information about a specific room"""
    connections = manager.active_connections.get(room_id, set())
    participants = []
    
    for conn in connections:
        if conn in manager.user_info:
            user = manager.user_info[conn]
            participants.append({
                "id": user["id"], 
                "name": user["name"],
                "joined_at": user.get("joined_at")
            })
    
    return {
        "room_id": room_id,
        "exists": room_id in manager.active_connections,
        "participant_count": len(connections),
        "participants": participants,
        "platform": "vercel"
    }

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, name: str = "Anonymous"):
    """WebSocket endpoint for video calling - Vercel compatible"""
    
    user_data = {
        "id": str(uuid.uuid4()),
        "name": name,
        "joined_at": datetime.now().isoformat(),
        "platform": "vercel"
    }
    
    logger.info(f"🔌 New WebSocket connection on Vercel: {name} -> room {room_id}")
    
    try:
        await manager.connect(websocket, room_id, user_data)
        
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
                elif message_type == "ping":
                    # Handle ping for connection keep-alive
                    await manager.send_to_user(websocket, {"type": "pong"})
                else:
                    logger.warning(f"❓ Unknown message type: {message_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON received: {e}")
                await manager.send_to_user(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected on Vercel: {name}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {name} on Vercel: {e}")
    finally:
        manager.disconnect(websocket)

async def handle_webrtc_message(websocket: WebSocket, room_id: str, message: dict):
    """Handle WebRTC signaling messages"""
    try:
        sender_info = manager.user_info[websocket]
        target_user_id = message.get("target")
        message_type = message["type"]
        
        # Add sender information
        message["sender"] = sender_info["id"]
        message["sender_name"] = sender_info["name"]
        message["platform"] = "vercel"
        
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
            # Broadcast to all users in room
            await manager.broadcast_to_room(room_id, message, exclude=websocket)
            logger.info(f"📡 Broadcasted {message_type} from {sender_info['name']} to room {room_id}")
            
    except Exception as e:
        logger.error(f"❌ Error handling WebRTC message: {e}")

async def handle_media_state(websocket: WebSocket, room_id: str, message: dict):
    """Handle media state changes"""
    try:
        sender_info = manager.user_info[websocket]
        
        media_message = {
            "type": "media-state",
            "user": sender_info,
            "audio_enabled": message.get("audio_enabled", True),
            "video_enabled": message.get("video_enabled", True),
            "platform": "vercel"
        }
        
        await manager.broadcast_to_room(room_id, media_message, exclude=websocket)
        logger.info(f"🎛️ Media state from {sender_info['name']}: audio={message.get('audio_enabled')}, video={message.get('video_enabled')}")
        
    except Exception as e:
        logger.error(f"❌ Error handling media state: {e}")

async def handle_chat_message(websocket: WebSocket, room_id: str, message: dict):
    """Handle chat messages"""
    try:
        sender_info = manager.user_info[websocket]
        
        chat_message = {
            "type": "chat",
            "user": sender_info,
            "message": message["message"],
            "timestamp": datetime.now().isoformat(),
            "platform": "vercel"
        }
        
        await manager.broadcast_to_room(room_id, chat_message)
        logger.info(f"💬 Chat from {sender_info['name']}: {message['message']}")
        
    except Exception as e:
        logger.error(f"❌ Error handling chat message: {e}")

# Vercel serverless function compatibility
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 STARTING VIDEOCALL SIGNALING SERVER FOR VERCEL")
    print("=" * 60)
    print("📡 Server URL: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/ws/{room_id}?name={user_name}")
    print("📊 Health Check: http://localhost:8000/health")
    print("🏠 Room List: http://localhost:8000/rooms")
    print("=" * 60)
    print("✅ Server is ready for Vercel deployment!")
    print("🌐 Deploy URL: video-call-1-0-0.vercel.app")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
