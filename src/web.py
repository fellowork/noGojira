"""Reflex Web UI for noGojira - Modern dashboard."""

import reflex as rx

from .events import get_event_queue
from .store import Store

# Initialize
store = Store()
events = get_event_queue()


class State(rx.State):
    """The app state."""

    # Current page
    current_page: str = "projects"
    
    # Stats
    total_projects: int = 0
    total_prds: int = 0
    total_stories: int = 0
    total_tasks: int = 0
    
    # Projects data
    projects: list[dict] = []
    
    # Recent activity
    recent_events: list[dict] = []
    
    # Project details
    selected_project_id: str = ""
    selected_project: dict = {}
    project_stories: list[dict] = []
    tasks_todo: list[dict] = []
    tasks_in_progress: list[dict] = []
    tasks_blocked: list[dict] = []
    tasks_review: list[dict] = []
    tasks_done: list[dict] = []
    
    # UI state
    stories_expanded: bool = False
    
    # Modal state
    show_task_modal: bool = False
    show_story_modal: bool = False
    selected_task: dict = {}
    selected_story: dict = {}

    def on_load(self):
        """Load initial data."""
        self.refresh_all()

    def refresh_all(self):
        """Refresh all dashboard data."""
        self.refresh_stats()
        self.refresh_projects()
        self.refresh_activity()

    def refresh_stats(self):
        """Refresh dashboard statistics."""
        projects = store.list_projects(limit=1000)
        self.total_projects = len(projects)

        prd_count = 0
        story_count = 0
        task_count = 0

        for project in projects:
            prds = store.list_prds(project_id=project.id, limit=1000)
            prd_count += len(prds)

            for prd in prds:
                stories = store.list_stories(prd_id=prd.id, limit=1000)
                story_count += len(stories)

                for story in stories:
                    tasks = store.list_tasks(story_id=story.id, limit=1000)
                    task_count += len(tasks)

        self.total_prds = prd_count
        self.total_stories = story_count
        self.total_tasks = task_count

    def refresh_projects(self):
        """Refresh projects list."""
        projects = store.list_projects(limit=100)
        self.projects = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description or "No description",
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for p in projects
        ]

    def refresh_activity(self):
        """Refresh activity stream."""
        recent = events.get_recent(limit=20)
        self.recent_events = [
            {
                "id": e.id,
                "display": e.to_display_string(),
                "timestamp": e.timestamp.strftime("%H:%M:%S"),
                "agent": e.agent_id,
                "type": e.event_type.value,
            }
            for e in recent
        ]

    def set_page(self, page: str):
        """Change current page."""
        self.current_page = page
    
    def toggle_stories(self):
        """Toggle stories section visibility."""
        self.stories_expanded = not self.stories_expanded
    
    def open_task_modal(self, task: dict):
        """Open task detail modal."""
        self.selected_task = task
        self.show_task_modal = True
    
    def close_task_modal(self):
        """Close task detail modal."""
        self.show_task_modal = False
    
    def open_story_modal(self, story: dict):
        """Open story detail modal."""
        self.selected_story = story
        self.show_story_modal = True
    
    def close_story_modal(self):
        """Close story detail modal."""
        self.show_story_modal = False
    
    def view_project_details(self, project_id: str):
        """Navigate to project details page."""
        self.selected_project_id = project_id
        self.stories_expanded = False  # Start collapsed
        self.load_project_details()
        self.current_page = "project_details"
    
    def load_project_details(self):
        """Load detailed data for the selected project."""
        if not self.selected_project_id:
            return
        
        # Get project info
        project = store.get_project(self.selected_project_id)
        if not project:
            return
        
        self.selected_project = {
            "id": project.id,
            "name": project.name,
            "description": project.description or "No description",
            "created_at": project.created_at.strftime("%Y-%m-%d %H:%M"),
            "prd_count": project.prd_count,
            "story_count": project.story_count,
            "task_count": project.task_count,
        }
        
        # Get all PRDs for this project
        prds = store.list_prds(project_id=self.selected_project_id, limit=1000)
        
        # Get all stories across all PRDs
        all_stories = []
        for prd in prds:
            stories = store.list_stories(prd_id=prd.id, limit=1000)
            for story in stories:
                # Get task counts for this story
                tasks = store.list_tasks(story_id=story.id, limit=1000)
                total_tasks = len(tasks)
                completed_tasks = sum(1 for t in tasks if t.status.value == "done")
                
                all_stories.append({
                    "id": story.id,
                    "title": story.title,
                    "description": story.description,
                    "status": story.status.value,
                    "prd_title": prd.title,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "progress": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                })
        
        # Reverse the order so newest stories appear first
        self.project_stories = list(reversed(all_stories))
        
        # Get all tasks and group by status
        todo_tasks = []
        in_progress_tasks = []
        blocked_tasks = []
        review_tasks = []
        done_tasks = []
        
        # Iterate through stories in their original order to maintain task order
        for story in reversed(all_stories):  # Reverse to get tasks in correct order
            tasks = store.list_tasks(story_id=story["id"], limit=1000)
            # Reverse tasks so newest appear first
            for task in reversed(tasks):
                task_dict = {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value,
                    "story_title": story["title"],
                    "story_id": story["id"],
                    "assigned_to": task.assigned_to,
                }
                status_key = task.status.value
                if status_key == "todo":
                    todo_tasks.append(task_dict)
                elif status_key == "in_progress":
                    in_progress_tasks.append(task_dict)
                elif status_key == "blocked":
                    blocked_tasks.append(task_dict)
                elif status_key == "review":
                    review_tasks.append(task_dict)
                elif status_key == "done":
                    done_tasks.append(task_dict)
        
        self.tasks_todo = todo_tasks
        self.tasks_in_progress = in_progress_tasks
        self.tasks_blocked = blocked_tasks
        self.tasks_review = review_tasks
        self.tasks_done = done_tasks


