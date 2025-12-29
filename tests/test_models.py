"""Tests for agentFlow data models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import (
    PRD,
    Comment,
    CommentCreate,
    CommentType,
    EntityType,
    PRDCreate,
    PRDStatus,
    PRDUpdate,
    Project,
    ProjectCreate,
    ProjectProgress,
    Story,
    StoryCreate,
    StoryProgress,
    StoryStatus,
    StoryUpdate,
    Task,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
    TaskWithContext,
)


class TestProject:
    """Tests for Project models."""

    def test_create_minimal_project(self):
        """Test creating a project with minimal required fields."""
        project = Project(name="Test Project")

        assert project.name == "Test Project"
        assert project.description is None
        assert project.metadata == {}
        assert isinstance(project.id, str)
        assert len(project.id) > 0
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

    def test_create_full_project(self):
        """Test creating a project with all fields."""
        metadata = {"priority": "high", "tags": ["backend", "api"]}
        project = Project(
            name="Full Project",
            description="A comprehensive test project",
            metadata=metadata,
        )

        assert project.name == "Full Project"
        assert project.description == "A comprehensive test project"
        assert project.metadata == metadata

    def test_project_name_required(self):
        """Test that project name is required."""
        with pytest.raises(ValidationError) as exc_info:
            Project()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_project_name_min_length(self):
        """Test that project name must have minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            Project(name="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_project_create(self):
        """Test ProjectCreate model."""
        project_create = ProjectCreate(name="New Project", description="Description")

        assert project_create.name == "New Project"
        assert project_create.description == "Description"


class TestPRD:
    """Tests for PRD models."""

    def test_create_minimal_prd(self):
        """Test creating a PRD with minimal required fields."""
        prd = PRD(
            project_id="proj-123",
            agent_id="po-agent",
            title="Test PRD",
            description="A test PRD",
        )

        assert prd.project_id == "proj-123"
        assert prd.agent_id == "po-agent"
        assert prd.created_by == "po-agent"  # Alias should work
        assert prd.title == "Test PRD"
        assert prd.description == "A test PRD"
        assert prd.status == PRDStatus.DRAFT
        assert prd.metadata == {}
        assert isinstance(prd.id, str)
        assert isinstance(prd.created_at, datetime)
        assert isinstance(prd.updated_at, datetime)

    def test_prd_status_enum(self):
        """Test PRD status enum values."""
        prd = PRD(
            project_id="proj-123",
            agent_id="po-agent",
            title="Test",
            description="Test",
            status=PRDStatus.ACTIVE,
        )

        assert prd.status == PRDStatus.ACTIVE
        assert prd.status.value == "active"

    def test_prd_status_transitions(self):
        """Test all valid PRD status values."""
        for status in [
            PRDStatus.DRAFT,
            PRDStatus.ACTIVE,
            PRDStatus.COMPLETED,
            PRDStatus.ARCHIVED,
        ]:
            prd = PRD(
                project_id="proj-123",
                agent_id="po-agent",
                title="Test",
                description="Test",
                status=status,
            )
            assert prd.status == status

    def test_prd_required_fields(self):
        """Test that all required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            PRD()

        errors = exc_info.value.errors()
        required_fields = {"project_id", "agent_id", "title", "description", "created_by"}
        error_fields = {e["loc"][0] for e in errors}
        assert required_fields.intersection(error_fields)

    def test_prd_title_min_length(self):
        """Test that PRD title must have minimum length."""
        with pytest.raises(ValidationError):
            PRD(
                project_id="proj-123",
                agent_id="po-agent",
                title="",
                description="Test",
            )

    def test_prd_create(self):
        """Test PRDCreate model."""
        prd_create = PRDCreate(
            project_id="proj-123",
            agent_id="po-agent",
            title="New PRD",
            description="Description",
        )

        assert prd_create.project_id == "proj-123"
        assert prd_create.agent_id == "po-agent"

    def test_prd_update(self):
        """Test PRDUpdate model."""
        prd_update = PRDUpdate(title="Updated Title", status=PRDStatus.ACTIVE)

        assert prd_update.title == "Updated Title"
        assert prd_update.status == PRDStatus.ACTIVE
        assert prd_update.description is None


class TestStory:
    """Tests for Story models."""

    def test_create_minimal_story(self):
        """Test creating a story with minimal required fields."""
        story = Story(
            prd_id="prd-123",
            agent_id="po-agent",
            title="Test Story",
            description="A test story",
        )

        assert story.prd_id == "prd-123"
        assert story.agent_id == "po-agent"
        assert story.title == "Test Story"
        assert story.description == "A test story"
        assert story.status == StoryStatus.TODO
        assert story.acceptance_criteria is None
        assert story.story_points is None
        assert story.assigned_to is None
        assert story.metadata == {}
        assert isinstance(story.id, str)
        assert isinstance(story.created_at, datetime)

    def test_create_full_story(self):
        """Test creating a story with all fields."""
        story = Story(
            prd_id="prd-123",
            agent_id="po-agent",
            title="Full Story",
            description="A comprehensive story",
            acceptance_criteria="User can login with email",
            story_points=5,
            assigned_to="backend-agent",
            status=StoryStatus.IN_PROGRESS,
            metadata={"priority": "high"},
        )

        assert story.story_points == 5
        assert story.assigned_to == "backend-agent"
        assert story.acceptance_criteria == "User can login with email"
        assert story.status == StoryStatus.IN_PROGRESS

    def test_story_status_enum(self):
        """Test all valid Story status values."""
        for status in [
            StoryStatus.TODO,
            StoryStatus.IN_PROGRESS,
            StoryStatus.REVIEW,
            StoryStatus.DONE,
            StoryStatus.ARCHIVED,
        ]:
            story = Story(
                prd_id="prd-123",
                agent_id="po-agent",
                title="Test",
                description="Test",
                status=status,
            )
            assert story.status == status

    def test_story_points_validation(self):
        """Test that story points must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            Story(
                prd_id="prd-123",
                agent_id="po-agent",
                title="Test",
                description="Test",
                story_points=-1,
            )

        errors = exc_info.value.errors()
        assert any("story_points" in str(e) for e in errors)

    def test_story_points_zero_valid(self):
        """Test that story points can be zero."""
        story = Story(
            prd_id="prd-123",
            agent_id="po-agent",
            title="Test",
            description="Test",
            story_points=0,
        )

        assert story.story_points == 0

    def test_story_create(self):
        """Test StoryCreate model."""
        story_create = StoryCreate(
            prd_id="prd-123",
            agent_id="po-agent",
            title="New Story",
            description="Description",
            story_points=3,
        )

        assert story_create.story_points == 3

    def test_story_update(self):
        """Test StoryUpdate model with story points validation."""
        story_update = StoryUpdate(
            title="Updated",
            status=StoryStatus.DONE,
            story_points=8,
        )

        assert story_update.story_points == 8

        # Test negative story points in update
        with pytest.raises(ValidationError):
            StoryUpdate(story_points=-5)


class TestTask:
    """Tests for Task models."""

    def test_create_minimal_task(self):
        """Test creating a task with minimal required fields."""
        task = Task(
            story_id="story-123",
            agent_id="backend-agent",
            title="Test Task",
            description="A test task",
            assigned_to="backend-agent",
        )

        assert task.story_id == "story-123"
        assert task.agent_id == "backend-agent"
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.assigned_to == "backend-agent"
        assert task.status == TaskStatus.TODO
        assert task.depends_on == []
        assert task.metadata == {}
        assert isinstance(task.id, str)

    def test_create_task_with_dependencies(self):
        """Test creating a task with dependencies."""
        task = Task(
            story_id="story-123",
            agent_id="backend-agent",
            title="Test Task",
            description="A test task",
            assigned_to="backend-agent",
            depends_on=["task-1", "task-2"],
        )

        assert task.depends_on == ["task-1", "task-2"]

    def test_task_status_enum(self):
        """Test all valid Task status values."""
        for status in [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.REVIEW,
            TaskStatus.DONE,
            TaskStatus.ARCHIVED,
        ]:
            task = Task(
                story_id="story-123",
                agent_id="backend-agent",
                title="Test",
                description="Test",
                assigned_to="agent",
                status=status,
            )
            assert task.status == status

    def test_task_assigned_to_required(self):
        """Test that assigned_to is required for tasks."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                story_id="story-123",
                agent_id="backend-agent",
                title="Test",
                description="Test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("assigned_to",) for e in errors)

    def test_task_depends_on_unique_validation(self):
        """Test that depends_on must contain unique task IDs."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                story_id="story-123",
                agent_id="backend-agent",
                title="Test",
                description="Test",
                assigned_to="agent",
                depends_on=["task-1", "task-1"],  # Duplicate
            )

        errors = exc_info.value.errors()
        assert any("depends_on" in str(e) for e in errors)

    def test_task_create(self):
        """Test TaskCreate model."""
        task_create = TaskCreate(
            story_id="story-123",
            agent_id="backend-agent",
            title="New Task",
            description="Description",
            assigned_to="backend-agent",
        )

        assert task_create.assigned_to == "backend-agent"

    def test_task_update(self):
        """Test TaskUpdate model."""
        task_update = TaskUpdate(
            title="Updated",
            status=TaskStatus.DONE,
            depends_on=["task-1"],
        )

        assert task_update.depends_on == ["task-1"]

        # Test duplicate validation in update
        with pytest.raises(ValidationError):
            TaskUpdate(depends_on=["task-1", "task-1"])


