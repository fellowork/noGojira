"""Event system for tracking all changes in noGojira."""

import json
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can occur."""

    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"

    # PRD events
    PRD_CREATED = "prd.created"
    PRD_UPDATED = "prd.updated"
    PRD_STATUS_CHANGED = "prd.status_changed"

    # Story events
    STORY_CREATED = "story.created"
    STORY_UPDATED = "story.updated"
    STORY_STATUS_CHANGED = "story.status_changed"
    STORY_ASSIGNED = "story.assigned"

    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_STATUS_CHANGED = "task.status_changed"
    TASK_ASSIGNED = "task.assigned"

    # Comment events
    COMMENT_CREATED = "comment.created"


class Event(BaseModel):
    """An event in the system."""

    id: str = Field(default_factory=lambda: str(datetime.now(timezone.utc).timestamp()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    agent_id: str
    entity_type: str  # project, prd, story, task, comment
    entity_id: str
    entity_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    def to_display_string(self) -> str:
        """Convert event to human-readable string."""
        action_map = {
            EventType.PROJECT_CREATED: "created project",
            EventType.PRD_CREATED: "created PRD",
            EventType.STORY_CREATED: "created story",
            EventType.TASK_CREATED: "created task",
            EventType.TASK_STATUS_CHANGED: "updated task status",
            EventType.STORY_STATUS_CHANGED: "updated story status",
            EventType.PRD_STATUS_CHANGED: "updated PRD status",
            EventType.COMMENT_CREATED: "added comment",
        }
        action = action_map.get(self.event_type, self.event_type.value)
        name = self.entity_name or self.entity_id[:8]
        return f"{self.agent_id} {action}: {name}"


class EventQueue:
    """Thread-safe event queue with maximum size."""

    def __init__(self, maxlen: int = 1000):
        """Initialize event queue."""
        self._queue: deque[Event] = deque(maxlen=maxlen)
        self._lock = Lock()

    def push(self, event: Event) -> None:
        """Add event to queue."""
        with self._lock:
            self._queue.append(event)

    def get_recent(self, limit: int = 50) -> list[Event]:
        """Get recent events (newest first)."""
        with self._lock:
            events = list(self._queue)
            events.reverse()  # Newest first
            return events[:limit]

    def get_by_agent(self, agent_id: str, limit: int = 50) -> list[Event]:
        """Get events for specific agent."""
        with self._lock:
            events = [e for e in self._queue if e.agent_id == agent_id]
            events.reverse()
            return events[:limit]

    def get_by_entity(self, entity_type: str, entity_id: str) -> list[Event]:
        """Get events for specific entity."""
        with self._lock:
            events = [
                e
                for e in self._queue
                if e.entity_type == entity_type and e.entity_id == entity_id
            ]
            events.reverse()
            return events

    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            self._queue.clear()


# Global event queue
_event_queue = EventQueue(maxlen=1000)


def get_event_queue() -> EventQueue:
    """Get the global event queue."""
    return _event_queue

