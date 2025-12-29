"""Tests for database layer."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.database import Database
from src.models import (
    PRD,
    Comment,
    CommentType,
    EntityType,
    PRDStatus,
    Project,
    Story,
    StoryStatus,
    Task,
    TaskStatus,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db


class TestProjectOperations:
    """Tests for Project database operations."""

    def test_create_and_get_project(self, temp_db):
        """Test creating and retrieving a project."""
        project = Project(name="Test Project", description="A test project")
        created = temp_db.create_project(project)

        assert created.id == project.id
        assert created.name == project.name

        retrieved = temp_db.get_project(project.id)
        assert retrieved is not None
        assert retrieved.id == project.id
        assert retrieved.name == "Test Project"
        assert retrieved.description == "A test project"

    def test_get_nonexistent_project(self, temp_db):
        """Test getting a project that doesn't exist."""
        result = temp_db.get_project("nonexistent-id")
        assert result is None

    def test_list_projects(self, temp_db):
        """Test listing projects."""
        projects = [Project(name=f"Project {i}") for i in range(5)]
        for project in projects:
            temp_db.create_project(project)

        listed = temp_db.list_projects()
        assert len(listed) == 5
        # Should be ordered by created_at DESC
        assert listed[0].name == "Project 4"

    def test_list_projects_pagination(self, temp_db):
        """Test project listing with pagination."""
        for i in range(10):
            temp_db.create_project(Project(name=f"Project {i}"))

        # First page
        page1 = temp_db.list_projects(limit=5, offset=0)
        assert len(page1) == 5

        # Second page
        page2 = temp_db.list_projects(limit=5, offset=5)
        assert len(page2) == 5

        # No overlap
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0

    def test_update_project(self, temp_db):
        """Test updating a project."""
        project = Project(name="Original", description="Original description")
        temp_db.create_project(project)

        updated = temp_db.update_project(
            project.id,
            {"name": "Updated", "description": "Updated description"},
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.description == "Updated description"

    def test_update_project_partial(self, temp_db):
        """Test partial project update."""
        project = Project(name="Original", description="Keep this")
        temp_db.create_project(project)

        updated = temp_db.update_project(project.id, {"name": "Updated Only"})

        assert updated is not None
        assert updated.name == "Updated Only"
        assert updated.description == "Keep this"

    def test_project_metadata(self, temp_db):
        """Test storing and retrieving project metadata."""
        metadata = {"priority": "high", "tags": ["backend", "api"]}
        project = Project(name="Test", metadata=metadata)
        temp_db.create_project(project)

        retrieved = temp_db.get_project(project.id)
        assert retrieved.metadata == metadata


class TestPRDOperations:
    """Tests for PRD database operations."""

    def test_create_and_get_prd(self, temp_db):
        """Test creating and retrieving a PRD."""
        project = Project(name="Test Project")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="po-agent",
            title="Test PRD",
            description="A test PRD",
        )
        created = temp_db.create_prd(prd)

        assert created.id == prd.id

        retrieved = temp_db.get_prd(prd.id)
        assert retrieved is not None
        assert retrieved.title == "Test PRD"
        assert retrieved.project_id == project.id
        assert retrieved.status == PRDStatus.DRAFT

    def test_list_prds_by_project(self, temp_db):
        """Test listing PRDs filtered by project."""
        project1 = Project(name="Project 1")
        project2 = Project(name="Project 2")
        temp_db.create_project(project1)
        temp_db.create_project(project2)

        for i in range(3):
            temp_db.create_prd(
                PRD(
                    project_id=project1.id,
                    agent_id="agent",
                    title=f"PRD {i}",
                    description="Test",
                )
            )
        temp_db.create_prd(
            PRD(
                project_id=project2.id,
                agent_id="agent",
                title="Other PRD",
                description="Test",
            )
        )

        project1_prds = temp_db.list_prds(project_id=project1.id)
        assert len(project1_prds) == 3

        project2_prds = temp_db.list_prds(project_id=project2.id)
        assert len(project2_prds) == 1

    def test_list_prds_by_status(self, temp_db):
        """Test listing PRDs filtered by status."""
        project = Project(name="Test")
        temp_db.create_project(project)

        temp_db.create_prd(
            PRD(
                project_id=project.id,
                agent_id="agent",
                title="Draft",
                description="Test",
                status=PRDStatus.DRAFT,
            )
        )
        temp_db.create_prd(
            PRD(
                project_id=project.id,
                agent_id="agent",
                title="Active",
                description="Test",
                status=PRDStatus.ACTIVE,
            )
        )

        draft_prds = temp_db.list_prds(status="draft")
        assert len(draft_prds) == 1
        assert draft_prds[0].title == "Draft"

        active_prds = temp_db.list_prds(status="active")
        assert len(active_prds) == 1
        assert active_prds[0].title == "Active"

    def test_update_prd(self, temp_db):
        """Test updating a PRD."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Original",
            description="Original",
        )
        temp_db.create_prd(prd)

        updated = temp_db.update_prd(
            prd.id,
            {"title": "Updated", "status": PRDStatus.ACTIVE},
        )

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == PRDStatus.ACTIVE


class TestStoryOperations:
    """Tests for Story database operations."""

    def test_create_and_get_story(self, temp_db):
        """Test creating and retrieving a story."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test PRD",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test Story",
            description="A test story",
            story_points=5,
        )
        created = temp_db.create_story(story)

        assert created.id == story.id

        retrieved = temp_db.get_story(story.id)
        assert retrieved is not None
        assert retrieved.title == "Test Story"
        assert retrieved.story_points == 5

    def test_list_stories_by_prd(self, temp_db):
        """Test listing stories filtered by PRD."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd1 = PRD(
            project_id=project.id,
            agent_id="agent",
            title="PRD 1",
            description="Test",
        )
        prd2 = PRD(
            project_id=project.id,
            agent_id="agent",
            title="PRD 2",
            description="Test",
        )
        temp_db.create_prd(prd1)
        temp_db.create_prd(prd2)

        for i in range(3):
            temp_db.create_story(
                Story(
                    prd_id=prd1.id,
                    agent_id="agent",
                    title=f"Story {i}",
                    description="Test",
                )
            )
        temp_db.create_story(
            Story(prd_id=prd2.id, agent_id="agent", title="Other Story", description="Test")
        )

        prd1_stories = temp_db.list_stories(prd_id=prd1.id)
        assert len(prd1_stories) == 3

    def test_list_stories_by_assigned_agent(self, temp_db):
        """Test listing stories filtered by assigned agent."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        temp_db.create_story(
            Story(
                prd_id=prd.id,
                agent_id="agent",
                title="Story 1",
                description="Test",
                assigned_to="agent-1",
            )
        )
        temp_db.create_story(
            Story(
                prd_id=prd.id,
                agent_id="agent",
                title="Story 2",
                description="Test",
                assigned_to="agent-2",
            )
        )

        agent1_stories = temp_db.list_stories(assigned_to="agent-1")
        assert len(agent1_stories) == 1
        assert agent1_stories[0].title == "Story 1"

    def test_update_story(self, temp_db):
        """Test updating a story."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Original",
            description="Test",
        )
        temp_db.create_story(story)

        updated = temp_db.update_story(
            story.id,
            {
                "title": "Updated",
                "status": StoryStatus.IN_PROGRESS,
                "story_points": 8,
            },
        )

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == StoryStatus.IN_PROGRESS
        assert updated.story_points == 8


class TestTaskOperations:
    """Tests for Task database operations."""

    def test_create_and_get_task(self, temp_db):
        """Test creating and retrieving a task."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test Story",
            description="Test",
        )
        temp_db.create_story(story)

        task = Task(
            story_id=story.id,
            agent_id="agent",
            title="Test Task",
            description="A test task",
            assigned_to="backend-agent",
        )
        created = temp_db.create_task(task)

        assert created.id == task.id

        retrieved = temp_db.get_task(task.id)
        assert retrieved is not None
        assert retrieved.title == "Test Task"
        assert retrieved.assigned_to == "backend-agent"

    def test_task_with_dependencies(self, temp_db):
        """Test creating and retrieving a task with dependencies."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_story(story)

        task1 = Task(
            story_id=story.id,
            agent_id="agent",
            title="Task 1",
            description="Test",
            assigned_to="agent",
        )
        temp_db.create_task(task1)

        task2 = Task(
            story_id=story.id,
            agent_id="agent",
            title="Task 2",
            description="Test",
            assigned_to="agent",
            depends_on=[task1.id],
        )
        temp_db.create_task(task2)

        retrieved = temp_db.get_task(task2.id)
        assert retrieved.depends_on == [task1.id]

    def test_list_tasks_by_story(self, temp_db):
        """Test listing tasks filtered by story."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story1 = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Story 1",
            description="Test",
        )
        story2 = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Story 2",
            description="Test",
        )
        temp_db.create_story(story1)
        temp_db.create_story(story2)

        for i in range(3):
            temp_db.create_task(
                Task(
                    story_id=story1.id,
                    agent_id="agent",
                    title=f"Task {i}",
                    description="Test",
                    assigned_to="agent",
                )
            )
        temp_db.create_task(
            Task(
                story_id=story2.id,
                agent_id="agent",
                title="Other Task",
                description="Test",
                assigned_to="agent",
            )
        )

        story1_tasks = temp_db.list_tasks(story_id=story1.id)
        assert len(story1_tasks) == 3

    def test_list_tasks_by_assigned_agent(self, temp_db):
        """Test listing tasks filtered by assigned agent."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_story(story)

        temp_db.create_task(
            Task(
                story_id=story.id,
                agent_id="agent",
                title="Task 1",
                description="Test",
                assigned_to="agent-1",
            )
        )
        temp_db.create_task(
            Task(
                story_id=story.id,
                agent_id="agent",
                title="Task 2",
                description="Test",
                assigned_to="agent-2",
            )
        )

        agent1_tasks = temp_db.list_tasks(assigned_to="agent-1")
        assert len(agent1_tasks) == 1
        assert agent1_tasks[0].title == "Task 1"

    def test_list_tasks_by_status(self, temp_db):
        """Test listing tasks filtered by status."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_story(story)

        temp_db.create_task(
            Task(
                story_id=story.id,
                agent_id="agent",
                title="Todo Task",
                description="Test",
                assigned_to="agent",
                status=TaskStatus.TODO,
            )
        )
        temp_db.create_task(
            Task(
                story_id=story.id,
                agent_id="agent",
                title="Done Task",
                description="Test",
                assigned_to="agent",
                status=TaskStatus.DONE,
            )
        )

        todo_tasks = temp_db.list_tasks(status="todo")
        assert len(todo_tasks) == 1
        assert todo_tasks[0].title == "Todo Task"

    def test_update_task(self, temp_db):
        """Test updating a task."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_story(story)

        task = Task(
            story_id=story.id,
            agent_id="agent",
            title="Original",
            description="Test",
            assigned_to="agent",
        )
        temp_db.create_task(task)

        updated = temp_db.update_task(
            task.id,
            {
                "title": "Updated",
                "status": TaskStatus.DONE,
                "assigned_to": "new-agent",
            },
        )

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == TaskStatus.DONE
        assert updated.assigned_to == "new-agent"


class TestCommentOperations:
    """Tests for Comment database operations."""

    def test_create_and_get_comments(self, temp_db):
        """Test creating and retrieving comments."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_story(story)

        task = Task(
            story_id=story.id,
            agent_id="agent",
            title="Test",
            description="Test",
            assigned_to="agent",
        )
        temp_db.create_task(task)

        comment = Comment(
            entity_type=EntityType.TASK,
            entity_id=task.id,
            agent_id="agent",
            content="This is a comment",
        )
        created = temp_db.create_comment(comment)

        assert created.id == comment.id

        comments = temp_db.get_comments(EntityType.TASK, task.id)
        assert len(comments) == 1
        assert comments[0].content == "This is a comment"

    def test_multiple_comments_on_entity(self, temp_db):
        """Test multiple comments on the same entity."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        for i in range(5):
            comment = Comment(
                entity_type=EntityType.PRD,
                entity_id=prd.id,
                agent_id=f"agent-{i}",
                content=f"Comment {i}",
            )
            temp_db.create_comment(comment)

        comments = temp_db.get_comments(EntityType.PRD, prd.id)
        assert len(comments) == 5

    def test_comment_types(self, temp_db):
        """Test different comment types."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        for comment_type in [
            CommentType.COMMENT,
            CommentType.QUESTION,
            CommentType.DECISION,
            CommentType.BLOCKER,
        ]:
            comment = Comment(
                entity_type=EntityType.PRD,
                entity_id=prd.id,
                agent_id="agent",
                content="Test",
                comment_type=comment_type,
            )
            temp_db.create_comment(comment)

        comments = temp_db.get_comments(EntityType.PRD, prd.id)
        comment_types = {c.comment_type for c in comments}
        assert len(comment_types) == 4