def navbar() -> rx.Component:
    """Top navigation bar."""
    return rx.box(
        rx.flex(
            # Left side: Logo & Brand
            rx.hstack(
                rx.heading(
                    "NoGojira",
                    size="6",
                    weight="bold",
                    color=rx.color("grass", 11),
                ),
                rx.text(
                    "AI Builds. No Tickets",
                    size="2",
                    color=rx.color("gray", 11),
                    weight="medium",
                    margin_left="12px",
                ),
                spacing="0",
                align="center",
            ),
            # Center: Navigation
            rx.hstack(
                rx.button(
                    "Projekte",
                    on_click=lambda: State.set_page("projects"),
                    variant=rx.cond(State.current_page == "projects", "soft", "ghost"),
                    color_scheme=rx.cond(State.current_page == "projects", "grass", "gray"),
                ),
                rx.button(
                    "Agent Monitor",
                    on_click=lambda: State.set_page("agents"),
                    variant=rx.cond(State.current_page == "agents", "soft", "ghost"),
                    color_scheme=rx.cond(State.current_page == "agents", "grass", "gray"),
                ),
                rx.button(
                    "Statistics",
                    on_click=lambda: State.set_page("statistics"),
                    variant=rx.cond(State.current_page == "statistics", "soft", "ghost"),
                    color_scheme=rx.cond(State.current_page == "statistics", "grass", "gray"),
                ),
                spacing="4",
                align="center",
                margin_left="48px",
            ),
            rx.spacer(),
            # Right side: Theme toggle & Status indicator
            rx.hstack(
                rx.button(
                    rx.icon("sun", size=18),
                    on_click=rx.toggle_color_mode,
                    variant="ghost",
                    size="2",
                    cursor="pointer",
                ),
                rx.badge(
                    "Live",
                    color_scheme="green",
                    variant="soft",
                ),
                spacing="3",
                align="center",
            ),
            direction="row",
            justify="start",
            align="center",
            width="100%",
            padding_x="24px",
            padding_y="16px",
        ),
        width="100%",
        border_bottom=f"1px solid {rx.color('gray', 6)}",
        background=rx.color("gray", 2),
    )


