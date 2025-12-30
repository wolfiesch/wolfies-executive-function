"""
WebSocket server for real-time updates.

CS Concept: **Pub/Sub Pattern** - The server acts as a message broker.
Clients subscribe to topics (tasks, calendar, etc.) and the server
publishes events to all subscribers when data changes.

Architecture:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Client A   │────►│  WebSocket  │◄────│  Client B   │
│  (browser)  │◄────│   Manager   │────►│  (browser)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   API       │
                    │   Routes    │
                    │  (publish)  │
                    └─────────────┘
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any
import json
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum


class TopicType(str, Enum):
    """Available subscription topics"""
    TASKS = "tasks"
    CALENDAR = "calendar"
    NOTES = "notes"
    GOALS = "goals"
    DASHBOARD = "dashboard"


@dataclass
class Connection:
    """Represents a WebSocket connection"""
    websocket: WebSocket
    topics: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Thread-safe implementation for handling multiple concurrent connections.

    Usage:
        manager = WebSocketManager()

        # In WebSocket endpoint
        await manager.connect(websocket)

        # When data changes (e.g., task created)
        await manager.broadcast_to_topic("tasks", {
            "type": "task_created",
            "data": task_data
        })
    """

    def __init__(self):
        # Map of connection_id -> Connection
        self.connections: Dict[str, Connection] = {}
        # Map of topic -> set of connection_ids
        self.topic_subscribers: Dict[str, Set[str]] = {
            topic.value: set() for topic in TopicType
        }
        # Lock for thread safety
        self._lock = asyncio.Lock()

    def _get_connection_id(self, websocket: WebSocket) -> str:
        """Generate unique ID for a connection"""
        return f"{id(websocket)}"

    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept and register a new WebSocket connection.

        Returns:
            Connection ID
        """
        await websocket.accept()

        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            self.connections[conn_id] = Connection(websocket=websocket)

        print(f"[WebSocket] Client connected: {conn_id}")
        return conn_id

    async def disconnect(self, websocket: WebSocket):
        """Remove a connection and all its subscriptions"""
        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            if conn_id in self.connections:
                # Remove from all topic subscriptions
                for topic in self.connections[conn_id].topics:
                    self.topic_subscribers[topic].discard(conn_id)

                # Remove connection
                del self.connections[conn_id]
                print(f"[WebSocket] Client disconnected: {conn_id}")

    async def subscribe(self, websocket: WebSocket, topics: list[str]):
        """Subscribe a connection to topics"""
        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            if conn_id not in self.connections:
                return

            for topic in topics:
                if topic in self.topic_subscribers:
                    self.topic_subscribers[topic].add(conn_id)
                    self.connections[conn_id].topics.add(topic)
                    print(f"[WebSocket] {conn_id} subscribed to {topic}")

    async def unsubscribe(self, websocket: WebSocket, topics: list[str]):
        """Unsubscribe a connection from topics"""
        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            if conn_id not in self.connections:
                return

            for topic in topics:
                if topic in self.topic_subscribers:
                    self.topic_subscribers[topic].discard(conn_id)
                    self.connections[conn_id].topics.discard(topic)

    async def broadcast_to_topic(self, topic: str, message: dict):
        """
        Send a message to all connections subscribed to a topic.

        Args:
            topic: The topic name (e.g., "tasks", "calendar")
            message: The message to send (will be JSON serialized)
        """
        if topic not in self.topic_subscribers:
            return

        # Add timestamp
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        message_json = json.dumps(message)

        # Get subscribers (copy to avoid modification during iteration)
        async with self._lock:
            subscriber_ids = list(self.topic_subscribers[topic])

        # Send to all subscribers (handle disconnections)
        disconnected = []
        for conn_id in subscriber_ids:
            if conn_id in self.connections:
                try:
                    await self.connections[conn_id].websocket.send_text(message_json)
                except Exception as e:
                    print(f"[WebSocket] Failed to send to {conn_id}: {e}")
                    disconnected.append(conn_id)

        # Clean up disconnected connections
        if disconnected:
            async with self._lock:
                for conn_id in disconnected:
                    if conn_id in self.connections:
                        for t in self.connections[conn_id].topics:
                            self.topic_subscribers[t].discard(conn_id)
                        del self.connections[conn_id]

    async def broadcast_to_all(self, message: dict):
        """Send a message to all connected clients"""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        message_json = json.dumps(message)

        async with self._lock:
            conn_ids = list(self.connections.keys())

        disconnected = []
        for conn_id in conn_ids:
            if conn_id in self.connections:
                try:
                    await self.connections[conn_id].websocket.send_text(message_json)
                except Exception:
                    disconnected.append(conn_id)

        # Clean up
        if disconnected:
            async with self._lock:
                for conn_id in disconnected:
                    if conn_id in self.connections:
                        del self.connections[conn_id]

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)

    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for a topic"""
        return len(self.topic_subscribers.get(topic, set()))