class TestStatistics:
    """Tests for statistics and aggregation queries."""

    def test_get_project_stats(self, temp_db):
        """Test getting project statistics."""
        project = Project(name="Test")
        temp_db.create_project(project)

        # Create 2 PRDs
        for i in range(2):
            prd = PRD(
                project_id=project.id,
                agent_id="agent",
                title=f"PRD {i}",
                description="Test",
            )
            temp_db.create_prd(prd)

            # Create 3 stories per PRD
            for j in range(3):
                story = Story(
                    prd_id=prd.id,
                    agent_id="agent",
                    title=f"Story {j}",
                    description="Test",
                )
                temp_db.create_story(story)

                # Create 2 tasks per story
                for k in range(2):
                    task = Task(
                        story_id=story.id,
                        agent_id="agent",
                        title=f"Task {k}",
                        description="Test",
                        assigned_to="agent",
                    )
                    temp_db.create_task(task)

        stats = temp_db.get_project_stats(project.id)
        assert stats["prd_count"] == 2
        assert stats["story_count"] == 6
        assert stats["task_count"] == 12

    def test_get_story_task_counts(self, temp_db):
        """Test getting task counts for a story."""
        project = Project(name="Test")
        temp_db.create_project(project)

        prd = PRD(
            project_id=project.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_prd(prd)

        story = Story(
            prd_id=prd.id,
            agent_id="agent",
            title="Test",
            description="Test",
        )
        temp_db.create_story(story)

        # Create 10 tasks, 3 done
        for i in range(10):
            status = TaskStatus.DONE if i < 3 else TaskStatus.TODO
            task = Task(
                story_id=story.id,
                agent_id="agent",
                title=f"Task {i}",
                description="Test",
                assigned_to="agent",
                status=status,
            )
            temp_db.create_task(task)

        total, completed = temp_db.get_story_task_counts(story.id)
        assert total == 10
        assert completed == 3


class TestForeignKeyConstraints:
    """Tests for foreign key constraints and cascading deletes."""

    def test_foreign_key_enforcement(self, temp_db):
        """Test that foreign keys are enforced."""
        # Try to create PRD with non-existent project - should fail
        # Note: SQLite will only enforce this if PRAGMA foreign_keys = ON
        prd = PRD(
            project_id="nonexistent",
            agent_id="agent",
            title="Test",
            description="Test",
        )

        with pytest.raises(sqlite3.IntegrityError):
            temp_db.create_prd(prd)