class TestComment:
    """Tests for Comment models."""

    def test_create_minimal_comment(self):
        """Test creating a comment with minimal required fields."""
        comment = Comment(
            entity_type=EntityType.TASK,
            entity_id="task-123",
            agent_id="backend-agent",
            content="This is a comment",
        )

        assert comment.entity_type == EntityType.TASK
        assert comment.entity_id == "task-123"
        assert comment.agent_id == "backend-agent"
        assert comment.author == "backend-agent"  # Alias should work
        assert comment.content == "This is a comment"
        assert comment.comment_type == CommentType.COMMENT
        assert comment.metadata == {}
        assert isinstance(comment.id, str)
        assert isinstance(comment.created_at, datetime)

    def test_comment_types(self):
        """Test all valid comment types."""
        for comment_type in [
            CommentType.COMMENT,
            CommentType.QUESTION,
            CommentType.DECISION,
            CommentType.BLOCKER,
        ]:
            comment = Comment(
                entity_type=EntityType.TASK,
                entity_id="task-123",
                agent_id="agent",
                content="Test",
                comment_type=comment_type,
            )
            assert comment.comment_type == comment_type

    def test_entity_types(self):
        """Test all valid entity types."""
        for entity_type in [EntityType.PRD, EntityType.STORY, EntityType.TASK]:
            comment = Comment(
                entity_type=entity_type,
                entity_id="entity-123",
                agent_id="agent",
                content="Test",
            )
            assert comment.entity_type == entity_type

    def test_comment_content_required(self):
        """Test that comment content is required."""
        with pytest.raises(ValidationError) as exc_info:
            Comment(
                entity_type=EntityType.TASK,
                entity_id="task-123",
                agent_id="agent",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)

    def test_comment_content_min_length(self):
        """Test that comment content must have minimum length."""
        with pytest.raises(ValidationError):
            Comment(
                entity_type=EntityType.TASK,
                entity_id="task-123",
                agent_id="agent",
                content="",
            )

    def test_comment_create(self):
        """Test CommentCreate model."""
        comment_create = CommentCreate(
            entity_type=EntityType.STORY,
            entity_id="story-123",
            agent_id="agent",
            content="New comment",
            comment_type=CommentType.QUESTION,
        )

        assert comment_create.comment_type == CommentType.QUESTION