def empty_projects() -> rx.Component:
    """Empty state for projects page."""
    return rx.center(
        rx.vstack(
            rx.icon(
                "folder_x",
                size=64,
                color=rx.color("gray", 8),
                stroke_width=1.5,
            ),
            rx.heading(
                "Noch keine Projekte",
                size="7",
                weight="bold",
                text_align="center",
                margin_top="20px",
            ),
            rx.text(
                "Verbinde einen AI-Agenten über MCP, um dein erstes Projekt zu starten.",
                size="3",
                color=rx.color("gray", 10),
                text_align="center",
                max_width="500px",
                line_height="1.6",
            ),
            rx.card(
                rx.vstack(
                    rx.text(
                        "Beispiel MCP Konfiguration:",
                        size="2",
                        weight="bold",
                        color=rx.color("gray", 11),
                        margin_bottom="12px",
                    ),
                    rx.box(
                        rx.code(
                            "uvx --from git+https://github.com/fellowork/noGojira nogojira",
                            font_size="14px",
                            color=rx.color("grass", 11),
                        ),
                        padding="16px",
                        border_radius="8px",
                        background=rx.color("gray", 3),
                        border=f"1px solid {rx.color('gray', 6)}",
                        width="100%",
                    ),
                    spacing="2",
                    align="stretch",
                    width="100%",
                ),
                width="100%",
                max_width="600px",
                padding="20px",
            ),
            spacing="5",
            align="center",
            max_width="700px",
        ),
        height="calc(100vh - 120px)",
        width="100%",
    )


