"""
Vercel-compatible WebRTC Signaling Server
Main entry point for Vercel deployment
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
import os

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VideoCall Signaling Server",
    description="WebRTC signaling server for video calling - Vercel compatible",
    version="1.0.0"
)

# CORS middleware - allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection storage (in-memory for serverless)
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
            
            # Get existing participants
            existing_participants = []
            for conn in self.active_connections[room_id]:
                if conn in self.user_info:
                    existing_participants.append(self.user_info[conn])
            
            # Add user to room
            self.active_connections[room_id].add(websocket)
            
            # Send room_joined message
            await self.send_to_user(websocket, {
                "type": "room_joined",
                "room_id": room_id,
                "user_id": user_data["id"],
                "participants": existing_participants,
                "server": "vercel",
                "timestamp": datetime.now().isoformat()
            })
            
            # Notify existing participants
            if existing_participants:
                await self.broadcast_to_room(room_id, {
                    "type": "user_joined",
                    "user": user_data,
                    "room_id": room_id
                }, exclude=websocket)
            
            logger.info(f"✅ User '{user_data['name']}' joined room '{room_id}'. Total: {len(self.active_connections[room_id])}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error connecting user: {e}")
            return False
    
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
            
            logger.info(f"👋 User '{user_name}' disconnected")
            
        except Exception as e:
            logger.error(f"❌ Error during disconnect: {e}")
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude: WebSocket = None):
        """Broadcast message to all users in a room"""
        if room_id not in self.active_connections:
            return
        
        message_text = json.dumps(message)
        disconnected = []
        sent_count = 0
        
        for connection in list(self.active_connections[room_id]):
            if connection != exclude:
                try:
                    await connection.send_text(message_text)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"❌ Error sending message: {e}")
                    disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            if room_id in self.active_connections:
                self.active_connections[room_id].discard(conn)
            self.disconnect(conn)
        
        logger.debug(f"📡 Broadcasted {message['type']} to {sent_count} users in room {room_id}")
    
    async def send_to_user(self, websocket: WebSocket, message: dict):
        """Send message to specific user"""
        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"❌ Error sending message to user: {e}")
            self.disconnect(websocket)
            return False

# Global connection manager
manager = ConnectionManager()

@app.get("/")
async def root():
    """Server status endpoint"""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "message": "VideoCall Signaling Server - Vercel Deployment",
        "status": "healthy",
        "version": "1.0.0",
        "platform": "vercel",
        "active_rooms": len(manager.active_connections),
        "total_connections": total_connections,
        "timestamp": datetime.now().isoformat(),
        "websocket_endpoint": "/ws/{room_id}?name={user_name}",
        "deployment": "vercel-serverless"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "platform": "vercel",
        "timestamp": datetime.now().isoformat(),
        "active_rooms": len(manager.active_connections),
        "total_connections": sum(len(conns) for conns in manager.active_connections.values())
    }

@app.get("/api/rooms")
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
            "participants": participants
        })
    
    return {
        "rooms": rooms,
        "total_rooms": len(rooms),
        "platform": "vercel"
    }

@app.get("/api/rooms/{room_id}")
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
    """WebSocket endpoint for video calling"""
    
    user_data = {
        "id": str(uuid.uuid4()),
        "name": name,
        "joined_at": datetime.now().isoformat(),
        "platform": "vercel"
    }
    
    logger.info(f"🔌 WebSocket connection attempt: {name} -> room {room_id}")
    
    try:
        # Connect user to room
        connected = await manager.connect(websocket, room_id, user_data)
        if not connected:
            await websocket.close(code=1011, reason="Connection failed")
            return
        
        # Message handling loop
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                message_type = message.get("type", "unknown")
                logger.info(f"📨 Received {message_type} from {name}")
                
                # Handle different message types
                if message_type in ["offer", "answer", "ice-candidate"]:
                    await handle_webrtc_message(websocket, room_id, message)
                elif message_type == "media-state":
                    await handle_media_state(websocket, room_id, message)
                elif message_type == "chat":
                    await handle_chat_message(websocket, room_id, message)
                elif message_type == "ping":
                    await manager.send_to_user(websocket, {"type": "pong", "timestamp": datetime.now().isoformat()})
                else:
                    logger.warning(f"❓ Unknown message type: {message_type}")
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_to_user(websocket, {"type": "ping"})
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON: {e}")
                await manager.send_to_user(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
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
    """Handle WebRTC signaling messages"""
    try:
        sender_info = manager.user_info.get(websocket)
        if not sender_info:
            return
            
        target_user_id = message.get("target")
        message_type = message["type"]
        
        # Add sender information
        message["sender"] = sender_info["id"]
        message["sender_name"] = sender_info["name"]
        message["timestamp"] = datetime.now().isoformat()
        
        if target_user_id:
            # Send to specific user
            target_websocket = None
            for conn in manager.active_connections.get(room_id, []):
                if conn in manager.user_info and manager.user_info[conn]["id"] == target_user_id:
                    target_websocket = conn
                    break
            
            if target_websocket:
                await manager.send_to_user(target_websocket, message)
                logger.info(f"📤 Forwarded {message_type} to target user")
            else:
                logger.warning(f"❌ Target user {target_user_id} not found")
        else:
            # Broadcast to all users in room
            await manager.broadcast_to_room(room_id, message, exclude=websocket)
            logger.info(f"📡 Broadcasted {message_type} to room")
            
    except Exception as e:
        logger.error(f"❌ Error handling WebRTC message: {e}")

async def handle_media_state(websocket: WebSocket, room_id: str, message: dict):
    """Handle media state changes"""
    try:
        sender_info = manager.user_info.get(websocket)
        if not sender_info:
            return
        
        media_message = {
            "type": "media-state",
            "user": sender_info,
            "audio_enabled": message.get("audio_enabled", True),
            "video_enabled": message.get("video_enabled", True),
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast_to_room(room_id, media_message, exclude=websocket)
        logger.info(f"🎛️ Media state updated for {sender_info['name']}")
        
    except Exception as e:
        logger.error(f"❌ Error handling media state: {e}")

async def handle_chat_message(websocket: WebSocket, room_id: str, message: dict):
    """Handle chat messages"""
    try:
        sender_info = manager.user_info.get(websocket)
        if not sender_info:
            return
        
        chat_message = {
            "type": "chat",
            "user": sender_info,
            "message": message.get("message", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast_to_room(room_id, chat_message)
        logger.info(f"💬 Chat message from {sender_info['name']}")
        
    except Exception as e:
        logger.error(f"❌ Error handling chat message: {e}")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "platform": "vercel"
        }
    )

# For Vercel deployment
handler = app
