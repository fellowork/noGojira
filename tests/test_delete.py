"""Tests für kaskadierendes Löschen."""

import tempfile
from pathlib import Path

import pytest
from src.database import Database
from src.models import (
    ProjectCreate,
    PRDCreate,
    StoryCreate,
    TaskCreate,
)
from src.store import Store


@pytest.fixture
def store():
    """Create a test store with temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield Store(db)


@pytest.fixture
def populated_store(store):
    """Create a store with test data: Project -> PRD -> Story -> Tasks."""
    # Create project
    project = store.create_project(
        ProjectCreate(
            name="Test Project",
            description="Test Description"
        ),
        agent_id="test-agent"
    )
    
    # Create PRD
    prd = store.create_prd(
        PRDCreate(
            project_id=project.id,
            agent_id="test-agent",
            title="Test PRD",
            description="Test PRD Description"
        ),
        agent_id="test-agent"
    )
    
    # Create Stories
    story1 = store.create_story(
        StoryCreate(
            prd_id=prd.id,
            agent_id="test-agent",
            title="Test Story 1",
            description="Test Story 1 Description"
        ),
        agent_id="test-agent"
    )
    
    story2 = store.create_story(
        StoryCreate(
            prd_id=prd.id,
            agent_id="test-agent",
            title="Test Story 2",
            description="Test Story 2 Description"
        ),
        agent_id="test-agent"
    )
    
    # Create Tasks
    task1 = store.create_task(
        TaskCreate(
            story_id=story1.id,
            agent_id="test-agent",
            title="Test Task 1",
            description="Test Task 1 Description",
            assigned_to="test-agent"
        ),
        agent_id="test-agent"
    )
    
    task2 = store.create_task(
        TaskCreate(
            story_id=story1.id,
            agent_id="test-agent",
            title="Test Task 2",
            description="Test Task 2 Description",
            assigned_to="test-agent"
        ),
        agent_id="test-agent"
    )
    
    task3 = store.create_task(
        TaskCreate(
            story_id=story2.id,
            agent_id="test-agent",
            title="Test Task 3",
            description="Test Task 3 Description",
            assigned_to="test-agent"
        ),
        agent_id="test-agent"
    )
    
    return store, project, prd, story1, story2, task1, task2, task3


def test_delete_task(populated_store):
    """Test that deleting a task works."""
    store, project, prd, story1, story2, task1, task2, task3 = populated_store
    
    # Delete task1
    result = store.delete_task(task1.id)
    assert result is True
    
    # Verify task is deleted
    assert store.get_task(task1.id) is None
    
    # Verify other tasks still exist
    assert store.get_task(task2.id) is not None
    assert store.get_task(task3.id) is not None
    
    # Verify stories still exist
    assert store.get_story(story1.id) is not None
    assert store.get_story(story2.id) is not None


def test_delete_story_cascades_to_tasks(populated_store):
    """Test that deleting a story also deletes its tasks."""
    store, project, prd, story1, story2, task1, task2, task3 = populated_store
    
    # Delete story1
    result = store.delete_story(story1.id)
    assert result is True
    
    # Verify story is deleted
    assert store.get_story(story1.id) is None
    
    # Verify story1's tasks are deleted
    assert store.get_task(task1.id) is None
    assert store.get_task(task2.id) is None
    
    # Verify story2 and its task still exist
    assert store.get_story(story2.id) is not None
    assert store.get_task(task3.id) is not None
    
    # Verify PRD still exists
    assert store.get_prd(prd.id) is not None


def test_delete_prd_cascades_to_stories_and_tasks(populated_store):
    """Test that deleting a PRD also deletes its stories and tasks."""
    store, project, prd, story1, story2, task1, task2, task3 = populated_store
    
    # Delete PRD
    result = store.delete_prd(prd.id)
    assert result is True
    
    # Verify PRD is deleted
    assert store.get_prd(prd.id) is None
    
    # Verify all stories are deleted
    assert store.get_story(story1.id) is None
    assert store.get_story(story2.id) is None
    
    # Verify all tasks are deleted
    assert store.get_task(task1.id) is None
    assert store.get_task(task2.id) is None
    assert store.get_task(task3.id) is None
    
    # Verify project still exists
    assert store.get_project(project.id) is not None


def test_delete_project_cascades_to_all(populated_store):
    """Test that deleting a project deletes everything (PRDs, stories, tasks)."""
    store, project, prd, story1, story2, task1, task2, task3 = populated_store
    
    # Delete project
    result = store.delete_project(project.id)
    assert result is True
    
    # Verify project is deleted
    assert store.get_project(project.id) is None
    
    # Verify PRD is deleted
    assert store.get_prd(prd.id) is None
    
    # Verify all stories are deleted
    assert store.get_story(story1.id) is None
    assert store.get_story(story2.id) is None
    
    # Verify all tasks are deleted
    assert store.get_task(task1.id) is None
    assert store.get_task(task2.id) is None
    assert store.get_task(task3.id) is None


def test_delete_nonexistent_task(store):
    """Test that deleting a non-existent task returns False."""
    result = store.delete_task("non-existent-id")
    assert result is False


def test_delete_nonexistent_story(store):
    """Test that deleting a non-existent story returns False."""
    result = store.delete_story("non-existent-id")
    assert result is False


def test_delete_nonexistent_prd(store):
    """Test that deleting a non-existent PRD returns False."""
    result = store.delete_prd("non-existent-id")
    assert result is False


def test_delete_nonexistent_project(store):
    """Test that deleting a non-existent project returns False."""
    result = store.delete_project("non-existent-id")
    assert result is False


def test_delete_project_with_multiple_prds(store):
    """Test cascading delete with multiple PRDs."""
    # Create project
    project = store.create_project(
        ProjectCreate(name="Multi PRD Project", description="Test"),
        agent_id="test-agent"
    )
    
    # Create multiple PRDs
    prd1 = store.create_prd(
        PRDCreate(
            project_id=project.id,
            agent_id="test-agent",
            title="PRD 1",
            description="First PRD"
        ),
        agent_id="test-agent"
    )
    
    prd2 = store.create_prd(
        PRDCreate(
            project_id=project.id,
            agent_id="test-agent",
            title="PRD 2",
            description="Second PRD"
        ),
        agent_id="test-agent"
    )
    
    # Create stories for each PRD
    story1 = store.create_story(
        StoryCreate(
            prd_id=prd1.id,
            agent_id="test-agent",
            title="Story 1",
            description="Story for PRD 1"
        ),
        agent_id="test-agent"
    )
    
    story2 = store.create_story(
        StoryCreate(
            prd_id=prd2.id,
            agent_id="test-agent",
            title="Story 2",
            description="Story for PRD 2"
        ),
        agent_id="test-agent"
    )
    
    # Delete project
    result = store.delete_project(project.id)
    assert result is True
    
    # Verify everything is deleted
    assert store.get_project(project.id) is None
    assert store.get_prd(prd1.id) is None
    assert store.get_prd(prd2.id) is None
    assert store.get_story(story1.id) is None
    assert store.get_story(story2.id) is None


def test_cascading_delete_count(store):
    """Test that cascading delete removes the correct number of items."""
    # Create a complex structure
    project = store.create_project(
        ProjectCreate(name="Count Test Project", description="Test"),
        agent_id="test-agent"
    )
    
    # Create 2 PRDs
    for i in range(2):
        prd = store.create_prd(
            PRDCreate(
                project_id=project.id,
                agent_id="test-agent",
                title=f"PRD {i}",
                description=f"PRD {i} Description"
            ),
            agent_id="test-agent"
        )
        
        # Create 3 stories per PRD
        for j in range(3):
            story = store.create_story(
                StoryCreate(
                    prd_id=prd.id,
                    agent_id="test-agent",
                    title=f"Story {i}-{j}",
                    description=f"Story {i}-{j} Description"
                ),
                agent_id="test-agent"
            )
            
            # Create 2 tasks per story
            for k in range(2):
                store.create_task(
                    TaskCreate(
                        story_id=story.id,
                        agent_id="test-agent",
                        title=f"Task {i}-{j}-{k}",
                        description=f"Task {i}-{j}-{k} Description",
                        assigned_to="test-agent"
                    ),
                    agent_id="test-agent"
                )
    
    # Before deletion: 1 project, 2 PRDs, 6 stories, 12 tasks
    projects = store.list_projects()
    prds = store.list_prds(project_id=project.id, limit=100)
    
    assert len(projects) == 1
    assert len(prds) == 2
    
    # Delete project
    store.delete_project(project.id)
    
    # After deletion: 0 projects
    projects_after = store.list_projects()
    assert len(projects_after) == 0