def project_card(project: dict) -> rx.Component:
    """Single project card."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("folder", size=24, color=rx.color("grass", 9)),
                rx.heading(
                    project["name"],
                    size="4",
                    weight="bold",
                ),
                rx.spacer(),
                rx.badge("Active", color_scheme="green", variant="soft"),
                width="100%",
                align="center",
            ),
            rx.text(
                project["description"],
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.divider(),
            rx.hstack(
                rx.text(
                    f"Erstellt: {project['created_at']}",
                    size="1",
                    color=rx.color("gray", 9),
                ),
                rx.spacer(),
                rx.button(
                    "Details",
                    size="1",
                    variant="soft",
                    color_scheme="grass",
                    on_click=lambda: State.view_project_details(project["id"]),
                ),
                width="100%",
                align="center",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        style={
            ":hover": {
                "border_color": rx.color("grass", 8),
                "transform": "translateY(-2px)",
                "transition": "all 0.2s ease",
            },
        },
    )


def projects_grid() -> rx.Component:
    """Grid of project cards."""
    return rx.box(
        rx.cond(
            State.projects.length() > 0,
            rx.vstack(
                rx.flex(
                    rx.heading("Projekte", size="6", weight="bold"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh_cw", size=16),
                        "Aktualisieren",
                        on_click=State.refresh_all,
                        size="2",
                        variant="soft",
                        color_scheme="grass",
                    ),
                    direction="row",
                    justify="between",
                    align="center",
                    width="100%",
                    margin_bottom="20px",
                ),
                rx.grid(
                    rx.foreach(
                        State.projects,
                        project_card,
                    ),
                    columns="3",
                    spacing="4",
                    width="100%",
                ),
                spacing="0",
                width="100%",
                padding="24px",
            ),
            empty_projects(),
        ),
        width="100%",
        height="100%",
    )


def agent_monitor_page() -> rx.Component:
    """Agent monitor page."""
    return rx.center(
        rx.vstack(
            rx.icon("bot", size=64, color=rx.color("grass", 9), stroke_width=1.5),
            rx.heading("Agent Monitor", size="7", weight="bold", margin_top="20px"),
            rx.text(
                "Agent Activity wird hier angezeigt",
                size="3",
                color=rx.color("gray", 10),
                text_align="center",
            ),
            spacing="5",
            align="center",
        ),
        height="calc(100vh - 120px)",
        width="100%",
    )


def statistics_page() -> rx.Component:
    """Statistics page."""
    return rx.box(
        rx.vstack(
            rx.heading("Statistics", size="6", weight="bold", margin_bottom="20px"),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.icon("folder", size=40, color=rx.color("blue", 9), stroke_width=1.5),
                        rx.heading(State.total_projects.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("Projects", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("file_text", size=40, color=rx.color("purple", 9), stroke_width=1.5),
                        rx.heading(State.total_prds.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("PRDs", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("book_open", size=40, color=rx.color("grass", 9), stroke_width=1.5),
                        rx.heading(State.total_stories.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("Stories", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("check_check", size=40, color=rx.color("orange", 9), stroke_width=1.5),
                        rx.heading(State.total_tasks.to_string(), size="8", weight="bold", margin_top="12px"),
                        rx.text("Tasks", size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                        padding="20px",
                    ),
                    width="100%",
                ),
                columns="4",
                spacing="4",
                width="100%",
            ),
            spacing="0",
            width="100%",
        ),
        padding="24px",
        width="100%",
    )


def task_card(task: dict) -> rx.Component:
    """Single task card for the board."""
    return rx.card(
        rx.vstack(
            rx.text(
                task["title"],
                size="2",
                weight="bold",
                color=rx.color("gray", 12),
            ),
            rx.text(
                task["description"],
                size="1",
                color=rx.color("gray", 10),
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
            rx.divider(),
            rx.hstack(
                rx.badge(
                    task["story_title"],
                    size="1",
                    color_scheme="blue",
                    variant="soft",
                ),
                rx.spacer(),
                rx.text(
                    task["assigned_to"],
                    size="1",
                    color=rx.color("gray", 9),
                ),
                width="100%",
                align="center",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        width="100%",
        padding="12px",
        on_click=lambda: State.open_task_modal(task),
        style={
            ":hover": {
                "border_color": rx.color("grass", 8),
                "cursor": "pointer",
            },
        },
    )


def board_column(title: str, tasks: list[dict], color: str) -> rx.Component:
    """Single column in the kanban board."""
    return rx.vstack(
        rx.hstack(
            rx.heading(
                title,
                size="3",
                weight="bold",
            ),
            rx.badge(
                rx.cond(
                    tasks.length() > 0,
                    tasks.length().to_string(),
                    "0",
                ),
                color_scheme=color,
                variant="soft",
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.box(
            rx.cond(
                tasks.length() > 0,
                rx.vstack(
                    rx.foreach(tasks, task_card),
                    spacing="3",
                    width="100%",
                ),
                rx.center(
                    rx.text(
                        "No tasks",
                        size="2",
                        color=rx.color("gray", 9),
                    ),
                    padding="20px",
                ),
            ),
            width="100%",
            height="600px",  # Fixed height for all columns
            overflow_y="auto",
            style={
                # Hide scrollbar for Chrome, Safari and Opera
                "::-webkit-scrollbar": {
                    "display": "none",
                },
                # Hide scrollbar for IE, Edge and Firefox
                "-ms-overflow-style": "none",
                "scrollbar-width": "none",
            },
        ),
        spacing="3",
        align="start",
        width="20%",  # Equal width for all columns (5 columns = 20% each)
        min_width="250px",
        padding="16px",
        border_radius="8px",
        background=rx.color("gray", 2),
        border=f"1px solid {rx.color('gray', 6)}",
    )


def story_card(story: dict) -> rx.Component:
    """Single story card with progress."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("book_open", size=20, color=rx.color("grass", 9)),
                rx.heading(
                    story["title"],
                    size="3",
                    weight="bold",
                ),
                rx.spacer(),
                rx.badge(
                    story["status"],
                    color_scheme=rx.cond(
                        story["status"] == "done",
                        "green",
                        rx.cond(
                            story["status"] == "in_progress",
                            "blue",
                            "gray",
                        ),
                    ),
                    variant="soft",
                ),
                width="100%",
                align="center",
            ),
            rx.text(
                story["description"],
                size="2",
                color=rx.color("gray", 10),
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
            rx.text(
                f"PRD: {story['prd_title']}",
                size="1",
                color=rx.color("gray", 9),
            ),
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        f"Tasks: {story['completed_tasks']}/{story['total_tasks']}",
                        size="2",
                        color=rx.color("gray", 11),
                    ),
                    rx.spacer(),
                    rx.text(
                        f"{story['progress']:.0f}%",
                        size="2",
                        weight="bold",
                        color=rx.color("grass", 11),
                    ),
                    width="100%",
                    align="center",
                ),
                rx.box(
                    rx.box(
                        width=f"{story['progress']}%",
                        height="100%",
                        background=rx.color("grass", 9),
                        border_radius="4px",
                    ),
                    width="100%",
                    height="6px",
                    background=rx.color("gray", 6),
                    border_radius="4px",
                    overflow="hidden",
                ),
                spacing="2",
                width="100%",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        on_click=lambda: State.open_story_modal(story),
        style={
            ":hover": {
                "border_color": rx.color("grass", 8),
                "cursor": "pointer",
            },
        },
    )


