"""Data models for agentFlow using Pydantic v2."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# Enums for status fields
class PRDStatus(str, Enum):
    """Valid statuses for PRD."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StoryStatus(str, Enum):
    """Valid statuses for Story."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Valid statuses for Task."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


class CommentType(str, Enum):
    """Valid types for Comment."""

    COMMENT = "comment"
    QUESTION = "question"
    DECISION = "decision"
    BLOCKER = "blocker"


class EntityType(str, Enum):
    """Valid entity types for comments."""

    PRD = "prd"
    STORY = "story"
    TASK = "task"


# Helper function for UTC timestamps
def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# Project Models
class ProjectCreate(BaseModel):
    """Schema for creating a Project."""

    name: str = Field(..., min_length=1, description="Project name")
    description: str | None = Field(None, description="Project description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Project(ProjectCreate):
    """Full Project model with all fields."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique project ID")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=utc_now, description="Last update timestamp")

    model_config = {"json_schema_extra": {"example": {"name": "E-commerce Platform"}}}


class ProjectUpdate(BaseModel):
    """Schema for updating a Project."""

    name: str | None = Field(None, min_length=1)
    description: str | None = None
    metadata: dict[str, Any] | None = None


# PRD Models
class PRDCreate(BaseModel):
    """Schema for creating a PRD."""

    project_id: str = Field(..., description="Parent project ID")
    agent_id: str = Field(..., description="Creator agent ID")
    title: str = Field(..., min_length=1, description="PRD title")
    description: str = Field(..., description="PRD description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PRD(PRDCreate):
    """Full PRD model with all fields."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique PRD ID")
    status: PRDStatus = Field(default=PRDStatus.DRAFT, description="PRD status")
    created_by: str = Field(..., description="Creator agent ID (alias for agent_id)")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=utc_now, description="Last update timestamp")

    def __init__(self, **data):
        """Initialize PRD, handling created_by alias."""
        if "agent_id" in data and "created_by" not in data:
            data["created_by"] = data["agent_id"]
        super().__init__(**data)

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "proj-123",
                "agent_id": "po-agent",
                "title": "User Authentication System",
                "description": "Implement secure user authentication",
            }
        }
    }


class PRDUpdate(BaseModel):
    """Schema for updating a PRD."""

    title: str | None = Field(None, min_length=1)
    description: str | None = None
    status: PRDStatus | None = None
    metadata: dict[str, Any] | None = None


# Story Models
class StoryCreate(BaseModel):
    """Schema for creating a Story."""

    prd_id: str = Field(..., description="Parent PRD ID")
    agent_id: str = Field(..., description="Creator agent ID")
    title: str = Field(..., min_length=1, description="Story title")
    description: str = Field(..., description="Story description")
    acceptance_criteria: str | None = Field(None, description="Acceptance criteria")
    story_points: int | None = Field(None, ge=0, description="Story points estimate")
    assigned_to: str | None = Field(None, description="Assigned agent ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int | None) -> int | None:
        """Validate story points are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Story points must be non-negative")
        return v


class Story(StoryCreate):
    """Full Story model with all fields."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique story ID")
    status: StoryStatus = Field(default=StoryStatus.TODO, description="Story status")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=utc_now, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prd_id": "prd-123",
                "agent_id": "po-agent",
                "title": "Login with Email",
                "description": "Implement email/password login",
                "story_points": 5,
            }
        }
    }


class StoryUpdate(BaseModel):
    """Schema for updating a Story."""

    title: str | None = Field(None, min_length=1)
    description: str | None = None
    status: StoryStatus | None = None
    assigned_to: str | None = None
    story_points: int | None = Field(None, ge=0)
    acceptance_criteria: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int | None) -> int | None:
        """Validate story points are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Story points must be non-negative")
        return v


# Task Models
class TaskCreate(BaseModel):
    """Schema for creating a Task."""

    story_id: str = Field(..., description="Parent story ID")
    agent_id: str = Field(..., description="Creator agent ID")
    title: str = Field(..., min_length=1, description="Task title")
    description: str = Field(..., description="Task description")
    assigned_to: str = Field(..., description="Assigned agent ID (required)")
    depends_on: list[str] = Field(
        default_factory=list, description="List of task IDs this depends on"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[str]) -> list[str]:
        """Validate depends_on list has unique values."""
        if len(v) != len(set(v)):
            raise ValueError("depends_on must contain unique task IDs")
        return v


class Task(TaskCreate):
    """Full Task model with all fields."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique task ID")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task status")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=utc_now, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "story_id": "story-123",
                "agent_id": "backend-agent",
                "title": "Design API endpoints",
                "description": "Create REST API for authentication",
                "assigned_to": "backend-agent",
            }
        }
    }


class TaskUpdate(BaseModel):
    """Schema for updating a Task."""

    title: str | None = Field(None, min_length=1)
    description: str | None = None
    status: TaskStatus | None = None
    assigned_to: str | None = None
    depends_on: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[str] | None) -> list[str] | None:
        """Validate depends_on list has unique values."""
        if v is not None and len(v) != len(set(v)):
            raise ValueError("depends_on must contain unique task IDs")
        return v


# Comment Models
class CommentCreate(BaseModel):
    """Schema for creating a Comment."""

    entity_type: EntityType = Field(..., description="Type of entity (prd, story, task)")
    entity_id: str = Field(..., description="ID of the parent entity")
    agent_id: str = Field(..., description="Author agent ID")
    content: str = Field(..., min_length=1, description="Comment content")
    comment_type: CommentType = Field(
        default=CommentType.COMMENT, description="Type of comment"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Comment(CommentCreate):
    """Full Comment model with all fields."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique comment ID")
    author: str = Field(..., description="Author agent ID (alias for agent_id)")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    def __init__(self, **data):
        """Initialize Comment, handling author alias."""
        if "agent_id" in data and "author" not in data:
            data["author"] = data["agent_id"]
        super().__init__(**data)

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_type": "task",
                "entity_id": "task-123",
                "agent_id": "backend-agent",
                "content": "Started implementing JWT authentication",
            }
        }
    }


