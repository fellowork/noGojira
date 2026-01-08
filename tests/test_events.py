"""Tests for the event system."""

from datetime import datetime, timezone

import pytest

from src.events import Event, EventQueue, EventType, get_event_queue


class TestEventModel:
    """Test Event model."""

    def test_create_event(self):
        """Test creating an event."""
        event = Event(
            event_type=EventType.PROJECT_CREATED,
            agent_id="test_agent",
            entity_type="project",
            entity_id="proj_123",
            entity_name="Test Project",
        )

        assert event.event_type == EventType.PROJECT_CREATED
        assert event.agent_id == "test_agent"
        assert event.entity_type == "project"
        assert event.entity_id == "proj_123"
        assert event.entity_name == "Test Project"
        assert isinstance(event.timestamp, datetime)

    def test_event_display_string(self):
        """Test event display string generation."""
        event = Event(
            event_type=EventType.PROJECT_CREATED,
            agent_id="agent1",
            entity_type="project",
            entity_id="proj_123",
            entity_name="My Project",
        )

        display = event.to_display_string()
        assert "agent1" in display
        assert "created project" in display
        assert "My Project" in display

    def test_event_display_string_without_name(self):
        """Test event display string when entity_name is None."""
        event = Event(
            event_type=EventType.TASK_CREATED,
            agent_id="agent1",
            entity_type="task",
            entity_id="task_abcd1234",
        )

        display = event.to_display_string()
        assert "agent1" in display
        assert "created task" in display
        assert "task_abc" in display  # First 8 chars of ID

    def test_event_with_details(self):
        """Test event with additional details."""
        event = Event(
            event_type=EventType.TASK_STATUS_CHANGED,
            agent_id="agent1",
            entity_type="task",
            entity_id="task_123",
            entity_name="Implement feature",
            details={"old_status": "todo", "new_status": "in_progress"},
        )

        assert event.details["old_status"] == "todo"
        assert event.details["new_status"] == "in_progress"