def task_detail_modal() -> rx.Component:
    """Modal to show full task details."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon("check-circle", size=24, color=rx.color("grass", 9)),
                    rx.heading(
                        State.selected_task["title"],
                        size="5",
                        weight="bold",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon("x", size=18),
                            variant="ghost",
                            size="2",
                            cursor="pointer",
                        ),
                    ),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                rx.vstack(
                    rx.text("Description", size="2", weight="bold", color=rx.color("gray", 11)),
                    rx.text(
                        State.selected_task["description"],
                        size="2",
                        color=rx.color("gray", 10),
                        line_height="1.6",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.divider(),
                rx.hstack(
                    rx.vstack(
                        rx.text("Story", size="1", color=rx.color("gray", 9)),
                        rx.badge(
                            State.selected_task["story_title"],
                            color_scheme="blue",
                            variant="soft",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Status", size="1", color=rx.color("gray", 9)),
                        rx.badge(
                            State.selected_task["status"],
                            color_scheme="gray",
                            variant="soft",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Assigned To", size="1", color=rx.color("gray", 9)),
                        rx.text(
                            State.selected_task["assigned_to"],
                            size="2",
                            weight="medium",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    spacing="6",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px",
            padding="24px",
        ),
        open=State.show_task_modal,
        on_open_change=State.close_task_modal,
    )


def story_detail_modal() -> rx.Component:
    """Modal to show full story details."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon("book_open", size=24, color=rx.color("grass", 9)),
                    rx.heading(
                        State.selected_story["title"],
                        size="5",
                        weight="bold",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon("x", size=18),
                            variant="ghost",
                            size="2",
                            cursor="pointer",
                        ),
                    ),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                rx.vstack(
                    rx.text("Description", size="2", weight="bold", color=rx.color("gray", 11)),
                    rx.text(
                        State.selected_story["description"],
                        size="2",
                        color=rx.color("gray", 10),
                        line_height="1.6",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.divider(),
                rx.hstack(
                    rx.vstack(
                        rx.text("PRD", size="1", color=rx.color("gray", 9)),
                        rx.text(
                            State.selected_story["prd_title"],
                            size="2",
                            weight="medium",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Status", size="1", color=rx.color("gray", 9)),
                        rx.badge(
                            State.selected_story["status"],
                            color_scheme=rx.cond(
                                State.selected_story["status"] == "done",
                                "green",
                                rx.cond(
                                    State.selected_story["status"] == "in_progress",
                                    "blue",
                                    "gray",
                                ),
                            ),
                            variant="soft",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Progress", size="1", color=rx.color("gray", 9)),
                        rx.text(
                            f"{State.selected_story['completed_tasks']}/{State.selected_story['total_tasks']} tasks ({State.selected_story['progress']:.0f}%)",
                            size="2",
                            weight="medium",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    spacing="6",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px",
            padding="24px",
        ),
        open=State.show_story_modal,
        on_open_change=State.close_story_modal,
    )


def project_details_page() -> rx.Component:
    """Project details page with stories and task board."""
    return rx.box(
        # Modals
        task_detail_modal(),
        story_detail_modal(),
        # Main content
        rx.vstack(
            # Compact header with all info in one card
            rx.card(
                rx.hstack(
                    # Back button
                    rx.button(
                        rx.icon("arrow_left", size=16),
                        "Back to Projects",
                        on_click=lambda: State.set_page("projects"),
                        variant="ghost",
                        size="2",
                    ),
                    rx.box(width="16px"),  # Spacer
                    # Project icon and name with tooltip
                    rx.icon("folder", size=24, color=rx.color("grass", 9)),
                    rx.tooltip(
                        rx.heading(
                            State.selected_project["name"],
                            size="5",
                            weight="bold",
                        ),
                        content=State.selected_project["description"],
                    ),
                    rx.spacer(),
                    # Stats inline in header
                    rx.hstack(
                        rx.vstack(
                            rx.text("PRDs", size="1", color=rx.color("gray", 9)),
                            rx.text(State.selected_project["prd_count"], size="3", weight="bold"),
                            spacing="0",
                            align="center",
                        ),
                        rx.vstack(
                            rx.text("Stories", size="1", color=rx.color("gray", 9)),
                            rx.text(State.selected_project["story_count"], size="3", weight="bold"),
                            spacing="0",
                            align="center",
                        ),
                        rx.vstack(
                            rx.text("Tasks", size="1", color=rx.color("gray", 9)),
                            rx.text(State.selected_project["task_count"], size="3", weight="bold"),
                            spacing="0",
                            align="center",
                        ),
                        spacing="6",
                    ),
                    rx.box(width="8px"),  # Small spacer
                    # Refresh button
                    rx.button(
                        rx.icon("refresh_cw", size=16),
                        on_click=State.load_project_details,
                        variant="ghost",
                        color_scheme="grass",
                        size="2",
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                width="100%",
                margin_bottom="16px",
                padding="12px 16px",
            ),
            # Task board (moved up)
            rx.heading("Task Board", size="5", weight="bold", margin_bottom="12px"),
            rx.box(
                rx.hstack(
                    board_column("TODO", State.tasks_todo, "gray"),
                    board_column("In Progress", State.tasks_in_progress, "blue"),
                    board_column("Blocked", State.tasks_blocked, "red"),
                    board_column("Review", State.tasks_review, "orange"),
                    board_column("Done", State.tasks_done, "green"),
                    spacing="4",
                    width="100%",
                    align="start",
                ),
                width="100%",
                overflow_x="auto",
                margin_bottom="32px",
            ),
            # Stories overview (moved to bottom, collapsible)
            rx.hstack(
                rx.heading("Stories", size="5", weight="bold"),
                rx.badge(
                    State.project_stories.length().to_string(),
                    color_scheme="blue",
                    variant="soft",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon(
                        rx.cond(
                            State.stories_expanded,
                            "chevron-up",
                            "chevron-down",
                        ),
                        size=16,
                    ),
                    rx.cond(
                        State.stories_expanded,
                        "Hide",
                        "Show",
                    ),
                    on_click=State.toggle_stories,
                    variant="ghost",
                    size="2",
                    cursor="pointer",
                ),
                width="100%",
                align="center",
                margin_bottom="12px",
            ),
            rx.cond(
                State.stories_expanded,
                rx.cond(
                    State.project_stories.length() > 0,
                    rx.grid(
                        rx.foreach(State.project_stories, story_card),
                        columns="3",
                        spacing="4",
                        width="100%",
                        margin_bottom="32px",
                    ),
                    rx.center(
                        rx.text(
                            "No stories yet",
                            size="3",
                            color=rx.color("gray", 9),
                        ),
                        padding="40px",
                        margin_bottom="32px",
                    ),
                ),
                rx.box(height="0px"),  # Empty box when collapsed
            ),
            spacing="0",
            width="100%",
        ),
        padding="24px",
        width="100%",
        overflow="auto",
    )


def content_area() -> rx.Component:
    """Main content area with page routing."""
    return rx.box(
        rx.match(
            State.current_page,
            ("projects", projects_grid()),
            ("agents", agent_monitor_page()),
            ("statistics", statistics_page()),
            ("project_details", project_details_page()),
            projects_grid(),  # default
        ),
        width="100%",
        flex="1",
        overflow="auto",
    )


def index() -> rx.Component:
    """The main page."""
    return rx.vstack(
        navbar(),
        content_area(),
        spacing="0",
        width="100%",
        height="100vh",
        on_mount=State.on_load,
    )


# Create the app
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="grass",
        gray_color="slate",
        radius="large",
    ),
)

app.add_page(
    index,
    title="noGojira - AI Builds. No Tickets",
    description="AI Agent Project Management System",
)