class TestProgressModels:
    """Tests for progress tracking models."""

    def test_story_progress(self):
        """Test StoryProgress model."""
        story = Story(
            prd_id="prd-123",
            agent_id="po-agent",
            title="Test Story",
            description="Test",
        )

        progress = StoryProgress(
            story=story,
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=1,
            completion_percentage=50.0,
        )

        assert progress.total_tasks == 10
        assert progress.completed_tasks == 5
        assert progress.completion_percentage == 50.0

    def test_project_progress(self):
        """Test ProjectProgress model."""
        progress = ProjectProgress(
            project_id="proj-123",
            total_prds=2,
            total_stories=5,
            total_tasks=20,
            stories_by_status={"todo": 2, "in_progress": 3},
            tasks_by_status={"todo": 10, "done": 10},
            tasks_by_agent={"agent-1": 10, "agent-2": 10},
            completion_percentage=50.0,
        )

        assert progress.project_id == "proj-123"
        assert progress.total_tasks == 20
        assert progress.tasks_by_agent["agent-1"] == 10
        assert progress.completion_percentage == 50.0


class TestTaskWithContext:
    """Tests for TaskWithContext model."""

    def test_task_with_context(self):
        """Test TaskWithContext includes parent context."""
        task = TaskWithContext(
            story_id="story-123",
            agent_id="backend-agent",
            title="Test Task",
            description="Test",
            assigned_to="backend-agent",
            story_title="Parent Story",
            prd_title="Parent PRD",
            project_id="proj-123",
        )

        assert task.story_title == "Parent Story"
        assert task.prd_title == "Parent PRD"
        assert task.project_id == "proj-123"


class TestModelTimestamps:
    """Tests for timestamp handling."""

    def test_timestamps_are_utc(self):
        """Test that timestamps are in UTC."""
        project = Project(name="Test")

        assert project.created_at.tzinfo == timezone.utc
        assert project.updated_at.tzinfo == timezone.utc

    def test_timestamps_auto_generated(self):
        """Test that timestamps are automatically generated."""
        before = datetime.now(timezone.utc)
        project = Project(name="Test")
        after = datetime.now(timezone.utc)

        assert before <= project.created_at <= after
        assert before <= project.updated_at <= after


class TestModelIDs:
    """Tests for ID generation."""

    def test_ids_are_unique(self):
        """Test that generated IDs are unique."""
        projects = [Project(name=f"Project {i}") for i in range(100)]
        ids = [p.id for p in projects]

        assert len(ids) == len(set(ids))  # All IDs are unique

    def test_ids_are_uuids(self):
        """Test that IDs are valid UUID strings."""
        project = Project(name="Test")

        # UUID4 format: 8-4-4-4-12 characters
        parts = project.id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[4]) == 12

