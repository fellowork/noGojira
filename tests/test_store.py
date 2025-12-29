"""Tests for store layer."""

import tempfile
from pathlib import Path

import pytest

from src.database import Database
from src.models import (
    CommentCreate,
    EntityType,
    PRDCreate,
    PRDStatus,
    PRDUpdate,
    ProjectCreate,
    ProjectUpdate,
    StoryCreate,
    StoryStatus,
    StoryUpdate,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)
from src.store import Store


@pytest.fixture
def temp_store():
    """Create a temporary store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        store = Store(db)
        yield store


class TestProjectOperations:
    """Tests for Project store operations."""

    def test_create_project(self, temp_store):
        """Test creating a project through store."""
        project_create = ProjectCreate(
            name="Test Project",
            description="A test project",
            metadata={"priority": "high"},
        )

        project = temp_store.create_project(project_create)

        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.metadata["priority"] == "high"
        assert project.id is not None

    def test_get_project_with_stats(self, temp_store):
        """Test getting project with statistics."""
        project_create = ProjectCreate(name="Test")
        project = temp_store.create_project(project_create)

        # Create some PRDs
        for i in range(2):
            prd_create = PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title=f"PRD {i}",
                description="Test",
            )
            temp_store.create_prd(prd_create)

        project_with_stats = temp_store.get_project(project.id)

        assert project_with_stats is not None
        assert project_with_stats.prd_count == 2
        assert project_with_stats.story_count == 0
        assert project_with_stats.task_count == 0

    def test_list_projects(self, temp_store):
        """Test listing projects."""
        for i in range(3):
            temp_store.create_project(ProjectCreate(name=f"Project {i}"))

        projects = temp_store.list_projects()
        assert len(projects) == 3

    def test_update_project(self, temp_store):
        """Test updating a project."""
        project = temp_store.create_project(ProjectCreate(name="Original"))

        update = ProjectUpdate(name="Updated", description="New description")
        updated = temp_store.update_project(project.id, update)

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.description == "New description"


class TestPRDOperations:
    """Tests for PRD store operations."""

    def test_create_prd(self, temp_store):
        """Test creating a PRD."""
        project = temp_store.create_project(ProjectCreate(name="Test"))

        prd_create = PRDCreate(
            project_id=project.id,
            agent_id="po-agent",
            title="Test PRD",
            description="A test PRD",
        )

        prd = temp_store.create_prd(prd_create)

        assert prd.title == "Test PRD"
        assert prd.project_id == project.id
        assert prd.status == PRDStatus.DRAFT

    def test_create_prd_invalid_project(self, temp_store):
        """Test creating PRD with non-existent project fails."""
        prd_create = PRDCreate(
            project_id="nonexistent",
            agent_id="agent",
            title="Test",
            description="Test",
        )

        with pytest.raises(ValueError, match="Project .* not found"):
            temp_store.create_prd(prd_create)

    def test_get_prd_with_stats(self, temp_store):
        """Test getting PRD with statistics."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        # Create stories
        for i in range(3):
            temp_store.create_story(
                StoryCreate(
                    prd_id=prd.id,
                    agent_id="agent",
                    title=f"Story {i}",
                    description="Test",
                )
            )

        prd_with_stats = temp_store.get_prd_with_stats(prd.id)

        assert prd_with_stats is not None
        assert prd_with_stats.story_count == 3
        assert prd_with_stats.task_count == 0

    def test_list_prds_filtered(self, temp_store):
        """Test listing PRDs with filters."""
        project = temp_store.create_project(ProjectCreate(name="Test"))

        # Create PRDs with different statuses
        temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent-1",
                title="Draft PRD",
                description="Test",
            )
        )
        prd2 = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent-2",
                title="Active PRD",
                description="Test",
            )
        )
        temp_store.update_prd(prd2.id, PRDUpdate(status=PRDStatus.ACTIVE))

        # Filter by status
        draft_prds = temp_store.list_prds(status="draft")
        assert len(draft_prds) == 1

        # Filter by creator
        agent1_prds = temp_store.list_prds(created_by="agent-1")
        assert len(agent1_prds) == 1

    def test_update_prd(self, temp_store):
        """Test updating a PRD."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Original",
                description="Test",
            )
        )

        update = PRDUpdate(title="Updated", status=PRDStatus.ACTIVE)
        updated = temp_store.update_prd(prd.id, update)

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == PRDStatus.ACTIVE


class TestStoryOperations:
    """Tests for Story store operations."""

    def test_create_story(self, temp_store):
        """Test creating a story."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        story_create = StoryCreate(
            prd_id=prd.id,
            agent_id="agent",
            title="Test Story",
            description="A test story",
            story_points=5,
        )

        story = temp_store.create_story(story_create)

        assert story.title == "Test Story"
        assert story.story_points == 5
        assert story.status == StoryStatus.TODO

    def test_create_story_invalid_prd(self, temp_store):
        """Test creating story with non-existent PRD fails."""
        story_create = StoryCreate(
            prd_id="nonexistent",
            agent_id="agent",
            title="Test",
            description="Test",
        )

        with pytest.raises(ValueError, match="PRD .* not found"):
            temp_store.create_story(story_create)

    def test_get_story_with_stats(self, temp_store):
        """Test getting story with statistics."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        # Create tasks
        for i in range(5):
            task = temp_store.create_task(
                TaskCreate(
                    story_id=story.id,
                    agent_id="agent",
                    title=f"Task {i}",
                    description="Test",
                    assigned_to="agent",
                )
            )
            # Update first 2 tasks to DONE
            if i < 2:
                temp_store.update_task(task.id, TaskUpdate(status=TaskStatus.DONE))

        story_with_stats = temp_store.get_story_with_stats(story.id)

        assert story_with_stats is not None
        assert story_with_stats.task_count == 5
        assert story_with_stats.completed_tasks == 2

    def test_list_stories_filtered(self, temp_store):
        """Test listing stories with filters."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        # Create stories with different assignments
        temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Story 1",
                description="Test",
                assigned_to="agent-1",
            )
        )
        temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Story 2",
                description="Test",
                assigned_to="agent-2",
            )
        )

        # Filter by assignment
        agent1_stories = temp_store.list_stories(assigned_to="agent-1")
        assert len(agent1_stories) == 1
        assert agent1_stories[0].title == "Story 1"

    def test_update_story(self, temp_store):
        """Test updating a story."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Original",
                description="Test",
            )
        )

        update = StoryUpdate(title="Updated", status=StoryStatus.IN_PROGRESS)
        updated = temp_store.update_story(story.id, update)

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == StoryStatus.IN_PROGRESS


class TestTaskOperations:
    """Tests for Task store operations."""

    def test_create_task(self, temp_store):
        """Test creating a task."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        task_create = TaskCreate(
            story_id=story.id,
            agent_id="agent",
            title="Test Task",
            description="A test task",
            assigned_to="backend-agent",
        )

        task = temp_store.create_task(task_create)

        assert task.title == "Test Task"
        assert task.assigned_to == "backend-agent"
        assert task.status == TaskStatus.TODO

    def test_create_task_invalid_story(self, temp_store):
        """Test creating task with non-existent story fails."""
        task_create = TaskCreate(
            story_id="nonexistent",
            agent_id="agent",
            title="Test",
            description="Test",
            assigned_to="agent",
        )

        with pytest.raises(ValueError, match="Story .* not found"):
            temp_store.create_task(task_create)

    def test_create_task_with_dependencies(self, temp_store):
        """Test creating a task with dependencies."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        task1 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Task 1",
                description="Test",
                assigned_to="agent",
            )
        )

        task2 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Task 2",
                description="Test",
                assigned_to="agent",
                depends_on=[task1.id],
            )
        )

        assert task2.depends_on == [task1.id]

    def test_create_task_invalid_dependency(self, temp_store):
        """Test creating task with non-existent dependency fails."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        task_create = TaskCreate(
            story_id=story.id,
            agent_id="agent",
            title="Test",
            description="Test",
            assigned_to="agent",
            depends_on=["nonexistent"],
        )

        with pytest.raises(ValueError, match="Dependency task .* not found"):
            temp_store.create_task(task_create)

    def test_update_task(self, temp_store):
        """Test updating a task."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        task = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Original",
                description="Test",
                assigned_to="agent",
            )
        )

        update = TaskUpdate(title="Updated", status=TaskStatus.DONE)
        updated = temp_store.update_task(task.id, update)

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == TaskStatus.DONE

    def test_get_agent_workload(self, temp_store):
        """Test getting agent workload."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test PRD",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test Story",
                description="Test",
            )
        )

        # Create tasks for different agents
        for i in range(3):
            temp_store.create_task(
                TaskCreate(
                    story_id=story.id,
                    agent_id="agent",
                    title=f"Task {i}",
                    description="Test",
                    assigned_to="agent-1",
                )
            )
        temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Other Task",
                description="Test",
                assigned_to="agent-2",
            )
        )

        # Get workload for agent-1
        workload = temp_store.get_agent_workload("agent-1")

        assert len(workload) == 3
        assert all(t.assigned_to == "agent-1" for t in workload)
        assert all(hasattr(t, "story_title") for t in workload)
        assert all(hasattr(t, "prd_title") for t in workload)
        assert workload[0].story_title == "Test Story"
        assert workload[0].prd_title == "Test PRD"

    def test_get_agent_workload_filtered_by_status(self, temp_store):
        """Test getting agent workload filtered by status."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        # Create tasks with different statuses
        temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Todo Task",
                description="Test",
                assigned_to="agent-1",
            )
        )
        task2 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Done Task",
                description="Test",
                assigned_to="agent-1",
            )
        )
        # Update second task to DONE
        temp_store.update_task(task2.id, TaskUpdate(status=TaskStatus.DONE))

        # Get only TODO tasks
        workload = temp_store.get_agent_workload("agent-1", status="todo")

        assert len(workload) == 1
        assert workload[0].title == "Todo Task"


class TestCommentOperations:
    """Tests for Comment store operations."""

    def test_add_comment_to_task(self, temp_store):
        """Test adding a comment to a task."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        task = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Test",
                description="Test",
                assigned_to="agent",
            )
        )

        comment_create = CommentCreate(
            entity_type=EntityType.TASK,
            entity_id=task.id,
            agent_id="agent",
            content="This is a comment",
        )

        comment = temp_store.add_comment(comment_create)

        assert comment.content == "This is a comment"
        assert comment.entity_id == task.id

    def test_add_comment_invalid_entity(self, temp_store):
        """Test adding comment to non-existent entity fails."""
        comment_create = CommentCreate(
            entity_type=EntityType.TASK,
            entity_id="nonexistent",
            agent_id="agent",
            content="Test",
        )

        with pytest.raises(ValueError, match="task .* not found"):
            temp_store.add_comment(comment_create)

    def test_get_comments(self, temp_store):
        """Test getting comments for an entity."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        # Add multiple comments
        for i in range(3):
            temp_store.add_comment(
                CommentCreate(
                    entity_type=EntityType.PRD,
                    entity_id=prd.id,
                    agent_id=f"agent-{i}",
                    content=f"Comment {i}",
                )
            )

        comments = temp_store.get_comments(EntityType.PRD, prd.id)

        assert len(comments) == 3


class TestProgressTracking:
    """Tests for progress tracking."""

    def test_get_story_progress(self, temp_store):
        """Test getting story progress."""
        project = temp_store.create_project(ProjectCreate(name="Test"))
        prd = temp_store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )
        story = temp_store.create_story(
            StoryCreate(
                prd_id=prd.id,
                agent_id="agent",
                title="Test",
                description="Test",
            )
        )

        # Create tasks with different statuses
        task1 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Done 1",
                description="Test",
                assigned_to="agent",
            )
        )
        temp_store.update_task(task1.id, TaskUpdate(status=TaskStatus.DONE))

        task2 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Done 2",
                description="Test",
                assigned_to="agent",
            )
        )
        temp_store.update_task(task2.id, TaskUpdate(status=TaskStatus.DONE))

        task3 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="In Progress",
                description="Test",
                assigned_to="agent",
            )
        )
        temp_store.update_task(task3.id, TaskUpdate(status=TaskStatus.IN_PROGRESS))

        task4 = temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Blocked",
                description="Test",
                assigned_to="agent",
            )
        )
        temp_store.update_task(task4.id, TaskUpdate(status=TaskStatus.BLOCKED))

        temp_store.create_task(
            TaskCreate(
                story_id=story.id,
                agent_id="agent",
                title="Todo",
                description="Test",
                assigned_to="agent",
            )
        )

        progress = temp_store.get_story_progress(story.id)

        assert progress is not None
        assert progress.total_tasks == 5
        assert progress.completed_tasks == 2
        assert progress.in_progress_tasks == 1
        assert progress.blocked_tasks == 1
        assert progress.completion_percentage == 40.0

    def test_get_project_progress(self, temp_store):
        """Test getting project progress."""
        project = temp_store.create_project(ProjectCreate(name="Test"))

        # Create 2 PRDs
        for i in range(2):
            prd = temp_store.create_prd(
                PRDCreate(
                    project_id=project.id,
                    agent_id="agent",
                    title=f"PRD {i}",
                    description="Test",
                )
            )

            # Create 2 stories per PRD
            for j in range(2):
                story = temp_store.create_story(
                    StoryCreate(
                        prd_id=prd.id,
                        agent_id="agent",
                        title=f"Story {j}",
                        description="Test",
                    )
                )

                # Create 3 tasks per story (1 done, 2 todo)
                task_done = temp_store.create_task(
                    TaskCreate(
                        story_id=story.id,
                        agent_id="agent",
                        title="Done Task",
                        description="Test",
                        assigned_to="agent-1",
                    )
                )
                temp_store.update_task(task_done.id, TaskUpdate(status=TaskStatus.DONE))

                for k in range(2):
                    temp_store.create_task(
                        TaskCreate(
                            story_id=story.id,
                            agent_id="agent",
                            title=f"Todo Task {k}",
                            description="Test",
                            assigned_to="agent-2",
                        )
                    )

        progress = temp_store.get_project_progress(project.id)

        assert progress is not None
        assert progress.total_prds == 2
        assert progress.total_stories == 4
        assert progress.total_tasks == 12
        assert progress.tasks_by_status["done"] == 4
        assert progress.tasks_by_status["todo"] == 8
        assert progress.tasks_by_agent["agent-1"] == 4
        assert progress.tasks_by_agent["agent-2"] == 8
        # 4 done out of 12 = 33.33%
        assert abs(progress.completion_percentage - 33.33) < 0.1

