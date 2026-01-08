"""Tests for store event emission."""

import tempfile
from pathlib import Path

import pytest

from src.database import Database
from src.events import EventType, get_event_queue
from src.models import PRDCreate, ProjectCreate, StoryCreate, TaskCreate
from src.store import Store


@pytest.fixture
def store():
    """Create a store with temporary database."""
    # Create temp file for DB
    fd, path = tempfile.mkstemp(suffix=".db")
    db_path = Path(path)
    
    db = Database(db_path)
    yield Store(db)
    
    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def clear_events():
    """Clear events before each test."""
    queue = get_event_queue()
    queue.clear()
    yield
    queue.clear()


class TestProjectEvents:
    """Test that project operations emit events."""

    def test_create_project_emits_event(self, store):
        """Test that creating a project emits an event."""
        events = get_event_queue()
        
        project_create = ProjectCreate(
            name="Test Project",
            description="Test description",
        )
        
        project = store.create_project(project_create, agent_id="test_agent")
        
        recent = events.get_recent(limit=10)
        assert len(recent) == 1
        
        event = recent[0]
        assert event.event_type == EventType.PROJECT_CREATED
        assert event.agent_id == "test_agent"
        assert event.entity_type == "project"
        assert event.entity_id == project.id
        assert event.entity_name == "Test Project"

    def test_create_project_default_agent(self, store):
        """Test that creating a project uses default agent_id."""
        events = get_event_queue()
        
        project_create = ProjectCreate(name="Test Project")
        project = store.create_project(project_create)
        
        recent = events.get_recent(limit=10)
        assert len(recent) == 1
        assert recent[0].agent_id == "system"


class TestPRDEvents:
    """Test that PRD operations emit events."""

    def test_create_prd_emits_event(self, store):
        """Test that creating a PRD emits an event."""
        events = get_event_queue()
        
        # Create project first
        project = store.create_project(ProjectCreate(name="Project 1"))
        
        # Clear events from project creation
        events.clear()
        
        prd_create = PRDCreate(
            project_id=project.id,
            agent_id="agent1",
            title="Test PRD",
            description="PRD description",
        )
        
        prd = store.create_prd(prd_create, agent_id="agent1")
        
        recent = events.get_recent(limit=10)
        assert len(recent) == 1
        
        event = recent[0]
        assert event.event_type == EventType.PRD_CREATED
        assert event.agent_id == "agent1"
        assert event.entity_type == "prd"
        assert event.entity_id == prd.id
        assert event.entity_name == "Test PRD"
        assert event.details["project_id"] == project.id
        assert event.details["status"] == "draft"


class TestStoryEvents:
    """Test that story operations emit events."""

    def test_create_story_emits_event(self, store):
        """Test that creating a story emits an event."""
        events = get_event_queue()
        
        # Setup
        project = store.create_project(ProjectCreate(name="Project 1"))
        prd = store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent1",
                title="PRD 1",
                description="PRD description",
            )
        )
        
        events.clear()
        
        story_create = StoryCreate(
            prd_id=prd.id,
            agent_id="agent2",
            title="Test Story",
            description="Story description",
        )
        
        story = store.create_story(story_create, agent_id="agent2")
        
        recent = events.get_recent(limit=10)
        assert len(recent) == 1
        
        event = recent[0]
        assert event.event_type == EventType.STORY_CREATED
        assert event.agent_id == "agent2"
        assert event.entity_type == "story"
        assert event.entity_id == story.id
        assert event.entity_name == "Test Story"
        assert event.details["prd_id"] == prd.id


class TestTaskEvents:
    """Test that task operations emit events."""

    def test_create_task_emits_event(self, store):
        """Test that creating a task emits an event."""
        events = get_event_queue()
        
        # Setup
        project = store.create_project(ProjectCreate(name="Project 1"))
        prd = store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent1",
                title="PRD 1",
                description="PRD description",
            )
        )
        story = store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent1",
                title="Story 1",
                description="Story description",
            )
        )
        
        events.clear()
        
        task_create = TaskCreate(
            story_id=story.id,
            agent_id="agent3",
            title="Test Task",
            description="Task description",
            assigned_to="agent3",
        )
        
        task = store.create_task(task_create, agent_id="agent3")
        
        recent = events.get_recent(limit=10)
        assert len(recent) == 1
        
        event = recent[0]
        assert event.event_type == EventType.TASK_CREATED
        assert event.agent_id == "agent3"
        assert event.entity_type == "task"
        assert event.entity_id == task.id
        assert event.entity_name == "Test Task"
        assert event.details["story_id"] == story.id
        assert event.details["assigned_to"] == "agent3"


class TestMultipleEvents:
    """Test multiple operations create multiple events."""

    def test_full_workflow_emits_events(self, store):
        """Test that a complete workflow emits all expected events."""
        events = get_event_queue()
        
        # Create project
        project = store.create_project(
            ProjectCreate(name="Full Workflow"),
            agent_id="pm_agent",
        )
        
        # Create PRD
        prd = store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="pm_agent",
                title="Feature PRD",
                description="Feature description",
            ),
            agent_id="pm_agent",
        )
        
        # Create story
        story = store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="dev_agent",
                title="User Story",
                description="Story description",
            ),
            agent_id="dev_agent",
        )
        
        # Create tasks
        task1 = store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="dev_agent",
                title="Task 1",
                description="Task 1 description",
                assigned_to="dev_agent",
            ),
            agent_id="dev_agent",
        )
        
        task2 = store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="dev_agent",
                title="Task 2",
                description="Task 2 description",
                assigned_to="dev_agent",
            ),
            agent_id="dev_agent",
        )
        
        # Check all events
        recent = events.get_recent(limit=100)
        assert len(recent) == 5
        
        # Verify event types (newest first)
        assert recent[0].event_type == EventType.TASK_CREATED
        assert recent[0].entity_name == "Task 2"
        
        assert recent[1].event_type == EventType.TASK_CREATED
        assert recent[1].entity_name == "Task 1"
        
        assert recent[2].event_type == EventType.STORY_CREATED
        assert recent[2].entity_name == "User Story"
        
        assert recent[3].event_type == EventType.PRD_CREATED
        assert recent[3].entity_name == "Feature PRD"
        
        assert recent[4].event_type == EventType.PROJECT_CREATED
        assert recent[4].entity_name == "Full Workflow"

    def test_events_from_different_agents(self, store):
        """Test tracking events from multiple agents."""
        events = get_event_queue()
        
        project = store.create_project(
            ProjectCreate(name="Multi-Agent Project"),
            agent_id="agent1",
        )
        
        prd = store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent2",
                title="PRD",
                description="PRD description",
            ),
            agent_id="agent2",
        )
        
        story = store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent3",
                title="Story",
                description="Story description",
            ),
            agent_id="agent3",
        )
        
        # Check agent filtering
        agent1_events = events.get_by_agent("agent1")
        assert len(agent1_events) == 1
        assert agent1_events[0].event_type == EventType.PROJECT_CREATED
        
        agent2_events = events.get_by_agent("agent2")
        assert len(agent2_events) == 1
        assert agent2_events[0].event_type == EventType.PRD_CREATED
        
        agent3_events = events.get_by_agent("agent3")
        assert len(agent3_events) == 1
        assert agent3_events[0].event_type == EventType.STORY_CREATED

