"""High-level store operations for noGojira."""


from .database import Database
from .events import Event, EventType, get_event_queue
from .models import (
    PRD,
    Comment,
    CommentCreate,
    EntityType,
    PRDCreate,
    PRDUpdate,
    PRDWithStats,
    Project,
    ProjectCreate,
    ProjectProgress,
    ProjectUpdate,
    ProjectWithStats,
    Story,
    StoryCreate,
    StoryProgress,
    StoryUpdate,
    StoryWithStats,
    Task,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
    TaskWithContext,
)


class Store:
    """High-level store for noGojira business logic."""

    def __init__(self, db: Database | None = None):
        """Initialize store with database."""
        self.db = db or Database()
        self.events = get_event_queue()

    # Project operations
    def create_project(self, project_create: ProjectCreate, agent_id: str = "system") -> Project:
        """Create a new project."""
        project = Project(**project_create.model_dump())
        result = self.db.create_project(project)
        
        # Emit event
        self.events.push(Event(
            event_type=EventType.PROJECT_CREATED,
            agent_id=agent_id,
            entity_type="project",
            entity_id=result.id,
            entity_name=result.name,
            details={"description": result.description},
        ))
        
        return result

    def get_project(self, project_id: str) -> ProjectWithStats | None:
        """Get a project by ID with statistics."""
        project = self.db.get_project(project_id)
        if not project:
            return None

        stats = self.db.get_project_stats(project_id)
        return ProjectWithStats(
            **project.model_dump(),
            prd_count=stats["prd_count"],
            story_count=stats["story_count"],
            task_count=stats["task_count"],
        )

    def list_projects(self, limit: int = 50, offset: int = 0) -> list[Project]:
        """List all projects."""
        return self.db.list_projects(limit=limit, offset=offset)

    def update_project(
        self, project_id: str, project_update: ProjectUpdate
    ) -> Project | None:
        """Update a project."""
        updates = {
            k: v for k, v in project_update.model_dump().items() if v is not None
        }
        if not updates:
            return self.db.get_project(project_id)
        return self.db.update_project(project_id, updates)

    # PRD operations
    def create_prd(self, prd_create: PRDCreate, agent_id: str = "system") -> PRD:
        """Create a new PRD."""
        # Verify project exists
        project = self.db.get_project(prd_create.project_id)
        if not project:
            raise ValueError(f"Project {prd_create.project_id} not found")

        prd = PRD(**prd_create.model_dump())
        result = self.db.create_prd(prd)
        
        # Emit event
        self.events.push(Event(
            event_type=EventType.PRD_CREATED,
            agent_id=agent_id,
            entity_type="prd",
            entity_id=result.id,
            entity_name=result.title,
            details={"project_id": result.project_id, "status": result.status},
        ))
        
        return result

    def get_prd(self, prd_id: str) -> PRD | None:
        """Get a PRD by ID."""
        return self.db.get_prd(prd_id)

    def get_prd_with_stats(self, prd_id: str) -> PRDWithStats | None:
        """Get a PRD with statistics."""
        prd = self.db.get_prd(prd_id)
        if not prd:
            return None

        # Count stories
        stories = self.db.list_stories(prd_id=prd_id, limit=1000)
        story_count = len(stories)

        # Count tasks across all stories
        task_count = 0
        for story in stories:
            tasks = self.db.list_tasks(story_id=story.id, limit=1000)
            task_count += len(tasks)

        return PRDWithStats(
            **prd.model_dump(),
            story_count=story_count,
            task_count=task_count,
        )

    def list_prds(
        self,
        project_id: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PRD]:
        """List PRDs with optional filters."""
        return self.db.list_prds(
            project_id=project_id,
            status=status,
            created_by=created_by,
            limit=limit,
            offset=offset,
        )

    def update_prd(self, prd_id: str, prd_update: PRDUpdate) -> PRD | None:
        """Update a PRD."""
        updates = {k: v for k, v in prd_update.model_dump().items() if v is not None}
        if not updates:
            return self.db.get_prd(prd_id)
        return self.db.update_prd(prd_id, updates)

    # Story operations
    def create_story(self, story_create: StoryCreate, agent_id: str = "system") -> Story:
        """Create a new story."""
        # Verify PRD exists
        prd = self.db.get_prd(story_create.prd_id)
        if not prd:
            raise ValueError(f"PRD {story_create.prd_id} not found")

        story = Story(**story_create.model_dump())
        result = self.db.create_story(story)
        
        # Emit event
        self.events.push(Event(
            event_type=EventType.STORY_CREATED,
            agent_id=agent_id,
            entity_type="story",
            entity_id=result.id,
            entity_name=result.title,
            details={"prd_id": result.prd_id, "status": result.status},
        ))
        
        return result

    def get_story(self, story_id: str) -> Story | None:
        """Get a story by ID."""
        return self.db.get_story(story_id)

    def get_story_with_stats(self, story_id: str) -> StoryWithStats | None:
        """Get a story with task statistics."""
        story = self.db.get_story(story_id)
        if not story:
            return None

        total, completed = self.db.get_story_task_counts(story_id)

        return StoryWithStats(
            **story.model_dump(),
            task_count=total,
            completed_tasks=completed,
        )

    def list_stories(
        self,
        prd_id: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Story]:
        """List stories with optional filters."""
        return self.db.list_stories(
            prd_id=prd_id,
            status=status,
            assigned_to=assigned_to,
            limit=limit,
            offset=offset,
        )

    def update_story(
        self, story_id: str, story_update: StoryUpdate
    ) -> Story | None:
        """Update a story."""
        updates = {k: v for k, v in story_update.model_dump().items() if v is not None}
        if not updates:
            return self.db.get_story(story_id)
        return self.db.update_story(story_id, updates)

    # Task operations
    def create_task(self, task_create: TaskCreate, agent_id: str = "system") -> Task:
        """Create a new task."""
        # Verify story exists
        story = self.db.get_story(task_create.story_id)
        if not story:
            raise ValueError(f"Story {task_create.story_id} not found")

        # Verify dependencies exist
        for dep_id in task_create.depends_on:
            dep_task = self.db.get_task(dep_id)
            if not dep_task:
                raise ValueError(f"Dependency task {dep_id} not found")

        task = Task(**task_create.model_dump())
        result = self.db.create_task(task)
        
        # Emit event
        self.events.push(Event(
            event_type=EventType.TASK_CREATED,
            agent_id=agent_id,
            entity_type="task",
            entity_id=result.id,
            entity_name=result.title,
            details={"story_id": result.story_id, "assigned_to": result.assigned_to},
        ))
        
        return result

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self.db.get_task(task_id)

    def list_tasks(
        self,
        story_id: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with optional filters."""
        return self.db.list_tasks(
            story_id=story_id,
            status=status,
            assigned_to=assigned_to,
            limit=limit,
            offset=offset,
        )

    def update_task(self, task_id: str, task_update: TaskUpdate) -> Task | None:
        """Update a task."""
        # Verify dependencies exist if being updated
        if task_update.depends_on is not None:
            for dep_id in task_update.depends_on:
                dep_task = self.db.get_task(dep_id)
                if not dep_task:
                    raise ValueError(f"Dependency task {dep_id} not found")

        updates = {k: v for k, v in task_update.model_dump().items() if v is not None}
        if not updates:
            return self.db.get_task(task_id)
        return self.db.update_task(task_id, updates)

    def get_agent_workload(
        self,
        agent_id: str,
        status: str | None = None,
        project_id: str | None = None,
    ) -> list[TaskWithContext]:
        """Get all tasks assigned to an agent with context."""
        # Get all tasks for the agent
        tasks = self.db.list_tasks(assigned_to=agent_id, status=status, limit=1000)

        # Build context for each task
        result = []
        for task in tasks:
            # Get story
            story = self.db.get_story(task.story_id)
            if not story:
                continue

            # Get PRD
            prd = self.db.get_prd(story.prd_id)
            if not prd:
                continue

            # Filter by project if specified
            if project_id and prd.project_id != project_id:
                continue

            task_with_context = TaskWithContext(
                **task.model_dump(),
                story_title=story.title,
                prd_title=prd.title,
                project_id=prd.project_id,
            )
            result.append(task_with_context)

        return result

    # Comment operations
    def add_comment(self, comment_create: CommentCreate) -> Comment:
        """Add a comment to an entity."""
        # Verify entity exists
        entity_id = comment_create.entity_id
        entity_type = comment_create.entity_type

        if entity_type == EntityType.PRD:
            entity = self.db.get_prd(entity_id)
        elif entity_type == EntityType.STORY:
            entity = self.db.get_story(entity_id)
        elif entity_type == EntityType.TASK:
            entity = self.db.get_task(entity_id)
        else:
            raise ValueError(f"Invalid entity type: {entity_type}")

        if not entity:
            raise ValueError(f"{entity_type.value} {entity_id} not found")

        comment = Comment(**comment_create.model_dump())
        return self.db.create_comment(comment)

    def get_comments(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Comment]:
        """Get all comments for an entity."""
        return self.db.get_comments(entity_type, entity_id, limit=limit, offset=offset)

    # Progress tracking
    def get_story_progress(self, story_id: str) -> StoryProgress | None:
        """Get progress statistics for a story."""
        story = self.db.get_story(story_id)
        if not story:
            return None

        # Get all tasks for the story
        tasks = self.db.list_tasks(story_id=story_id, limit=1000)

        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        blocked_tasks = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)

        completion_percentage = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        )

        return StoryProgress(
            story=story,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            blocked_tasks=blocked_tasks,
            completion_percentage=completion_percentage,
        )

    def get_project_progress(self, project_id: str) -> ProjectProgress | None:
        """Get overall progress statistics for a project."""
        project = self.db.get_project(project_id)
        if not project:
            return None

        # Get all PRDs
        prds = self.db.list_prds(project_id=project_id, limit=1000)
        total_prds = len(prds)

        # Get all stories across all PRDs
        all_stories = []
        for prd in prds:
            stories = self.db.list_stories(prd_id=prd.id, limit=1000)
            all_stories.extend(stories)

        total_stories = len(all_stories)

        # Count stories by status
        stories_by_status: dict[str, int] = {}
        for story in all_stories:
            status = story.status.value
            stories_by_status[status] = stories_by_status.get(status, 0) + 1

        # Get all tasks across all stories
        all_tasks = []
        for story in all_stories:
            tasks = self.db.list_tasks(story_id=story.id, limit=1000)
            all_tasks.extend(tasks)

        total_tasks = len(all_tasks)

        # Count tasks by status
        tasks_by_status: dict[str, int] = {}
        for task in all_tasks:
            status = task.status.value
            tasks_by_status[status] = tasks_by_status.get(status, 0) + 1

        # Count tasks by agent
        tasks_by_agent: dict[str, int] = {}
        for task in all_tasks:
            agent = task.assigned_to
            tasks_by_agent[agent] = tasks_by_agent.get(agent, 0) + 1

        # Calculate completion percentage
        completed_tasks = tasks_by_status.get("done", 0)
        completion_percentage = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        )

        return ProjectProgress(
            project_id=project_id,
            total_prds=total_prds,
            total_stories=total_stories,
            total_tasks=total_tasks,
            stories_by_status=stories_by_status,
            tasks_by_status=tasks_by_status,
            tasks_by_agent=tasks_by_agent,
            completion_percentage=completion_percentage,
        )