class TestEventQueue:
    """Test EventQueue functionality."""

    def test_push_and_get_recent(self):
        """Test pushing events and retrieving recent ones."""
        queue = EventQueue(maxlen=100)

        event1 = Event(
            event_type=EventType.PROJECT_CREATED,
            agent_id="agent1",
            entity_type="project",
            entity_id="proj_1",
        )
        event2 = Event(
            event_type=EventType.PRD_CREATED,
            agent_id="agent2",
            entity_type="prd",
            entity_id="prd_1",
        )

        queue.push(event1)
        queue.push(event2)

        recent = queue.get_recent(limit=10)
        assert len(recent) == 2
        # Newest first
        assert recent[0].entity_id == "prd_1"
        assert recent[1].entity_id == "proj_1"

    def test_maxlen_enforcement(self):
        """Test that queue respects maxlen."""
        queue = EventQueue(maxlen=5)

        # Push 10 events
        for i in range(10):
            event = Event(
                event_type=EventType.TASK_CREATED,
                agent_id=f"agent{i}",
                entity_type="task",
                entity_id=f"task_{i}",
            )
            queue.push(event)

        recent = queue.get_recent(limit=100)
        # Should only have last 5
        assert len(recent) == 5
        # Newest first, so should be 9, 8, 7, 6, 5
        assert recent[0].entity_id == "task_9"
        assert recent[4].entity_id == "task_5"

    def test_get_recent_with_limit(self):
        """Test limiting the number of recent events."""
        queue = EventQueue(maxlen=100)

        # Push 10 events
        for i in range(10):
            event = Event(
                event_type=EventType.TASK_CREATED,
                agent_id=f"agent{i}",
                entity_type="task",
                entity_id=f"task_{i}",
            )
            queue.push(event)

        recent = queue.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[0].entity_id == "task_9"
        assert recent[1].entity_id == "task_8"
        assert recent[2].entity_id == "task_7"

    def test_get_by_agent(self):
        """Test filtering events by agent."""
        queue = EventQueue(maxlen=100)

        # Push events from different agents
        for i in range(5):
            queue.push(
                Event(
                    event_type=EventType.TASK_CREATED,
                    agent_id="agent1",
                    entity_type="task",
                    entity_id=f"task_a{i}",
                )
            )
            queue.push(
                Event(
                    event_type=EventType.STORY_CREATED,
                    agent_id="agent2",
                    entity_type="story",
                    entity_id=f"story_b{i}",
                )
            )

        agent1_events = queue.get_by_agent("agent1", limit=10)
        assert len(agent1_events) == 5
        assert all(e.agent_id == "agent1" for e in agent1_events)
        assert all(e.entity_type == "task" for e in agent1_events)

        agent2_events = queue.get_by_agent("agent2", limit=10)
        assert len(agent2_events) == 5
        assert all(e.agent_id == "agent2" for e in agent2_events)
        assert all(e.entity_type == "story" for e in agent2_events)

    def test_get_by_entity(self):
        """Test filtering events by entity."""
        queue = EventQueue(maxlen=100)

        # Create events for same entity
        queue.push(
            Event(
                event_type=EventType.TASK_CREATED,
                agent_id="agent1",
                entity_type="task",
                entity_id="task_123",
            )
        )
        queue.push(
            Event(
                event_type=EventType.TASK_STATUS_CHANGED,
                agent_id="agent1",
                entity_type="task",
                entity_id="task_123",
                details={"status": "in_progress"},
            )
        )
        queue.push(
            Event(
                event_type=EventType.TASK_STATUS_CHANGED,
                agent_id="agent2",
                entity_type="task",
                entity_id="task_123",
                details={"status": "done"},
            )
        )
        # Different entity
        queue.push(
            Event(
                event_type=EventType.TASK_CREATED,
                agent_id="agent1",
                entity_type="task",
                entity_id="task_456",
            )
        )

        task_123_events = queue.get_by_entity("task", "task_123")
        assert len(task_123_events) == 3
        assert all(e.entity_id == "task_123" for e in task_123_events)

    def test_clear(self):
        """Test clearing the queue."""
        queue = EventQueue(maxlen=100)

        for i in range(5):
            queue.push(
                Event(
                    event_type=EventType.TASK_CREATED,
                    agent_id="agent1",
                    entity_type="task",
                    entity_id=f"task_{i}",
                )
            )

        assert len(queue.get_recent(limit=100)) == 5

        queue.clear()
        assert len(queue.get_recent(limit=100)) == 0

    def test_thread_safety(self):
        """Test that queue is thread-safe (basic test)."""
        import threading

        queue = EventQueue(maxlen=1000)
        errors = []

        def push_events(agent_id: str, count: int):
            try:
                for i in range(count):
                    queue.push(
                        Event(
                            event_type=EventType.TASK_CREATED,
                            agent_id=agent_id,
                            entity_type="task",
                            entity_id=f"{agent_id}_task_{i}",
                        )
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=push_events, args=(f"agent{i}", 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        recent = queue.get_recent(limit=1000)
        assert len(recent) == 100  # 5 agents * 20 events


class TestGlobalEventQueue:
    """Test the global event queue singleton."""

    def test_get_event_queue(self):
        """Test getting the global event queue."""
        queue1 = get_event_queue()
        queue2 = get_event_queue()

        # Should be the same instance
        assert queue1 is queue2

    def test_global_queue_persistence(self):
        """Test that events persist in the global queue."""
        queue = get_event_queue()
        
        # Clear first to ensure clean state
        queue.clear()

        event = Event(
            event_type=EventType.PROJECT_CREATED,
            agent_id="test_agent",
            entity_type="project",
            entity_id="proj_test",
        )
        queue.push(event)

        # Get queue again
        queue2 = get_event_queue()
        recent = queue2.get_recent(limit=10)

        assert len(recent) >= 1
        # Find our event
        found = any(e.entity_id == "proj_test" for e in recent)
        assert found


class TestEventTypes:
    """Test all event types."""

    def test_all_event_types(self):
        """Test that all event types can be created."""
        event_types = [
            EventType.PROJECT_CREATED,
            EventType.PROJECT_UPDATED,
            EventType.PRD_CREATED,
            EventType.PRD_UPDATED,
            EventType.PRD_STATUS_CHANGED,
            EventType.STORY_CREATED,
            EventType.STORY_UPDATED,
            EventType.STORY_STATUS_CHANGED,
            EventType.STORY_ASSIGNED,
            EventType.TASK_CREATED,
            EventType.TASK_UPDATED,
            EventType.TASK_STATUS_CHANGED,
            EventType.TASK_ASSIGNED,
            EventType.COMMENT_CREATED,
        ]

        for event_type in event_types:
            event = Event(
                event_type=event_type,
                agent_id="test_agent",
                entity_type="test",
                entity_id="test_123",
            )
            assert event.event_type == event_type

