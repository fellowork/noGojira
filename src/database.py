"""Database layer for noGojira using SQLite."""

import json
import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    PRD,
    Comment,
    EntityType,
    Project,
    Story,
    Task,
)


def get_data_dir() -> Path:
    """Get the data directory for noGojira."""
    data_dir = os.environ.get(
        "NOGOJIRA_DATA_DIR",
        str(Path.home() / ".local" / "share" / "nogojira"),
    )
    return Path(data_dir)


def get_db_path() -> Path:
    """Get the database file path."""
    db_path = os.environ.get("NOGOJIRA_DB_PATH")
    if db_path:
        return Path(db_path)
    return get_data_dir() / "nogojira.db"


class Database:
    """SQLite database manager for noGojira."""

    def __init__(self, db_path: Path | None = None):
        """Initialize database connection."""
        self.db_path = db_path or get_db_path()
        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Projects table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # PRDs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prds (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)

            # Stories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    prd_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'todo',
                    assigned_to TEXT,
                    story_points INTEGER,
                    acceptance_criteria TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (prd_id) REFERENCES prds(id) ON DELETE CASCADE
                )
            """)

            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'todo',
                    assigned_to TEXT NOT NULL,
                    depends_on TEXT DEFAULT '[]',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
                )
            """)

            # Comments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    comment_type TEXT DEFAULT 'comment',
                    created_at TIMESTAMP NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Create indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_stories_prd_id ON stories(prd_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_stories_assigned_to ON stories(assigned_to)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_story_id ON tasks(story_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_comments_entity ON comments(entity_type, entity_id)"
            )

    # Helper methods for serialization
    def _serialize_metadata(self, metadata: dict[str, Any]) -> str:
        """Serialize metadata dict to JSON string."""
        return json.dumps(metadata)

    def _deserialize_metadata(self, metadata_str: str) -> dict[str, Any]:
        """Deserialize metadata JSON string to dict."""
        return json.loads(metadata_str) if metadata_str else {}

    def _serialize_list(self, items: list[str]) -> str:
        """Serialize list to JSON string."""
        return json.dumps(items)

    def _deserialize_list(self, items_str: str) -> list[str]:
        """Deserialize JSON string to list."""
        return json.loads(items_str) if items_str else []

    # Project CRUD operations
    def create_project(self, project: Project) -> Project:
        """Create a new project."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, description, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.name,
                    project.description,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                    self._serialize_metadata(project.metadata),
                ),
            )
        return project

    def get_project(self, project_id: str) -> Project | None:
        """Get a project by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            if row:
                return Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=self._deserialize_metadata(row["metadata"]),
                )
            return None

    def list_projects(self, limit: int = 50, offset: int = 0) -> list[Project]:
        """List all projects with pagination."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM projects ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            projects = []
            for row in cursor.fetchall():
                projects.append(
                    Project(
                        id=row["id"],
                        name=row["name"],
                        description=row["description"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        metadata=self._deserialize_metadata(row["metadata"]),
                    )
                )
            return projects

    def update_project(
        self, project_id: str, updates: dict[str, Any]
    ) -> Project | None:
        """Update a project."""
        with self._get_connection() as conn:
            set_clauses = []
            values = []

            if "name" in updates:
                set_clauses.append("name = ?")
                values.append(updates["name"])
            if "description" in updates:
                set_clauses.append("description = ?")
                values.append(updates["description"])
            if "metadata" in updates:
                set_clauses.append("metadata = ?")
                values.append(self._serialize_metadata(updates["metadata"]))

            if not set_clauses:
                return self.get_project(project_id)

            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(project_id)

            conn.execute(
                f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )

        return self.get_project(project_id)

    # PRD CRUD operations
    def create_prd(self, prd: PRD) -> PRD:
        """Create a new PRD."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO prds
                (id, project_id, title, description, status, created_by,
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prd.id,
                    prd.project_id,
                    prd.title,
                    prd.description,
                    prd.status.value,
                    prd.created_by,
                    prd.created_at.isoformat(),
                    prd.updated_at.isoformat(),
                    self._serialize_metadata(prd.metadata),
                ),
            )
        return prd

    def get_prd(self, prd_id: str) -> PRD | None:
        """Get a PRD by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM prds WHERE id = ?",
                (prd_id,),
            )
            row = cursor.fetchone()
            if row:
                return PRD(
                    id=row["id"],
                    project_id=row["project_id"],
                    agent_id=row["created_by"],
                    created_by=row["created_by"],
                    title=row["title"],
                    description=row["description"],
                    status=row["status"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=self._deserialize_metadata(row["metadata"]),
                )
            return None

    def list_prds(
        self,
        project_id: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PRD]:
        """List PRDs with optional filters."""
        with self._get_connection() as conn:
            where_clauses = []
            values = []

            if project_id:
                where_clauses.append("project_id = ?")
                values.append(project_id)
            if status:
                where_clauses.append("status = ?")
                values.append(status)
            if created_by:
                where_clauses.append("created_by = ?")
                values.append(created_by)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            values.extend([limit, offset])

            cursor = conn.execute(
                f"SELECT * FROM prds {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                values,
            )

            prds = []
            for row in cursor.fetchall():
                prds.append(
                    PRD(
                        id=row["id"],
                        project_id=row["project_id"],
                        agent_id=row["created_by"],
                        created_by=row["created_by"],
                        title=row["title"],
                        description=row["description"],
                        status=row["status"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        metadata=self._deserialize_metadata(row["metadata"]),
                    )
                )
            return prds

    def update_prd(self, prd_id: str, updates: dict[str, Any]) -> PRD | None:
        """Update a PRD."""
        with self._get_connection() as conn:
            set_clauses = []
            values = []

            if "title" in updates:
                set_clauses.append("title = ?")
                values.append(updates["title"])
            if "description" in updates:
                set_clauses.append("description = ?")
                values.append(updates["description"])
            if "status" in updates:
                set_clauses.append("status = ?")
                values.append(
                    updates["status"].value
                    if hasattr(updates["status"], "value")
                    else updates["status"]
                )
            if "metadata" in updates:
                set_clauses.append("metadata = ?")
                values.append(self._serialize_metadata(updates["metadata"]))

            if not set_clauses:
                return self.get_prd(prd_id)

            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(prd_id)

            conn.execute(
                f"UPDATE prds SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )

        return self.get_prd(prd_id)

    # Story CRUD operations
    def create_story(self, story: Story) -> Story:
        """Create a new story."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO stories
                (id, prd_id, agent_id, title, description, status, assigned_to,
                 story_points, acceptance_criteria, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    story.id,
                    story.prd_id,
                    story.agent_id,
                    story.title,
                    story.description,
                    story.status.value,
                    story.assigned_to,
                    story.story_points,
                    story.acceptance_criteria,
                    story.created_at.isoformat(),
                    story.updated_at.isoformat(),
                    self._serialize_metadata(story.metadata),
                ),
            )
        return story

    def get_story(self, story_id: str) -> Story | None:
        """Get a story by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM stories WHERE id = ?",
                (story_id,),
            )
            row = cursor.fetchone()
            if row:
                return Story(
                    id=row["id"],
                    prd_id=row["prd_id"],
                    agent_id=row["agent_id"],
                    title=row["title"],
                    description=row["description"],
                    status=row["status"],
                    assigned_to=row["assigned_to"],
                    story_points=row["story_points"],
                    acceptance_criteria=row["acceptance_criteria"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=self._deserialize_metadata(row["metadata"]),
                )
            return None

    def list_stories(
        self,
        prd_id: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Story]:
        """List stories with optional filters."""
        with self._get_connection() as conn:
            where_clauses = []
            values = []

            if prd_id:
                where_clauses.append("prd_id = ?")
                values.append(prd_id)
            if status:
                where_clauses.append("status = ?")
                values.append(status)
            if assigned_to:
                where_clauses.append("assigned_to = ?")
                values.append(assigned_to)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            values.extend([limit, offset])

            cursor = conn.execute(
                f"SELECT * FROM stories {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                values,
            )

            stories = []
            for row in cursor.fetchall():
                stories.append(
                    Story(
                        id=row["id"],
                        prd_id=row["prd_id"],
                        agent_id=row["agent_id"],
                        title=row["title"],
                        description=row["description"],
                        status=row["status"],
                        assigned_to=row["assigned_to"],
                        story_points=row["story_points"],
                        acceptance_criteria=row["acceptance_criteria"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        metadata=self._deserialize_metadata(row["metadata"]),
                    )
                )
            return stories

    def update_story(self, story_id: str, updates: dict[str, Any]) -> Story | None:
        """Update a story."""
        with self._get_connection() as conn:
            set_clauses = []
            values = []

            if "title" in updates:
                set_clauses.append("title = ?")
                values.append(updates["title"])
            if "description" in updates:
                set_clauses.append("description = ?")
                values.append(updates["description"])
            if "status" in updates:
                set_clauses.append("status = ?")
                values.append(
                    updates["status"].value
                    if hasattr(updates["status"], "value")
                    else updates["status"]
                )
            if "assigned_to" in updates:
                set_clauses.append("assigned_to = ?")
                values.append(updates["assigned_to"])
            if "story_points" in updates:
                set_clauses.append("story_points = ?")
                values.append(updates["story_points"])
            if "acceptance_criteria" in updates:
                set_clauses.append("acceptance_criteria = ?")
                values.append(updates["acceptance_criteria"])
            if "metadata" in updates:
                set_clauses.append("metadata = ?")
                values.append(self._serialize_metadata(updates["metadata"]))

            if not set_clauses:
                return self.get_story(story_id)

            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(story_id)

            conn.execute(
                f"UPDATE stories SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )

        return self.get_story(story_id)

    # Task CRUD operations
    def create_task(self, task: Task) -> Task:
        """Create a new task."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tasks
                (id, story_id, agent_id, title, description, status, assigned_to,
                 depends_on, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.story_id,
                    task.agent_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.assigned_to,
                    self._serialize_list(task.depends_on),
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    self._serialize_metadata(task.metadata),
                ),
            )
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                return Task(
                    id=row["id"],
                    story_id=row["story_id"],
                    agent_id=row["agent_id"],
                    title=row["title"],
                    description=row["description"],
                    status=row["status"],
                    assigned_to=row["assigned_to"],
                    depends_on=self._deserialize_list(row["depends_on"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=self._deserialize_metadata(row["metadata"]),
                )
            return None

    def list_tasks(
        self,
        story_id: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with optional filters."""
        with self._get_connection() as conn:
            where_clauses = []
            values = []

            if story_id:
                where_clauses.append("story_id = ?")
                values.append(story_id)
            if status:
                where_clauses.append("status = ?")
                values.append(status)
            if assigned_to:
                where_clauses.append("assigned_to = ?")
                values.append(assigned_to)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            values.extend([limit, offset])

            cursor = conn.execute(
                f"SELECT * FROM tasks {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                values,
            )

            tasks = []
            for row in cursor.fetchall():
                tasks.append(
                    Task(
                        id=row["id"],
                        story_id=row["story_id"],
                        agent_id=row["agent_id"],
                        title=row["title"],
                        description=row["description"],
                        status=row["status"],
                        assigned_to=row["assigned_to"],
                        depends_on=self._deserialize_list(row["depends_on"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        metadata=self._deserialize_metadata(row["metadata"]),
                    )
                )
            return tasks

    def update_task(self, task_id: str, updates: dict[str, Any]) -> Task | None:
        """Update a task."""
        with self._get_connection() as conn:
            set_clauses = []
            values = []

            if "title" in updates:
                set_clauses.append("title = ?")
                values.append(updates["title"])
            if "description" in updates:
                set_clauses.append("description = ?")
                values.append(updates["description"])
            if "status" in updates:
                set_clauses.append("status = ?")
                values.append(
                    updates["status"].value
                    if hasattr(updates["status"], "value")
                    else updates["status"]
                )
            if "assigned_to" in updates:
                set_clauses.append("assigned_to = ?")
                values.append(updates["assigned_to"])
            if "depends_on" in updates:
                set_clauses.append("depends_on = ?")
                values.append(self._serialize_list(updates["depends_on"]))
            if "metadata" in updates:
                set_clauses.append("metadata = ?")
                values.append(self._serialize_metadata(updates["metadata"]))

            if not set_clauses:
                return self.get_task(task_id)

            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(task_id)

            conn.execute(
                f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )

        return self.get_task(task_id)

    # Comment operations
    def create_comment(self, comment: Comment) -> Comment:
        """Create a new comment."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO comments
                (id, entity_type, entity_id, author, content, comment_type,
                 created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comment.id,
                    comment.entity_type.value,
                    comment.entity_id,
                    comment.author,
                    comment.content,
                    comment.comment_type.value,
                    comment.created_at.isoformat(),
                    self._serialize_metadata(comment.metadata),
                ),
            )
        return comment

    def get_comments(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Comment]:
        """Get all comments for an entity."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM comments
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
                """,
                (entity_type.value, entity_id, limit, offset),
            )

            comments = []
            for row in cursor.fetchall():
                comments.append(
                    Comment(
                        id=row["id"],
                        entity_type=row["entity_type"],
                        entity_id=row["entity_id"],
                        agent_id=row["author"],
                        author=row["author"],
                        content=row["content"],
                        comment_type=row["comment_type"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        metadata=self._deserialize_metadata(row["metadata"]),
                    )
                )
            return comments

    # Statistics and aggregation queries
    def get_project_stats(self, project_id: str) -> dict[str, int]:
        """Get statistics for a project."""
        with self._get_connection() as conn:
            # Count PRDs
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM prds WHERE project_id = ?",
                (project_id,),
            )
            prd_count = cursor.fetchone()["count"]

            # Count Stories
            cursor = conn.execute(
                """
                SELECT COUNT(*) as count FROM stories
                WHERE prd_id IN (SELECT id FROM prds WHERE project_id = ?)
                """,
                (project_id,),
            )
            story_count = cursor.fetchone()["count"]

            # Count Tasks
            cursor = conn.execute(
                """
                SELECT COUNT(*) as count FROM tasks
                WHERE story_id IN (
                    SELECT id FROM stories WHERE prd_id IN (
                        SELECT id FROM prds WHERE project_id = ?
                    )
                )
                """,
                (project_id,),
            )
            task_count = cursor.fetchone()["count"]

            return {
                "prd_count": prd_count,
                "story_count": story_count,
                "task_count": task_count,
            }

    def get_story_task_counts(self, story_id: str) -> tuple[int, int]:
        """Get total and completed task counts for a story."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE story_id = ?",
                (story_id,),
            )
            total = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE story_id = ? AND status = 'done'",
                (story_id,),
            )
            completed = cursor.fetchone()["count"]

            return total, completed