# Response models with nested data
class PRDWithStats(PRD):
    """PRD with statistics about stories and tasks."""

    story_count: int = Field(0, description="Number of stories")
    task_count: int = Field(0, description="Number of tasks")


class StoryWithStats(Story):
    """Story with statistics about tasks."""

    task_count: int = Field(0, description="Number of tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")


class ProjectWithStats(Project):
    """Project with statistics."""

    prd_count: int = Field(0, description="Number of PRDs")
    story_count: int = Field(0, description="Number of stories")
    task_count: int = Field(0, description="Number of tasks")


# Progress tracking models
class StoryProgress(BaseModel):
    """Progress statistics for a Story."""

    story: Story
    total_tasks: int = Field(0, description="Total number of tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")
    in_progress_tasks: int = Field(0, description="Number of in-progress tasks")
    blocked_tasks: int = Field(0, description="Number of blocked tasks")
    completion_percentage: float = Field(0.0, ge=0, le=100, description="Completion percentage")


class ProjectProgress(BaseModel):
    """Progress statistics for a Project."""

    project_id: str
    total_prds: int = Field(0, description="Total number of PRDs")
    total_stories: int = Field(0, description="Total number of stories")
    total_tasks: int = Field(0, description="Total number of tasks")
    stories_by_status: dict[str, int] = Field(
        default_factory=dict, description="Story counts by status"
    )
    tasks_by_status: dict[str, int] = Field(
        default_factory=dict, description="Task counts by status"
    )
    tasks_by_agent: dict[str, int] = Field(
        default_factory=dict, description="Task counts by agent"
    )
    completion_percentage: float = Field(0.0, ge=0, le=100, description="Overall completion %")


# Task with context for agent workload
class TaskWithContext(Task):
    """Task with additional context (story and PRD info)."""

    story_title: str = Field(..., description="Parent story title")
    prd_title: str = Field(..., description="Parent PRD title")
    project_id: str = Field(..., description="Parent project ID")