# Global manager instance
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint handler.

    Protocol:
        Client sends: { "type": "subscribe", "topics": ["tasks", "calendar"] }
        Client sends: { "type": "ping", "timestamp": 1234567890 }
        Server sends: { "type": "task_created", "data": {...}, "timestamp": "..." }
        Server sends: { "type": "pong", "timestamp": 1234567890, "serverTime": "..." }
    """
    conn_id = await ws_manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "subscribe":
                    topics = message.get("topics", [])
                    await ws_manager.subscribe(websocket, topics)

                elif msg_type == "unsubscribe":
                    topics = message.get("topics", [])
                    await ws_manager.unsubscribe(websocket, topics)

                elif msg_type == "ping":
                    # Respond with pong
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp"),
                        "serverTime": datetime.now(timezone.utc).isoformat(),
                    }))

                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "UNKNOWN_MESSAGE_TYPE",
                        "message": f"Unknown message type: {msg_type}",
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Message must be valid JSON",
                }))

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


# ============================================================
# HELPER FUNCTIONS FOR API ROUTES
# ============================================================
# Call these from your API routes when data changes

async def notify_task_created(task: dict):
    """Call this after creating a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_created",
        "data": task,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_task_updated(task: dict):
    """Call this after updating a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_updated",
        "data": task,
    })


async def notify_task_completed(task: dict):
    """Call this after completing a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_completed",
        "data": task,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_task_deleted(task_id: str):
    """Call this after deleting a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_deleted",
        "id": task_id,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_event_created(event: dict):
    """Call this after creating a calendar event"""
    await ws_manager.broadcast_to_topic("calendar", {
        "type": "event_created",
        "data": event,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_event_updated(event: dict):
    """Call this after updating a calendar event"""
    await ws_manager.broadcast_to_topic("calendar", {
        "type": "event_updated",
        "data": event,
    })


async def notify_event_deleted(event_id: str):
    """Call this after deleting a calendar event"""
    await ws_manager.broadcast_to_topic("calendar", {
        "type": "event_deleted",
        "id": event_id,
    })


async def notify_note_created(note: dict):
    """Call this after creating a note"""
    await ws_manager.broadcast_to_topic("notes", {
        "type": "note_created",
        "data": note,
    })


async def notify_note_updated(note: dict):
    """Call this after updating a note"""
    await ws_manager.broadcast_to_topic("notes", {
        "type": "note_updated",
        "data": note,
    })


async def notify_note_deleted(note_id: str):
    """Call this after deleting a note"""
    await ws_manager.broadcast_to_topic("notes", {
        "type": "note_deleted",
        "id": note_id,
    })


async def notify_goal_progress(goal_id: str, progress: float):
    """Call this after logging goal progress"""
    await ws_manager.broadcast_to_topic("goals", {
        "type": "goal_progress",
        "goalId": goal_id,
        "progress": progress,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_goal_updated(goal: dict):
    """Call this after updating a goal"""
    await ws_manager.broadcast_to_topic("goals", {
        "type": "goal_updated",
        "data": goal,
    })
